"""Portable credential-profile loader; plaintext is never logged.

The operating environment owns encryption and access controls. A systemd
service can supply a decrypted, read-only runtime file via LoadCredentialEncrypted.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import stat
from typing import Mapping

from .errors import BackupError


@dataclass(frozen=True)
class Credential:
    username: str
    password: str
    enable_secret: str | None = None


def load_profiles(path: Path | str) -> Mapping[str, Credential]:
    """Read protected JSON profiles, rejecting files accessible by group/others.

    A root-only source is fine for systemd: it makes a separate credential file
    readable to the service account at activation time.
    """
    source = Path(path).expanduser()
    try:
        info = source.stat()
        if not stat.S_ISREG(info.st_mode):
            raise BackupError("Credentials path must be a regular file")
        if os.name == "posix" and stat.S_IMODE(info.st_mode) & 0o077:
            raise BackupError("Credentials file permissions must be owner-only (0600 or stricter)")
        with source.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, UnicodeError, ValueError) as exc:
        raise BackupError("Could not load credential profiles") from exc
    if not isinstance(data, dict) or not isinstance(data.get("profiles"), dict):
        raise BackupError("Credentials file must have a profiles object")
    result: dict[str, Credential] = {}
    for name, item in data["profiles"].items():
        if not isinstance(name, str) or not name or not isinstance(item, dict):
            raise BackupError("Invalid credential profile entry")
        username, password = item.get("username"), item.get("password")
        secret = item.get("enable_secret")
        if not isinstance(username, str) or not username or not isinstance(password, str) or not password:
            raise BackupError("Credential profile is missing a username or password")
        if secret is not None and (not isinstance(secret, str) or not secret):
            raise BackupError("Credential profile has an invalid enable secret")
        result[name] = Credential(username, password, secret)
    return result
