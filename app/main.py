from __future__ import annotations
import json
import os
from typing import Any, Dict

from dotenv import load_dotenv

from app.mailer import load_smtp_config, send_pdf
from app.payload import parse_submission
from app.pdf_report import build_pdf_bytes


def load_event() -> Dict[str, Any]:
    # In GitHub Actions, this is provided automatically
    path = os.environ.get("GITHUB_EVENT_PATH")
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # Local fallback
    local_path = os.environ.get("LOCAL_EVENT_PATH", "sample_event.json")
    with open(local_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    load_dotenv()  # local convenience; harmless in Actions
    event = load_event()
    submission = parse_submission(event)

    subject = os.environ.get("MAIL_SUBJECT", f"{submission.form_title} submission")
    body = os.environ.get("MAIL_BODY", "Attached is the generated PDF from the Google Form submission.")
    filename = os.environ.get("PDF_FILENAME", "submission.pdf")

    pdf = build_pdf_bytes(
        title=f"{submission.form_title} — Submission",
        fields={"submission_id": submission.submission_id, "timestamp": submission.timestamp, **submission.fields},
    )

    smtp = load_smtp_config()
    send_pdf(smtp, submission.email_to, subject, body, filename, pdf)

    print(json.dumps({
        "status": "ok",
        "submission_id": submission.submission_id,
        "recipients": submission.email_to
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
