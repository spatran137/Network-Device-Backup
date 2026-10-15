"""Small, read-only configuration backup engine for Netmiko-supported switches.

No network connection is made during import. The legacy application remains
separate until the adapters have been tested on representative hardware.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Callable
import json
import os
import re
import tempfile


# Do not enable other device families until their commands and backup formats
# have been verified on hardware. In particular airOS != EdgeSwitch.
COMMANDS = {
    "cisco_ios": "show running-config",
    "ubiquiti_edgeswitch": "show running-config",
}
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
ENV_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
ERROR_RE = re.compile(
    r"(?im)^\s*(?:%\s*(?:invalid input|ambiguous command|error)|"
    r"(?:error|permission denied|authentication denied|access denied)\s*[:!])"
)


class BackupError(Exception):
    """An expected inventory, transport, or backup validation failure."""


@dataclass(frozen=True)
class Device:
    name: str
    host: str
    device_type: str
    username_env: str
    password_env: str
    enable_secret_env: str | None = None
    port: int = 22


@dataclass(frozen=True)
class BackupResult:
    name: str
    path: Path
    bytes_written: int
    sha256_hex: str


def load_inventory(path: str | Path) -> list[Device]:
    """Load an explicit, non-secret JSON inventory. Reject unsupported types."""
    try:
        parsed = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BackupError("Cannot load or parse inventory JSON") from exc
    if not isinstance(parsed, dict) or not isinstance(parsed.get("devices"), list):
        raise BackupError("Inventory must be an object containing a devices list")

    devices: list[Device] = []
    seen: set[str] = set()
    for index, item in enumerate(parsed["devices"], start=1):
        if not isinstance(item, dict):
            raise BackupError(f"Device {index}: expected an object")
        required = ("name", "host", "device_type", "username_env", "password_env")
        if any(not isinstance(item.get(k), str) or not item[k].strip() for k in required):
            raise BackupError(f"Device {index}: missing or invalid required field")
        name = item["name"]
        if not NAME_RE.fullmatch(name) or name in {".", ".."}:
            raise BackupError(f"Device {index}: name must be a safe filename component")
        if name.casefold() in seen:
            raise BackupError(f"Device {index}: duplicate device name")
        seen.add(name.casefold())
        if not isinstance(item["host"], str) or any(ch.isspace() for ch in item["host"]):
            raise BackupError(f"Device {index}: invalid hostname or IP address")
        kind = item["device_type"]
        if kind not in COMMANDS:
            raise BackupError(f"Device {index}: unsupported device type {kind!r}")
        for key in ("username_env", "password_env", "enable_secret_env"):
            value = item.get(key)
            if value is not None and (not isinstance(value, str) or not ENV_RE.fullmatch(value)):
                raise BackupError(f"Device {index}: invalid environment-variable name in {key}")
        port = item.get("port", 22)
        if type(port) is not int or not 1 <= port <= 65535:
            raise BackupError(f"Device {index}: port must be 1 through 65535")
        devices.append(Device(name=name, host=item["host"], device_type=kind,
                              username_env=item["username_env"], password_env=item["password_env"],
                              enable_secret_env=item.get("enable_secret_env"), port=port))
    return devices


def validate_output(output: str) -> str:
    """Reject evident command errors, empty/implausibly short output and pagination."""
    if not isinstance(output, str):
        raise BackupError("Backup command returned non-text output")
    normalized = output.replace("\r\n", "\n").replace("\r", "\n").strip() + "\n"
    if len(normalized.strip()) < 32:
        raise BackupError("Configuration is empty or unexpectedly short")
    if ERROR_RE.search(normalized):
        raise BackupError("Device reported a command or permission error")
    if "--More--" in normalized or "<--- More --->" in normalized:
        raise BackupError("Configuration appears paginated or truncated")
    return normalized


def _netmiko_connect(**options):
    from netmiko import ConnectHandler
    return ConnectHandler(**options)


def backup_device(
    device: Device,
    output_root: str | Path,
    known_hosts: str | Path,
    *,
    connector: Callable | None = None,
) -> BackupResult:
    """Read a running configuration and write it atomically with restrictive mode.

    Strict SSH host verification is required. Known hosts must be enrolled by
    the operator out of band, not silently accepted by the application.
    """
    if device.device_type not in COMMANDS:
        raise BackupError("Unsupported device type")
    hostfile = Path(known_hosts).expanduser()
    if not hostfile.is_file() or hostfile.stat().st_size == 0:
        raise BackupError("A populated SSH known_hosts file is required")
    username = os.environ.get(device.username_env)
    password = os.environ.get(device.password_env)
    if not username or not password:
        raise BackupError(f"Missing credentials in environment for {device.name}")
    enable_secret = None
    if device.enable_secret_env:
        enable_secret = os.environ.get(device.enable_secret_env)
        if not enable_secret:
            raise BackupError(f"Missing enable secret in environment for {device.name}")

    options = dict(
        device_type=device.device_type,
        host=device.host,
        port=device.port,
        username=username,
        password=password,
        ssh_strict=True,
        system_host_keys=False,
        alt_host_keys=True,
        alt_key_file=str(hostfile.resolve()),
        allow_agent=False,
        use_keys=False,
        conn_timeout=15,
        auth_timeout=15,
        banner_timeout=15,
        timeout=15,
    )
    if enable_secret is not None:
        options["secret"] = enable_secret
    connect = connector or _netmiko_connect
    connection = connect(**options)
    try:
        if enable_secret is not None:
            connection.enable()
        output = connection.send_command(COMMANDS[device.device_type], read_timeout=60)
    finally:
        connection.disconnect()

    contents = validate_output(output)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = Path(output_root) / device.device_type / device.name
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    filename = directory / f"{stamp}.cfg"
    # Same-filesystem temporary file + atomic replace avoids partial backups.
    tmpname: str | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=directory, prefix=".partial-", delete=False) as temporary:
            tmpname = temporary.name
            os.chmod(tmpname, 0o600)
            temporary.write(contents)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(tmpname, filename)
    finally:
        if tmpname is not None and os.path.exists(tmpname):
            os.unlink(tmpname)
    data = contents.encode("utf-8")
    return BackupResult(name=device.name, path=filename,
                        bytes_written=len(data), sha256_hex=sha256(data).hexdigest())
