#!/usr/bin/env python3
"""CLI for sending CRJ Engine milestone notifications.

Usage:
    # Send a custom milestone notification:
    python scripts/notify.py --label "Pitch Detection Complete" --tag v0.1.0-pitch

    # Auto-detect from current git tag:
    python scripts/notify.py --auto

    # Send with extra details:
    python scripts/notify.py --label "Sprint 1 Done" --tag v0.1.0-pitch --details "CREPE accuracy at 95%"

    # Test the notification system (sends a test email):
    python scripts/notify.py --test
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crj_engine.notify import notify_for_tag, send_notification


def get_current_tag() -> str:
    """Get the git tag pointing at HEAD, if any."""
    try:
        return subprocess.check_output(
            ["git", "describe", "--tags", "--exact-match", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        return ""


def main():
    parser = argparse.ArgumentParser(description="CRJ Engine milestone notifications")
    parser.add_argument("--label", help="Milestone label (e.g. 'Pitch Detection Complete')")
    parser.add_argument("--tag", help="Git tag (e.g. 'v0.1.0-pitch')")
    parser.add_argument("--details", default="", help="Additional details")
    parser.add_argument("--auto", action="store_true", help="Auto-detect milestone from current git tag")
    parser.add_argument("--test", action="store_true", help="Send a test notification")
    args = parser.parse_args()

    if args.test:
        success = send_notification(
            milestone_label="Test Notification",
            tag="test",
            details="This is a test of the CRJ Engine notification system. If you received this, email is working.",
        )
        sys.exit(0 if success else 1)

    if args.auto:
        tag = get_current_tag()
        if not tag:
            print("[notify] No git tag at HEAD. Nothing to notify.")
            sys.exit(0)
        success = notify_for_tag(tag, details=args.details)
        sys.exit(0 if success else 1)

    if args.label:
        success = send_notification(
            milestone_label=args.label,
            tag=args.tag or "",
            details=args.details,
        )
        sys.exit(0 if success else 1)

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
