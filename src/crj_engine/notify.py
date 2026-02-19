"""Milestone notification system — sends email updates at key project junctures."""

from __future__ import annotations

import json
import os
import smtplib
import subprocess
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

_CONFIGS_DIR = Path(__file__).resolve().parents[2] / "configs"
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_config() -> dict:
    with open(_CONFIGS_DIR / "notify.json") as f:
        return json.load(f)


def _get_smtp_settings(config: dict) -> dict:
    """Resolve SMTP settings from environment variables (preferred) or config file."""
    return {
        "host": os.environ.get("CRJ_SMTP_HOST", config["smtp"]["host"]),
        "port": int(os.environ.get("CRJ_SMTP_PORT", config["smtp"]["port"])),
        "use_tls": config["smtp"]["use_tls"],
        "username": os.environ.get("CRJ_SMTP_USERNAME", config["smtp"]["username"]),
        "password": os.environ.get("CRJ_SMTP_PASSWORD", config["smtp"]["password"]),
    }


def _get_git_info() -> dict:
    """Gather current git state for the notification."""
    def run(cmd: list[str]) -> str:
        try:
            return subprocess.check_output(cmd, cwd=_PROJECT_ROOT, text=True).strip()
        except Exception:
            return ""

    return {
        "branch": run(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        "commit": run(["git", "rev-parse", "--short", "HEAD"]),
        "commit_msg": run(["git", "log", "-1", "--pretty=%s"]),
        "author": run(["git", "log", "-1", "--pretty=%an"]),
        "tag": run(["git", "describe", "--tags", "--exact-match", "HEAD"]),
    }


def _build_html_body(
    milestone_label: str,
    tag: str,
    details: str,
    git_info: dict,
) -> str:
    """Build a clean HTML email body."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""\
<html>
<body style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
  <div style="background: linear-gradient(135deg, #1a1a2e, #16213e); padding: 24px; border-radius: 8px 8px 0 0;">
    <h1 style="color: #e0e0e0; margin: 0; font-size: 20px;">CRJ Engine</h1>
    <p style="color: #a0c4ff; margin: 4px 0 0 0; font-size: 14px;">Milestone Notification</p>
  </div>

  <div style="border: 1px solid #e0e0e0; border-top: none; padding: 24px; border-radius: 0 0 8px 8px;">
    <h2 style="color: #1a1a2e; margin-top: 0;">{milestone_label}</h2>

    <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
      <tr>
        <td style="padding: 8px 12px; background: #f5f5f5; font-weight: bold; width: 120px;">Tag</td>
        <td style="padding: 8px 12px; background: #f5f5f5;"><code>{tag}</code></td>
      </tr>
      <tr>
        <td style="padding: 8px 12px; font-weight: bold;">Branch</td>
        <td style="padding: 8px 12px;">{git_info.get('branch', '—')}</td>
      </tr>
      <tr>
        <td style="padding: 8px 12px; background: #f5f5f5; font-weight: bold;">Commit</td>
        <td style="padding: 8px 12px; background: #f5f5f5;">
          <code>{git_info.get('commit', '—')}</code> — {git_info.get('commit_msg', '')}
        </td>
      </tr>
      <tr>
        <td style="padding: 8px 12px; font-weight: bold;">Author</td>
        <td style="padding: 8px 12px;">{git_info.get('author', '—')}</td>
      </tr>
      <tr>
        <td style="padding: 8px 12px; background: #f5f5f5; font-weight: bold;">Time</td>
        <td style="padding: 8px 12px; background: #f5f5f5;">{now}</td>
      </tr>
    </table>

    {f'<div style="margin-top: 16px; padding: 16px; background: #f0f7ff; border-left: 4px solid #2196F3; border-radius: 4px;"><strong>Details:</strong><br/>{details}</div>' if details else ''}

    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 24px 0;" />
    <p style="color: #888; font-size: 12px; margin: 0;">
      This is an automated notification from CRJ Engine.<br/>
      114 Ananda Ghanam, Ooty Road, Mysore 570025
    </p>
  </div>
</body>
</html>"""


def send_notification(
    milestone_label: str,
    tag: str = "",
    details: str = "",
    recipient: str | None = None,
) -> bool:
    """Send a milestone notification email.

    Args:
        milestone_label: Human-readable milestone name (e.g. "Pitch Detection Complete").
        tag: Git tag associated with this milestone (e.g. "v0.1.0-pitch").
        details: Optional additional details or notes.
        recipient: Override recipient email (defaults to config).

    Returns:
        True if email was sent successfully, False otherwise.
    """
    config = _load_config()
    smtp = _get_smtp_settings(config)
    git_info = _get_git_info()

    to_addr = recipient or os.environ.get("CRJ_NOTIFY_RECIPIENT", config["recipient"])
    from_addr = os.environ.get("CRJ_NOTIFY_SENDER", config["sender"])

    if not smtp["host"] or not smtp["username"]:
        print(f"[notify] SMTP not configured. Notification logged locally:")
        print(f"  Milestone: {milestone_label}")
        print(f"  Tag:       {tag}")
        print(f"  Commit:    {git_info.get('commit', '?')} — {git_info.get('commit_msg', '')}")
        print(f"  Details:   {details}")
        _log_locally(milestone_label, tag, details, git_info)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[CRJ Engine] {milestone_label}"
    msg["From"] = from_addr
    msg["To"] = to_addr

    plain_text = (
        f"CRJ Engine — Milestone Notification\n"
        f"{'=' * 40}\n\n"
        f"Milestone: {milestone_label}\n"
        f"Tag:       {tag}\n"
        f"Branch:    {git_info.get('branch', '—')}\n"
        f"Commit:    {git_info.get('commit', '—')} — {git_info.get('commit_msg', '')}\n"
        f"Author:    {git_info.get('author', '—')}\n\n"
        f"{f'Details: {details}' if details else ''}\n"
    )
    html_body = _build_html_body(milestone_label, tag, details, git_info)

    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(smtp["host"], smtp["port"]) as server:
            if smtp["use_tls"]:
                server.starttls()
            server.login(smtp["username"], smtp["password"])
            server.sendmail(from_addr, [to_addr], msg.as_string())
        print(f"[notify] Email sent to {to_addr}: {milestone_label}")
        _log_locally(milestone_label, tag, details, git_info, sent=True)
        return True
    except Exception as e:
        print(f"[notify] Failed to send email: {e}")
        _log_locally(milestone_label, tag, details, git_info, sent=False, error=str(e))
        return False


def _log_locally(
    milestone_label: str,
    tag: str,
    details: str,
    git_info: dict,
    sent: bool = False,
    error: str = "",
) -> None:
    """Append a record to the local notification log."""
    log_path = _PROJECT_ROOT / "data" / "notifications.log"
    now = datetime.now(timezone.utc).isoformat()
    status = "SENT" if sent else ("FAILED" if error else "LOCAL_ONLY")

    entry = (
        f"[{now}] [{status}] {milestone_label} | tag={tag} "
        f"| commit={git_info.get('commit', '?')} "
        f"| {details}"
        f"{f' | error={error}' if error else ''}\n"
    )

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as f:
        f.write(entry)


def notify_for_tag(tag: str, details: str = "") -> bool:
    """Look up a git tag in the milestone list and send notification if it matches."""
    config = _load_config()
    for m in config["milestones"]:
        if m["tag"] == tag:
            return send_notification(m["label"], tag=tag, details=details)
    print(f"[notify] Tag '{tag}' is not a registered milestone. No notification sent.")
    return False
