"""Validate that a string is an allowed storage link (Google Drive, Dropbox, OneDrive, etc.)."""
import re
from urllib.parse import urlparse

ALLOWED_LINK_HOSTS = (
    "drive.google.com",
    "docs.google.com",
    "www.drive.google.com",
    "www.docs.google.com",
    "dropbox.com",
    "www.dropbox.com",
    "dl.dropbox.com",
    "1drv.ms",
    "onedrive.live.com",
    "sharepoint.com",
    "*.sharepoint.com",
)


def is_allowed_drive_link(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if not url.startswith("https://"):
        return False
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        if not host:
            return False
        # Remove port
        if ":" in host:
            host = host.split(":")[0]
        for allowed in ALLOWED_LINK_HOSTS:
            if allowed.startswith("*."):
                pattern = allowed.replace(".", r"\.").replace("*", r".*")
                if re.match(pattern + r"$", host):
                    return True
            if host == allowed or host.endswith("." + allowed):
                return True
        return False
    except Exception:
        return False
