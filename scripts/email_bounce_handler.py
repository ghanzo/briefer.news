#!/usr/bin/env python3
"""
email_bounce_handler.py — Poll SQS for SES bounce + complaint events,
mark affected subscribers as bounced in postgres, log every event.

Architecture:
    SES → SNS topic briefer-ses-events
        → SQS queue briefer-ses-events-queue
        → this script (LaunchAgent, every 10 min)
        → email_subscribers.mark_bounced(email)
        → logs/email-bounces-YYYY-MM-DD.jsonl

Why SQS instead of an HTTP webhook: the mini sits behind a residential
ISP; SQS holds messages durably until acked, so a network blip or a
crashed handler doesn't lose bounce data. Also avoids needing the
Cloudflare Tunnel up for Step 7 to be functional.

Hard bounces → DB status='bounced'  (subscriber removed from send list)
Soft bounces → logged only          (transient — recipient might recover)
Complaints   → DB status='bounced'  (treat same as bounce — don't send again)

Usage:
    python3 scripts/email_bounce_handler.py            # one-shot poll
    python3 scripts/email_bounce_handler.py --verbose  # show each msg
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
LOGS = REPO / "logs"
LOGS.mkdir(exist_ok=True)

AWS = "/Users/maxgoshay/.local/bin/aws"
REGION = "us-east-1"
QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/462170975634/briefer-ses-events-queue"

sys.path.insert(0, str(REPO / "scripts"))
import email_subscribers as subs  # type: ignore


def log_event(record: dict) -> None:
    today = dt.date.today().isoformat()
    record["timestamp"] = dt.datetime.now().isoformat()
    with (LOGS / f"email-bounces-{today}.jsonl").open("a") as f:
        f.write(json.dumps(record) + "\n")


def receive_batch(max_messages: int = 10) -> list[dict]:
    """Pull up to max_messages from SQS. Wait 5s for messages (long polling)."""
    out = subprocess.check_output(
        [AWS, "sqs", "receive-message",
         "--queue-url", QUEUE_URL,
         "--max-number-of-messages", str(max_messages),
         "--wait-time-seconds", "5",
         "--visibility-timeout", "60",
         "--region", REGION,
         "--output", "json"],
        text=True, timeout=20,
    )
    data = json.loads(out) if out.strip() else {}
    return data.get("Messages", [])


def delete_message(receipt_handle: str) -> None:
    subprocess.check_call(
        [AWS, "sqs", "delete-message",
         "--queue-url", QUEUE_URL,
         "--receipt-handle", receipt_handle,
         "--region", REGION],
        timeout=10, stdout=subprocess.DEVNULL,
    )


def process_message(msg: dict, verbose: bool = False) -> dict:
    """Parse one SQS message (an SNS envelope around an SES event). Return summary."""
    body_str = msg.get("Body", "{}")
    try:
        sns_envelope = json.loads(body_str)
    except json.JSONDecodeError:
        return {"status": "skipped", "reason": "invalid SQS body JSON"}

    inner = sns_envelope.get("Message", "{}")
    try:
        event = json.loads(inner) if isinstance(inner, str) else inner
    except json.JSONDecodeError:
        return {"status": "skipped", "reason": "invalid SNS Message JSON"}

    event_type = event.get("notificationType") or event.get("eventType", "unknown")
    summary = {"event_type": event_type, "raw_event_id": event.get("mail", {}).get("messageId")}

    if event_type == "Bounce":
        bounce = event.get("bounce", {})
        bounce_type = bounce.get("bounceType", "?")        # Permanent / Transient / Undetermined
        bounce_subtype = bounce.get("bounceSubType", "?")  # General / NoEmail / Suppressed / etc.
        recipients = bounce.get("bouncedRecipients", [])
        summary["bounce_type"] = bounce_type
        summary["bounce_subtype"] = bounce_subtype
        summary["recipients"] = [r.get("emailAddress") for r in recipients]

        for r in recipients:
            email = r.get("emailAddress", "").strip().lower()
            if not email:
                continue
            if bounce_type == "Permanent":
                # Hard bounce — remove from sending list
                result = subs.mark_bounced(email)
                action = "marked_bounced" if result else "not_found"
            else:
                # Transient / Undetermined — log only, don't remove
                action = "logged_only_transient"
            log_event({"event": "bounce", "email": email,
                       "bounce_type": bounce_type, "bounce_subtype": bounce_subtype,
                       "action": action,
                       "diagnostic_code": r.get("diagnosticCode", "")[:200]})
            if verbose:
                print(f"  Bounce: {email} ({bounce_type}/{bounce_subtype}) → {action}")
        return summary

    if event_type == "Complaint":
        complaint = event.get("complaint", {})
        recipients = complaint.get("complainedRecipients", [])
        feedback_type = complaint.get("complaintFeedbackType", "?")  # abuse / fraud / virus / other
        summary["complaint_feedback_type"] = feedback_type
        summary["recipients"] = [r.get("emailAddress") for r in recipients]

        for r in recipients:
            email = r.get("emailAddress", "").strip().lower()
            if not email:
                continue
            # Complaints → treat as bounce (stop sending immediately)
            result = subs.mark_bounced(email)
            action = "marked_bounced_from_complaint" if result else "not_found"
            log_event({"event": "complaint", "email": email,
                       "feedback_type": feedback_type, "action": action})
            if verbose:
                print(f"  Complaint: {email} ({feedback_type}) → {action}")
        return summary

    # Unknown event type — log + ack so it doesn't loop
    log_event({"event": "unknown", "event_type": event_type, "raw": str(event)[:500]})
    if verbose:
        print(f"  Unknown event type: {event_type}")
    summary["status"] = "ignored"
    return summary


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--max-rounds", type=int, default=3,
                    help="How many receive-batch rounds before exiting (default 3)")
    args = ap.parse_args(argv)

    total_processed = 0
    total_bounces = 0
    total_complaints = 0

    for round_num in range(args.max_rounds):
        try:
            messages = receive_batch(max_messages=10)
        except subprocess.CalledProcessError as e:
            print(f"SQS receive failed: {e}", file=sys.stderr)
            return 1

        if not messages:
            if args.verbose:
                print(f"  (round {round_num + 1}: no messages)")
            break

        if args.verbose:
            print(f"  round {round_num + 1}: {len(messages)} messages")

        for msg in messages:
            summary = process_message(msg, verbose=args.verbose)
            total_processed += 1
            if summary.get("event_type") == "Bounce":
                total_bounces += 1
            elif summary.get("event_type") == "Complaint":
                total_complaints += 1
            try:
                delete_message(msg["ReceiptHandle"])
            except subprocess.CalledProcessError as e:
                print(f"  WARN: failed to delete msg: {e}", file=sys.stderr)

    print(f"processed={total_processed} bounces={total_bounces} complaints={total_complaints}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
