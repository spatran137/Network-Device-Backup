"""Command-line entry point. Does not connect unless --device or --all is set."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .engine import BackupError, backup_device, load_inventory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Experimental v1.1 read-only network backups")
    parser.add_argument("--inventory", type=Path, required=True, help="JSON device inventory")
    parser.add_argument("--output", type=Path, default=Path("backups"))
    parser.add_argument("--known-hosts", type=Path, default=Path.home() / ".ssh" / "known_hosts")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List devices without network access")
    group.add_argument("--device", help="Back up exactly one named device")
    group.add_argument("--all", action="store_true", help="Back up all inventory devices")
    args = parser.parse_args(argv)

    try:
        devices = load_inventory(args.inventory)
    except BackupError as exc:
        print(f"Inventory error: {exc}", file=sys.stderr)
        return 2
    if args.list:
        for d in devices:
            print(f"{d.name}\t{d.device_type}\t{d.host}")
        return 0
    if args.device:
        devices = [d for d in devices if d.name == args.device]
        if not devices:
            print("Requested device not found", file=sys.stderr)
            return 2
    if not devices:
        print("No devices selected", file=sys.stderr)
        return 2
    failures = 0
    for device in devices:
        try:
            result = backup_device(device, args.output, args.known_hosts)
            print(f"OK {result.name}: {result.bytes_written} bytes, SHA256 {result.sha256_hex} -> {result.path}")
        except (BackupError, OSError) as exc:
            # Expected failures do not expose credentials or CLI session output.
            print(f"FAILED {device.name}: {exc}", file=sys.stderr)
            failures += 1
        except Exception as exc:
            # Third-party connection exceptions can contain sensitive details.
            print(f"FAILED {device.name}: {type(exc).__name__} (details withheld)", file=sys.stderr)
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
