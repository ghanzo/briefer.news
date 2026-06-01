#!/usr/bin/env python3
"""
dmarc_report.py — daily DMARC aggregate-report digest.

DMARC reports for briefer.news are routed (via the _dmarc `rua` record) to
dmarc@briefer.news, received by AWS SES, and dropped as raw MIME into
s3://briefer-news-dmarc/incoming/. This job fetches each one, extracts the
gzip/zip XML aggregate report, parses it, and appends a plain-English summary to
logs/dmarc/dmarc-<date>.log — so the operator never opens an XML attachment.

Per message: how many emails a provider saw claiming to be from briefer.news,
and what fraction passed SPF/DKIM alignment. Anything that FAILS both (possible
spoofing of the domain) is flagged and routed through the shared notifier — which
in the default digest mode lands in the 09:00 alert digest, i.e. this becomes a
real deliverability/spoofing signal in the daily health check.

Processed S3 objects are deleted; non-DMARC mail (SES setup pings, strays) is
logged and deleted too, so incoming/ never accumulates. Report files live under
logs/dmarc/ and are auto-pruned by cleanup.sh's logs/ rotation (>14d).

Runs daily from news.briefer.dmarc.

Usage:
  python3 scripts/dmarc_report.py
  python3 scripts/dmarc_report.py --selftest   # parse a synthetic report; no S3/network
  python3 scripts/dmarc_report.py --keep       # don't delete S3 objects (debugging)
"""

from __future__ import annotations

import argparse
import datetime as dt
import email
import gzip
import io
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOG_DIR = REPO / "logs" / "dmarc"
AWS = "/Users/maxgoshay/.local/bin/aws"   # PATH isn't set under launchd
REGION = "us-east-1"
BUCKET = "briefer-news-dmarc"
PREFIX = "incoming/"

sys.path.insert(0, str(REPO / "scripts"))
try:
    from notify import notify  # off-box notifier (digest mode by default)
except Exception:  # pragma: no cover
    def notify(severity: str, message: str, dry_run: bool = False) -> bool:
        sys.stderr.write(f"notify failed; would send [{severity}] {message}\n")
        return False


def _aws(*args: str, binary: bool = False):
    r = subprocess.run([AWS, *args], capture_output=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"aws {' '.join(args[:3])}… failed: {r.stderr.decode(errors='replace')[:300]}")
    return r.stdout if binary else r.stdout.decode(errors="replace")


def list_incoming() -> list[str]:
    out = _aws("s3api", "list-objects-v2", "--bucket", BUCKET, "--prefix", PREFIX,
               "--region", REGION, "--query", "Contents[].Key", "--output", "json")
    keys = json.loads(out) if out.strip() and out.strip() != "None" else []
    return [k for k in (keys or []) if not k.endswith("/")]


def fetch(key: str) -> bytes:
    return _aws("s3", "cp", f"s3://{BUCKET}/{key}", "-", "--region", REGION, binary=True)


def delete(key: str) -> None:
    _aws("s3", "rm", f"s3://{BUCKET}/{key}", "--region", REGION)


def extract_dmarc_xml(raw: bytes) -> bytes | None:
    """Pull the gzip/zip/plain XML aggregate report out of a raw MIME email."""
    msg = email.message_from_bytes(raw)
    for part in msg.walk():
        ct = (part.get_content_type() or "").lower()
        fn = (part.get_filename() or "").lower()
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        if ct in ("application/gzip", "application/x-gzip") or fn.endswith(".gz"):
            try:
                return gzip.decompress(payload)
            except Exception:
                pass
        if ct in ("application/zip", "application/x-zip-compressed") or fn.endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(payload)) as z:
                    name = next((n for n in z.namelist() if n.lower().endswith(".xml")), None)
                    if name:
                        return z.read(name)
            except Exception:
                pass
        if ct in ("text/xml", "application/xml") or fn.endswith(".xml"):
            return payload
    return None


def parse_report(xml_bytes: bytes) -> dict:
    root = ET.fromstring(xml_bytes)
    org = (root.findtext("report_metadata/org_name") or "?").strip()

    def asdate(ts):
        try:
            return dt.datetime.utcfromtimestamp(int(ts)).date().isoformat()
        except Exception:
            return "?"

    begin = asdate(root.findtext("report_metadata/date_range/begin"))
    end = asdate(root.findtext("report_metadata/date_range/end"))
    total = aligned = 0
    rows = []
    for rec in root.findall("record"):
        cnt = int(rec.findtext("row/count") or 0)
        ip = rec.findtext("row/source_ip") or "?"
        dkim = (rec.findtext("row/policy_evaluated/dkim") or "?").lower()
        spf = (rec.findtext("row/policy_evaluated/spf") or "?").lower()
        disp = (rec.findtext("row/policy_evaluated/disposition") or "?").lower()
        hfrom = rec.findtext("identifiers/header_from") or "?"
        total += cnt
        ok = dkim == "pass" or spf == "pass"   # DMARC passes on EITHER aligned mechanism
        if ok:
            aligned += cnt
        rows.append({"ip": ip, "count": cnt, "dkim": dkim, "spf": spf,
                     "disp": disp, "hfrom": hfrom, "aligned": ok})
    return {"org": org, "begin": begin, "end": end, "total": total,
            "aligned": aligned, "rows": rows}


def summarize(rep: dict) -> tuple[str, list]:
    pct = (100 * rep["aligned"] // rep["total"]) if rep["total"] else 0
    fails = [r for r in rep["rows"] if not r["aligned"]]
    lines = [f"  {rep['org']}  {rep['begin']}..{rep['end']}  —  "
             f"{rep['total']} msg, {pct}% aligned (SPF or DKIM pass)"]
    for r in fails:
        lines.append(f"    [!] UNALIGNED: {r['count']} msg from {r['ip']} "
                     f"(dkim={r['dkim']} spf={r['spf']} disp={r['disp']} from={r['hfrom']})")
    return "\n".join(lines), fails


SAMPLE_XML = b"""<?xml version="1.0"?>
<feedback>
  <report_metadata><org_name>google.com</org_name>
    <date_range><begin>1717200000</begin><end>1717286400</end></date_range></report_metadata>
  <record><row><source_ip>54.240.1.2</source_ip><count>120</count>
    <policy_evaluated><disposition>none</disposition><dkim>pass</dkim><spf>pass</spf></policy_evaluated></row>
    <identifiers><header_from>briefer.news</header_from></identifiers></record>
  <record><row><source_ip>203.0.113.9</source_ip><count>3</count>
    <policy_evaluated><disposition>none</disposition><dkim>fail</dkim><spf>fail</spf></policy_evaluated></row>
    <identifiers><header_from>briefer.news</header_from></identifiers></record>
</feedback>"""


def main() -> int:
    ap = argparse.ArgumentParser(description="DMARC aggregate-report digest")
    ap.add_argument("--selftest", action="store_true", help="parse a synthetic report, no S3")
    ap.add_argument("--keep", action="store_true", help="do not delete S3 objects")
    args = ap.parse_args()

    if args.selftest:
        rep = parse_report(SAMPLE_XML)
        text, fails = summarize(rep)
        print("SELFTEST — parsed synthetic report:")
        print(text)
        print(f"unaligned sources: {len(fails)} (expected 1)")
        return 0 if len(fails) == 1 and rep["total"] == 123 else 1

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    report_path = LOG_DIR / f"dmarc-{today.replace('-', '')}.log"

    try:
        keys = list_incoming()
    except Exception as e:
        msg = f"dmarc_report could not list S3 inbound: {e}"
        sys.stderr.write(msg + "\n")
        notify("warn", msg)
        return 2

    if not keys:
        print("[dmarc] no new reports in incoming/")
        return 0

    out_lines = [f"DMARC digest — {dt.datetime.utcnow().isoformat()}Z — {len(keys)} object(s)"]
    all_fails, parsed, skipped = [], 0, 0
    for key in keys:
        try:
            raw = fetch(key)
            xml = extract_dmarc_xml(raw)
            if xml is None:
                skipped += 1
                out_lines.append(f"  (skipped non-DMARC object {key.split('/')[-1]})")
                if not args.keep:
                    delete(key)
                continue
            rep = parse_report(xml)
            text, fails = summarize(rep)
            out_lines.append(text)
            all_fails.extend(fails)
            parsed += 1
            if not args.keep:
                delete(key)
        except Exception as e:
            out_lines.append(f"  ERROR parsing {key}: {e} (left in S3 for retry)")

    summary = "\n".join(out_lines) + "\n"
    print(summary)
    with report_path.open("a") as f:
        f.write(summary + "\n")

    if all_fails:
        total_bad = sum(r["count"] for r in all_fails)
        notify("warn", f"DMARC: {total_bad} message(s) from {len(all_fails)} source(s) FAILED "
                       f"SPF+DKIM alignment for briefer.news (possible spoofing). See {report_path}.")
    print(f"[dmarc] parsed {parsed} report(s), skipped {skipped} non-DMARC, "
          f"{len(all_fails)} unaligned source(s) -> {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
