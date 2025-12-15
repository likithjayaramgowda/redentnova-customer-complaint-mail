import os
from dotenv import load_dotenv

from app.payload import load_event, parse_submission
from app.pdf_report import build_pdf_bytes, build_pdf_bytes_dynamic
from app.mailer import send_mail


def main():
    # --------------------------------------------------
    # Local convenience (safe in GitHub Actions as well)
    # --------------------------------------------------
    load_dotenv()

    # --------------------------------------------------
    # 1. Load GitHub repository_dispatch payload
    # --------------------------------------------------
    event = load_event()

    # --------------------------------------------------
    # 2. Parse payload into Submission object
    # --------------------------------------------------
    submission = parse_submission(event)

    # --------------------------------------------------
    # 3. Prepare common values
    # --------------------------------------------------
    title = f"{submission.form_title} – Customer Complaint"
    filename = f"{submission.submission_id}.pdf"

    subject = os.environ.get(
        "MAIL_SUBJECT",
        f"{submission.form_title} – Complaint {submission.submission_id}",
    )

    body = os.environ.get(
        "MAIL_BODY",
        "Attached is the generated customer complaint PDF.",
    )

    # --------------------------------------------------
    # 4. Generate PDF
    #    Dynamic if sections exist, else legacy fallback
    # --------------------------------------------------
    if submission.sections:
        pdf_bytes = build_pdf_bytes_dynamic(
            title=title,
            complaint_id=submission.submission_id,
            timestamp=submission.timestamp,
            status=submission.status,
            contact_consent=submission.contact_consent,
            sections=submission.sections,
        )
    else:
        pdf_bytes = build_pdf_bytes(
            title=title,
            fields={
                "submission_id": submission.submission_id,
                "timestamp": submission.timestamp,
                **submission.fields,
            },
        )

    # --------------------------------------------------
    # 5. Send email
    #    (lab always included, customer only if consent=yes)
    # --------------------------------------------------
    send_mail(
        subject=subject,
        body=body,
        pdf_bytes=pdf_bytes,
        filename=filename,
        recipients=submission.email_to,
    )


if __name__ == "__main__":
    main()
