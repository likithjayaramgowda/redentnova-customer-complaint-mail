from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass(frozen=True)
class DropboxConfig:
    access_token: str
    base_folder: str
    create_shared_link: bool


def load_dropbox_config() -> Optional[DropboxConfig]:
    """Load Dropbox settings from environment.

    If DROPBOX_ACCESS_TOKEN is not set, Dropbox upload is disabled.
    """
    token = (os.environ.get("DROPBOX_ACCESS_TOKEN") or "").strip()
    if not token:
        return None

    base_folder = (os.environ.get("DROPBOX_BASE_FOLDER") or "/ReDentNova/Complaints").strip()
    if not base_folder.startswith("/"):
        base_folder = "/" + base_folder

    create_link = (os.environ.get("DROPBOX_CREATE_SHARED_LINK") or "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
    }

    return DropboxConfig(access_token=token, base_folder=base_folder, create_shared_link=create_link)


def _dropbox_api_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def build_dropbox_path(base_folder: str, submission_id: str, when_utc: Optional[dt.datetime] = None) -> str:
    when_utc = when_utc or dt.datetime.utcnow()
    y = when_utc.strftime("%Y")
    m = when_utc.strftime("%m")
    d = when_utc.strftime("%d")
    safe_id = submission_id.replace(":", "-").replace("#", "-").replace("/", "-")
    return f"{base_folder}/Submissions/{y}/{m}/{d}/complaint_{safe_id}.pdf"


def upload_pdf_and_get_link(cfg: DropboxConfig, dropbox_path: str, pdf_bytes: bytes) -> Optional[str]:
    """Uploads the PDF to Dropbox.

    Returns a shared link URL if enabled, otherwise None.
    """
    upload_url = "https://content.dropboxapi.com/2/files/upload"
    upload_headers = {
        **_dropbox_api_headers(cfg.access_token),
        "Content-Type": "application/octet-stream",
        "Dropbox-API-Arg": json.dumps(
            {
                "path": dropbox_path,
                "mode": "add",
                "autorename": True,
                "mute": False,
            }
        ),
    }
    r = requests.post(upload_url, headers=upload_headers, data=pdf_bytes, timeout=30)
    r.raise_for_status()

    if not cfg.create_shared_link:
        return None

    # Try to create (or reuse) a shared link
    link_url = "https://api.dropboxapi.com/2/sharing/create_shared_link_with_settings"
    payload = {"path": dropbox_path, "settings": {"requested_visibility": "public"}}
    r2 = requests.post(link_url, headers={**_dropbox_api_headers(cfg.access_token), "Content-Type": "application/json"}, json=payload, timeout=30)

    if r2.status_code == 409:
        # Shared link already exists; fetch existing links
        list_url = "https://api.dropboxapi.com/2/sharing/list_shared_links"
        r3 = requests.post(
            list_url,
            headers={**_dropbox_api_headers(cfg.access_token), "Content-Type": "application/json"},
            json={"path": dropbox_path, "direct_only": True},
            timeout=30,
        )
        r3.raise_for_status()
        links = (r3.json() or {}).get("links") or []
        return str(links[0].get("url")) if links else None

    r2.raise_for_status()
    return str((r2.json() or {}).get("url"))
