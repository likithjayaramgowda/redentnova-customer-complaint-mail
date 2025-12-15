from __future__ import annotations
import json
import os
from typing import Any, Dict

from dotenv import load_dotenv

from app.dropbox_uploader import build_dropbox_path, load_dropbox_config, upload_pdf_and_get_link
from app.mailer import load_smtp_config, send_pdf
from app.payload import parse_submission
from app.pdf_report import build_pdf_bytes, build_pdf_bytes_dynamic



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
    body = os.environ.get("MAIL_BODY", "Attached is the generated PDF from the form submission.")
    filename = os.environ.get("PDF_FILENAME", "submission.pdf")

    title = f"{submission.form_title} — Submission"

# If sections exist -> fully dynamic, form-driven professional PDF
if submission.sections:
    pdf = build_pdf_bytes_dynamic(
        title=title,
        complaint_id=submission.submission_id,
        timestamp=submission.timestamp,
        status=os.environ.get("COMPLAINT_STATUS", "Received"),
        contact_consent=submission.contact_consent,
        sections=submission.sections,
    )
else:
    # Legacy: schema-driven PDF
    pdf = build_pdf_bytes(
        title=title,
        fields={"submission_id": submission.submission_id, "timestamp": submission.timestamp, **submission.fields},
    )


    # Optional: Upload to Dropbox (recommended, since it's the easiest durable archive)
    dropbox_cfg = load_dropbox_config()
    dropbox_path = None
    shared_link = None
    if dropbox_cfg:
        dropbox_path = build_dropbox_path(dropbox_cfg.base_folder, submission.submission_id)
        shared_link = upload_pdf_and_get_link(dropbox_cfg, dropbox_path, pdf)

        # Add the archive link to the internal email body
        if shared_link:
            body = body + f"\n\nDropbox archive link: {shared_link}\nDropbox path: {dropbox_path}"
        else:
            body = body + f"\n\nDropbox path: {dropbox_path}"

    smtp = load_smtp_config()
    send_pdf(smtp, submission.email_to, subject, body, filename, pdf)

    print(json.dumps({
        "status": "ok",
        "submission_id": submission.submission_id,
        "recipients": submission.email_to,
        "dropbox_path": dropbox_path,
        "dropbox_shared_link": shared_link,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
