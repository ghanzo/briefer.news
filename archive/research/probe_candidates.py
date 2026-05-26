"""
Probe every US-gov RSS candidate from us_gov_feeds_catalog_2026-05-05.md.

Reuses probe_rss() from probe_sources.py. Skips entries that the catalog
explicitly flagged as JS-only / no-RSS / aggregator-index pages.

Output:
    research/candidates_probe_<DATE>.json  — machine-readable
    research/candidates_probe_<DATE>.md    — written separately after review
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research"))
from probe_sources import probe_rss, MAX_WORKERS

TODAY = datetime.now(timezone.utc).date().isoformat()
OUT_JSON = ROOT / "research" / f"candidates_probe_{TODAY}.json"

# ─────────────────────────────────────────────────────────────────────────────
# Candidate list — extracted from us_gov_feeds_catalog_2026-05-05.md
# Each tuple: (name, url, section, flag)
# Skipped intentionally: NSA (no RSS), CRS (no public RSS), SCOTUS opinions
# (no native — Cornell third-party left out as not-gov), index-only pages,
# and entries explicitly tagged [JS] in catalog.
# ─────────────────────────────────────────────────────────────────────────────

CANDIDATES = [
    # ── USDA ─────────────────────────────────────────────────────────────
    ("USDA — NASS News & Events",       "https://www.nass.usda.gov/Newsroom/rss/news.xml",            "USDA", "🔴"),
    ("USDA — NASS Today's Reports",     "https://www.nass.usda.gov/Newsroom/rss/todaysreports.xml",   "USDA", "🔴"),
    ("USDA — WASDE",                    "https://www.usda.gov/oce/commodity/wasde/rss.xml",           "USDA", "🔴"),
    ("USDA — ERS",                      "https://www.ers.usda.gov/rss/",                              "USDA", "🟡"),
    ("USDA — FAS",                      "https://www.fas.usda.gov/feed",                              "USDA", "🔴"),
    ("USDA — Newsroom",                 "https://www.usda.gov/about-usda/news/feed",                  "USDA", "🟡"),

    # ── DOL / BLS ────────────────────────────────────────────────────────
    ("DOL — News Releases",             "https://www.dol.gov/rss/releases.xml",                       "DOL", "🟡"),
    ("BLS — Major Economic Indicators", "https://www.bls.gov/feed/bls_latest.rss",                    "DOL/BLS", "🔴"),
    ("BLS — All News Releases",         "https://www.bls.gov/feed/news_release.rss",                  "DOL/BLS", "🔴"),
    ("BLS — Employment Situation",      "https://www.bls.gov/feed/empsit.rss",                        "DOL/BLS", "🔴"),
    ("BLS — CPI",                       "https://www.bls.gov/feed/cpi.rss",                           "DOL/BLS", "🔴"),
    ("BLS — PPI",                       "https://www.bls.gov/feed/ppi.rss",                           "DOL/BLS", "🔴"),
    ("OSHA — News",                     "https://www.dol.gov/newsroom/releases/osha/feed",            "DOL", "🟡"),
    ("ETA — Employment & Training",     "https://www.dol.gov/newsroom/releases/eta/feed",             "DOL", "🟡"),

    # ── VA ───────────────────────────────────────────────────────────────
    ("VA — VHA Inside Veterans Health", "https://www.va.gov/health/NewsFeatures/news.xml",            "VA", "⚪"),
    ("VA — OIG Reports",                "https://www.va.gov/oig/rss/reports-rss.asp",                 "VA", "🟡"),
    ("VA — Press Room",                 "https://news.va.gov/feed/",                                  "VA", "🟡"),

    # ── Education / HUD (low priority) ──────────────────────────────────
    ("Education — Press Releases",      "https://www.ed.gov/news/press-releases/feed",                "ED",  "⚪"),
    ("HUD — Press Releases",            "https://www.hud.gov/press/press_releases_media_advisories/feed", "HUD", "🟡"),

    # ── DOT ──────────────────────────────────────────────────────────────
    ("DOT — Newsroom",                  "https://www.transportation.gov/rss/briefing-room",           "DOT", "🟡"),
    ("FAA — News",                      "https://www.faa.gov/news/rss",                               "DOT", "🟡"),
    ("NHTSA — Press Releases",          "https://www.nhtsa.gov/press-releases/feed",                  "DOT", "🟡"),
    ("NHTSA — Vehicle Recalls (ODI)",   "https://www-odi.nhtsa.dot.gov/RSS/index.cfm",                "DOT", "🟡"),
    ("FRA — Federal Railroad",          "https://railroads.dot.gov/rss",                              "DOT", "⚪"),
    ("FMCSA — Motor Carrier",           "https://www.fmcsa.dot.gov/newsroom/rss",                     "DOT", "⚪"),
    ("FHWA — Federal Highway",          "https://www.fhwa.dot.gov/rss/index.htm",                     "DOT", "⚪"),
    ("MARAD — Maritime",                "https://www.maritime.dot.gov/rss",                           "DOT", "🟡"),
    ("FTA — Federal Transit",           "https://www.transit.dot.gov/rss",                            "DOT", "⚪"),
    ("PHMSA — Pipeline & Hazmat",       "https://www.phmsa.dot.gov/news/rss",                         "DOT", "🔴"),

    # ── Interior ─────────────────────────────────────────────────────────
    ("DOI — Press Releases",            "https://www.doi.gov/news/feed",                              "DOI", "🟡"),
    ("BLM — Index",                     "https://www.blm.gov/info/RSS-feeds",                         "DOI", "🟡"),
    ("NPS — Park News",                 "https://www.nps.gov/orgs/news/feed.xml",                     "DOI", "⚪"),
    ("FWS — Fish & Wildlife",           "https://www.fws.gov/news/feed",                              "DOI", "⚪"),
    ("BIA — Indian Affairs",            "https://www.bia.gov/news/feed",                              "DOI", "⚪"),
    ("BOEM — Ocean Energy Mgmt",        "https://www.boem.gov/newsroom/feed",                         "DOI", "🔴"),
    ("BSEE — Safety Enforcement",       "https://www.bsee.gov/newsroom/feed",                         "DOI", "🟡"),

    # ── DHS sub-agencies ────────────────────────────────────────────────
    ("DHS — Press Releases",            "https://www.dhs.gov/news-releases/press-releases/feed",      "DHS", "🔴"),
    ("TSA — News",                      "https://www.tsa.gov/news/rss",                               "DHS", "🟡"),
    ("CBP — News",                      "https://www.cbp.gov/rss.xml",                                "DHS", "🔴"),
    ("CBP — Media Releases",            "https://www.cbp.gov/newsroom/media-releases/all/feed",       "DHS", "🔴"),
    ("ICE — Press",                     "https://www.ice.gov/news/feed",                              "DHS", "🟡"),
    ("USCIS — News",                    "https://www.uscis.gov/news/rss",                             "DHS", "🟡"),
    ("FEMA — Disaster Declarations",    "https://www.fema.gov/news/disasters_rss.fema",               "DHS", "🔴"),
    ("FEMA — Press Releases",           "https://www.fema.gov/media-library/assets/rss.xml/rss.xml",  "DHS", "🟡"),
    ("USCG — News",                     "https://www.news.uscg.mil/RSS/Headlines.aspx",               "DHS", "🟡"),

    # ── DOJ sub-agencies ────────────────────────────────────────────────
    ("DOJ — Justice News (OPA)",        "https://www.justice.gov/news/rss?m=1",                       "DOJ", "🟡"),
    ("DOJ — Antitrust Division",        "https://www.justice.gov/atr/news-feeds",                     "DOJ", "🔴"),
    ("FBI — National Press",            "https://www.fbi.gov/feeds/national-press-releases/RSS",      "DOJ", "🔴"),
    ("FBI — Top Stories",               "https://www.fbi.gov/feeds/fbi-top-stories/RSS",              "DOJ", "🟡"),
    ("FBI — Congressional Testimony",   "https://www.fbi.gov/feeds/congressional-testimony/RSS",      "DOJ", "🟡"),
    ("DEA — Press",                     "https://www.dea.gov/press-releases/feed",                    "DOJ", "🟡"),
    ("ATF — Press",                     "https://www.atf.gov/news/press-releases/feed",               "DOJ", "⚪"),
    ("USMS — News",                     "https://www.usmarshals.gov/news/feed",                       "DOJ", "⚪"),
    ("BOP — News",                      "https://www.bop.gov/resources/news/feed",                    "DOJ", "⚪"),

    # ── Treasury sub-agencies ───────────────────────────────────────────
    ("IRS — Newsroom",                  "https://www.irs.gov/newsroom/feed",                          "Treasury", "🟡"),
    ("FinCEN — News",                   "https://www.fincen.gov/news/news-releases/feed",             "Treasury", "🔴"),
    ("TTB — News",                      "https://www.ttb.gov/templates/ttb/news/ttb.xml",             "Treasury", "⚪"),
    ("Treasury — Press Releases",       "https://home.treasury.gov/news/press-releases/feed",         "Treasury", "🔴"),

    # ── Commerce sub-agencies ───────────────────────────────────────────
    ("BEA — Releases",                  "https://apps.bea.gov/rss/rss.xml",                           "Commerce", "🔴"),
    ("Census — News",                   "https://www.census.gov/about/contact-us/feeds/news.xml",     "Commerce", "🟡"),
    ("USPTO — PTAB Notifications",      "https://developer.uspto.gov/ptab-feed/notifications.rss",    "Commerce", "⚪"),
    ("USPTO — News & Updates",          "https://www.uspto.gov/about-us/news-updates/feed",           "Commerce", "⚪"),
    ("ITA — International Trade",       "https://www.trade.gov/rss/news.xml",                         "Commerce", "🔴"),

    # ── DoD branches ────────────────────────────────────────────────────
    ("DoD — Releases",                  "https://www.war.gov/News/Releases/feed",                     "DoD", "🔴"),
    ("DoD — Transcripts",               "https://www.war.gov/News/Transcripts/feed",                  "DoD", "🟡"),
    ("DoD — Contracts",                 "https://www.war.gov/News/Contracts/feed",                    "DoD", "🟡"),
    ("Army — News",                     "https://www.army.mil/rss/",                                  "DoD", "🟡"),
    ("Navy — News (index)",             "https://www.navy.mil/Resources/Rss-Feeds/",                  "DoD", "🟡"),
    ("Air Force — News",                "https://www.af.mil/News/RSS/",                               "DoD", "🟡"),
    ("Marine Corps — News",             "https://www.marines.mil/RSS/",                               "DoD", "🟡"),
    ("Space Force — News",              "https://www.spaceforce.mil/News/feed",                       "DoD", "🔴"),
    ("Space Systems Command",           "https://www.ssc.spaceforce.mil/RSS",                         "DoD", "🔴"),
    ("DCSA — Counterintelligence",      "https://www.dcsa.mil/news/feed",                             "DoD", "🟡"),
    ("DTRA — Threat Reduction",         "https://www.dtra.mil/News/feed",                             "DoD", "🔴"),

    # ── HHS sub-agencies ────────────────────────────────────────────────
    ("CMS — Newsroom",                  "https://www.cms.gov/newsroom/rss",                           "HHS", "🔴"),
    ("CMS — Internet-Only Manuals",     "https://www.cms.gov/rss/31836",                              "HHS", "🟡"),
    ("SAMHSA — News",                   "https://www.samhsa.gov/news/feed",                           "HHS", "⚪"),
    ("HRSA — News",                     "https://www.hrsa.gov/about/news/feed",                       "HHS", "⚪"),
    ("AHRQ — News",                     "https://www.ahrq.gov/news/rss.xml",                          "HHS", "⚪"),
    ("ACL — News",                      "https://acl.gov/news-and-events/feed",                       "HHS", "⚪"),

    # ── DOE program offices ─────────────────────────────────────────────
    ("DOE — EERE",                      "https://www.energy.gov/eere/rss.xml",                        "DOE", "🔴"),
    ("DOE — FECM",                      "https://www.energy.gov/fecm/rss.xml",                        "DOE", "🔴"),
    ("DOE — NETL",                      "https://netl.doe.gov/rss/news.xml",                          "DOE", "🔴"),

    # ── DOE national labs ───────────────────────────────────────────────
    ("ORNL — Oak Ridge",                "https://www.ornl.gov/news/feed",                             "DOE labs", "🔴"),
    ("LBNL — Lawrence Berkeley",        "https://newscenter.lbl.gov/feed/",                           "DOE labs", "🔴"),
    ("LLNL — Lawrence Livermore",       "https://www.llnl.gov/news/feed",                             "DOE labs", "🔴"),
    ("ANL — Argonne",                   "https://www.anl.gov/feed/news",                              "DOE labs", "🔴"),
    ("PNNL — Pacific Northwest",        "https://www.pnnl.gov/news/feed",                             "DOE labs", "🔴"),
    ("INL — Idaho",                     "https://inl.gov/feed/",                                      "DOE labs", "🔴"),
    ("SLAC",                            "https://www6.slac.stanford.edu/news/feed",                   "DOE labs", "🟡"),
    ("FNAL — Fermilab",                 "https://news.fnal.gov/feed/",                                "DOE labs", "🟡"),
    ("BNL — Brookhaven",                "https://www.bnl.gov/newsroom/news.rss",                      "DOE labs", "🟡"),
    ("LANL — Los Alamos",               "https://www.lanl.gov/discover/news-release/feed",            "DOE labs", "🔴"),
    ("NREL — Renewables",               "https://www.nrel.gov/news/rss.xml",                          "DOE labs", "🔴"),
    ("SNL — Sandia",                    "https://newsreleases.sandia.gov/feed/",                      "DOE labs", "🔴"),
    ("PPPL — Princeton Plasma",         "https://www.pppl.gov/news/feed",                             "DOE labs", "🟡"),
    ("JLab — Jefferson",                "https://www.jlab.org/news/feed",                             "DOE labs", "⚪"),
    ("AMES — Ames",                     "https://www.ameslab.gov/news/feed",                          "DOE labs", "🟡"),

    # ── Independent regulators ─────────────────────────────────────────
    ("SSA — Press Releases",            "https://www.ssa.gov/news/press/releases/rss.xml",            "Indep", "🟡"),
    ("SBA — Press",                     "https://www.sba.gov/about-sba/sba-newsroom/press-releases-media-advisories/feed", "Indep", "⚪"),
    ("OPM — News",                      "https://www.opm.gov/rss/",                                   "Indep", "⚪"),
    ("CFPB — Newsroom",                 "https://www.consumerfinance.gov/about-us/newsroom/feed/",    "Indep", "🔴"),
    ("PBGC — News",                     "https://www.pbgc.gov/news/rss",                              "Indep", "🟡"),
    ("EXIM Bank — News",                "https://www.exim.gov/news/feed",                             "Indep", "🟡"),
    ("NLRB — Press Releases",           "https://www.nlrb.gov/rss/rssPressReleases.xml",              "Indep", "🟡"),
    ("NLRB — Weekly Summaries",         "https://www.nlrb.gov/rss/rssWeeklySummaries.xml",            "Indep", "🟡"),
    ("NLRB — Announcements",            "https://www.nlrb.gov/rss/rssAnnouncements.xml",              "Indep", "⚪"),
    ("EEOC — Newsroom",                 "https://www.eeoc.gov/newsroom/feed",                         "Indep", "⚪"),
    ("NARA — News",                     "https://www.archives.gov/news/rss",                         "Indep", "⚪"),
    ("Smithsonian Insider",             "https://insider.si.edu/feed/",                               "Indep", "⚪"),

    # ── Intelligence Community ──────────────────────────────────────────
    ("ODNI — Press",                    "https://www.dni.gov/index.php/rss",                          "IC", "🔴"),
    ("CIA — News",                      "https://www.cia.gov/news-information/rss",                   "IC", "🔴"),
    ("DIA — News",                      "https://www.dia.mil/News-Features/feed",                     "IC", "🔴"),
    ("NRO — Press",                     "https://www.nro.gov/News-Press-Releases/feed",               "IC", "🔴"),

    # ── Federal Reserve regional banks ──────────────────────────────────
    ("NY Fed — Liberty Street",         "https://libertystreeteconomics.newyorkfed.org/feed/",        "Fed banks", "🔴"),
    ("NY Fed — EPR",                    "https://www.newyorkfed.org/medialibrary/media/research/rss/feeds/epr.xml", "Fed banks", "🟡"),
    ("Atlanta Fed — Index",             "https://www.atlantafed.org/RSS",                             "Fed banks", "🔴"),
    ("Chicago Fed — Index",             "https://www.chicagofed.org/rss",                             "Fed banks", "🔴"),
    ("St. Louis Fed — Research",        "https://research.stlouisfed.org/rss/",                       "Fed banks", "🔴"),
    ("Cleveland Fed — News",            "https://www.clevelandfed.org/news-and-events/rss",           "Fed banks", "🔴"),
    ("Dallas Fed — Index",              "https://www.dallasfed.org/rss/",                             "Fed banks", "🔴"),
    ("Boston Fed — Index",              "https://www.bostonfed.org/feeds.aspx",                       "Fed banks", "🟡"),
    ("Philadelphia Fed",                "https://www.philadelphiafed.org/rss",                        "Fed banks", "🟡"),
    ("Richmond Fed",                    "https://www.richmondfed.org/press_room/rss",                 "Fed banks", "🟡"),
    ("Minneapolis Fed",                 "https://www.minneapolisfed.org/feeds",                       "Fed banks", "🟡"),
    ("Kansas City Fed",                 "https://www.kansascityfed.org/about-us/rss/",                "Fed banks", "🟡"),
    ("San Francisco Fed",               "https://www.frbsf.org/feed/",                                "Fed banks", "🟡"),

    # ── GovInfo (Legislative) ───────────────────────────────────────────
    ("GovInfo — Bills",                 "https://www.govinfo.gov/rss/bills.xml",                      "GovInfo", "🔴"),
    ("GovInfo — Bills Enrolled",        "https://www.govinfo.gov/rss/bills-enr.xml",                  "GovInfo", "🔴"),
    ("GovInfo — Public Laws",           "https://www.govinfo.gov/rss/plaw.xml",                       "GovInfo", "🔴"),
    ("GovInfo — Hearings",              "https://www.govinfo.gov/rss/chrg.xml",                       "GovInfo", "🟡"),
    ("GovInfo — Reports",               "https://www.govinfo.gov/rss/crpt.xml",                       "GovInfo", "🟡"),
    ("GovInfo — Congressional Record",  "https://www.govinfo.gov/rss/crec.xml",                       "GovInfo", "🟡"),
    ("GovInfo — Presidential Documents","https://www.govinfo.gov/rss/dcpd.xml",                       "GovInfo", "🟡"),
    ("GovInfo — Federal Register",      "https://www.govinfo.gov/rss/fr.xml",                         "GovInfo", "🟡"),
    ("GovInfo — Economic Indicators",   "https://www.govinfo.gov/rss/econi.xml",                      "GovInfo", "🟡"),

    # ── CBO ─────────────────────────────────────────────────────────────
    ("CBO — Publications",              "https://www.cbo.gov/publications/all/rss.xml",               "CBO", "🔴"),

    # ── Congress committees (Drupal _format=rss probe) ─────────────────
    ("Senate Armed Services",           "https://www.armed-services.senate.gov/press-releases?_format=rss", "Cong", "🔴"),
    ("Senate Foreign Relations",        "https://www.foreign.senate.gov/press/?_format=rss",          "Cong", "🔴"),
    ("Senate Select Intelligence",      "https://www.intelligence.senate.gov/press/?_format=rss",     "Cong", "🔴"),
    ("Senate Banking",                  "https://www.banking.senate.gov/newsroom?_format=rss",        "Cong", "🔴"),
    ("Senate Finance",                  "https://www.finance.senate.gov/chairmans-news?_format=rss",  "Cong", "🔴"),
    ("Senate Energy & Nat Resources",   "https://www.energy.senate.gov/press-releases?_format=rss",   "Cong", "🔴"),
    ("House Armed Services",            "https://armedservices.house.gov/press-releases?_format=rss", "Cong", "🔴"),
    ("House Foreign Affairs",           "https://foreignaffairs.house.gov/news?_format=rss",          "Cong", "🔴"),
    ("House Permanent Select Intel",    "https://intelligence.house.gov/news?_format=rss",            "Cong", "🔴"),
    ("House Financial Services",        "https://financialservices.house.gov/news/?_format=rss",      "Cong", "🔴"),
    ("House Energy & Commerce",         "https://energycommerce.house.gov/news?_format=rss",          "Cong", "🔴"),

    # ── Judicial — GovInfo per-court feeds ──────────────────────────────
    ("US Courts (top-level index)",     "https://www.uscourts.gov/rss-feeds",                         "Judicial", "🟡"),
    ("GovInfo — Court of Intl Trade",   "https://www.govinfo.gov/rss/uscourts-cit.xml",               "Judicial", "🔴"),
    ("GovInfo — Court of Fed Claims",   "https://www.govinfo.gov/rss/uscourts-cofc.xml",              "Judicial", "🟡"),
    ("GovInfo — JPML",                  "https://www.govinfo.gov/rss/uscourts-jpml.xml",              "Judicial", "🟡"),
    ("GovInfo — Court of Appeals DC",   "https://www.govinfo.gov/rss/uscourts-cadc.xml",              "Judicial", "🔴"),
    ("GovInfo — Court of Appeals 9th",  "https://www.govinfo.gov/rss/uscourts-ca9.xml",               "Judicial", "🔴"),
    ("GovInfo — Court of Appeals 2nd",  "https://www.govinfo.gov/rss/uscourts-ca2.xml",               "Judicial", "🟡"),
    ("GovInfo — Court of Appeals 5th",  "https://www.govinfo.gov/rss/uscourts-ca5.xml",               "Judicial", "🟡"),

    # ── Aggregators / cross-cutting ────────────────────────────────────
    ("Federal Register — Public Inspect","https://www.federalregister.gov/api/v1/public-inspection-documents.rss", "Agg", "🔴"),
    ("CPSC — News Releases",            "https://www.cpsc.gov/Newsroom/News-Releases/feed",           "Agg", "🟡"),
    ("USDA FSIS — Recalls",             "https://www.fsis.usda.gov/recalls-alerts/feed",              "Agg", "🟡"),
]


def probe_one(item: tuple) -> dict:
    name, url, section, flag = item
    result = probe_rss(url)
    return {
        "name": name,
        "section": section,
        "url": url,
        "flag": flag,
        **result,
    }


def main():
    print(f"Probing {len(CANDIDATES)} candidate sources (workers={MAX_WORKERS})", flush=True)
    print("-" * 100, flush=True)

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(probe_one, item): item for item in CANDIDATES}
        for fut in as_completed(futures):
            try:
                r = fut.result()
                results.append(r)
                status = r.get("status") or "?"
                marker = {
                    "fresh": "OK", "stale": "OLD", "empty": "EMPTY",
                    "no_dates": "NODATE", "timeout": "TIMEOUT",
                    "parse_error": "PARSE", "request_error": "NET",
                    "exception": "EXC", "skipped_playwright": "SKIP",
                }.get(status, status[:8])
                if status.startswith("http_"):
                    marker = status.upper()
                err = ""
                if r.get("error"):
                    err = f" :: {r['error'][:60]}"
                # ASCII-only print to avoid Windows console encoding crashes
                safe_name = r['name'].encode('ascii', errors='replace').decode('ascii')
                line = (f"  [{marker:>10}] {safe_name:42.42}  "
                        f"e={r.get('entry_count', 0):>3} f={r.get('fresh_count', 0):>2}  "
                        f"{r.get('elapsed_s', 0):>5}s{err}")
                try:
                    print(line, flush=True)
                except UnicodeEncodeError:
                    pass
            except Exception as e:
                item = futures[fut]
                try:
                    print(f"  [!ERR] {item[0]}  worker_error: {e}", flush=True)
                except UnicodeEncodeError:
                    pass

    results.sort(key=lambda x: x["name"])
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "probe_date": TODAY,
            "probed_at": datetime.now(timezone.utc).isoformat(),
            "fresh_threshold_hours": 72,
            "total_sources": len(results),
            "results": results,
        }, f, indent=2, default=str)

    by_status: dict[str, int] = {}
    for r in results:
        s = r.get("status", "?")
        by_status[s] = by_status.get(s, 0) + 1
    print("\n" + "=" * 100)
    print(f"Total: {len(results)} candidates")
    for status, count in sorted(by_status.items(), key=lambda x: -x[1]):
        print(f"  {status:>22}  {count:>3}")
    print(f"\nResults: {OUT_JSON}")


if __name__ == "__main__":
    main()
