from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Submission:
    submission_id: str
    form_title: str
    timestamp: str
    email_to: List[str]

    # Legacy schema-driven payload
    fields: Dict[str, Any]

    # New form-driven payload
    sections: Optional[List[Dict[str, Any]]] = None
    contact_consent: str = "no"


def parse_submission(event: Dict[str, Any]) -> Submission:
    payload = (event.get("client_payload") or {})

    email_to = payload.get("email_to") or []
    if isinstance(email_to, str):
        email_to = [email_to]

    submission_id = str(payload.get("submission_id") or payload.get("complaint_id") or "").strip()

    timestamp = str(
        payload.get("timestamp")
        or payload.get("submission_timestamp")
        or ""
    ).strip()

    sub = Submission(
        submission_id=submission_id,
        form_title=str(payload.get("form_title") or "Customer Complaint Form").strip(),
        timestamp=timestamp,
        email_to=[str(x).strip() for x in email_to if str(x).strip()],
        fields=dict(payload.get("fields") or {}),
        sections=payload.get("sections"),
        contact_consent=str(payload.get("contact_consent") or "no").strip().lower() or "no",
    )

    if not sub.submission_id:
        raise ValueError("Missing submission_id in client_payload.")
    if not sub.email_to:
        raise ValueError("No recipients provided (email_to is empty).")

    return sub
