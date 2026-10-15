# v1.1 modernization track (experimental)

This is a new, opt-in engine. The original scripts, schedule, and configuration
are deliberately unchanged. Do not switch production backups to this implementation
until it has been tested with real hardware and independently validated restorations.

## Supported by the new engine

| Device family | Status | Retrieval | Restoration confidence |
|---|---|---|---|
| Cisco Catalyst running Cisco IOS / IOS-XE | Implemented; hardware testing pending | Netmiko cisco_ios, show running-config | Not yet restore-tested |
| Ubiquiti EdgeSwitch | Implemented; hardware testing pending | Netmiko ubiquiti_edgeswitch, show running-config | Not yet restore-tested |
| Ubiquiti airOS point-to-point / airMAX radios | Planned adapter; not enabled | Determine airOS/firmware-specific safe retrieval | Not yet restore-tested |
| Ubiquiti TOUGHSwitch (not UniFi) | Planned adapter; production device | Verify supported backup export; avoid changes | Not yet restore-tested |
| Motorola RFS | Legacy-only; no current test device confirmed | Requires testing | Not yet restore-tested |
| SonicWall | Legacy-only; no test device available | Replace insecure FTP flow per SonicOS version | Not yet restore-tested |

## Local start (Python 3.11+)

1. Create a virtual environment and install: python -m pip install -e .
2. Copy examples/devices.example.json to devices.json. Change the device names,
   hosts, and credential environment-variable names. Do not put passwords in inventory.
3. Set the named environment variables using a protected service configuration.
4. Independently verify each SSH host key and add it to a dedicated OpenSSH
   known_hosts file. Do not automatically trust an unverified key.
   Ensure entries match the hostname or IP and, for nondefault ports, [host]:port.
5. List devices without any network access:
   network-backup --inventory devices.json --list
6. Back up one lab device only after confirming read-only commands:
   network-backup --inventory devices.json --device lab-catalyst --known-hosts ./known_hosts --output ./backups
7. Examine the resulting configuration file. A checksum and file-size check do
   not prove that the configuration can be restored. Test restoration on lab hardware.

The output path is backups/<device_type>/<device_name>/<UTC-timestamp>.cfg.
Writes are atomic with restrictive mode on POSIX. Device configurations may
contain embedded passwords and keys. Protect backup files with filesystem ACLs
and encrypted storage. Do not commit backups or credentials to GitHub.
Environment variables are a migration step; a secret manager is preferable for
a fuller deployment.

The engine uses read-only show commands. Optional privilege elevation through
enable mode may be required, but no configuration commands are sent.

## Design and validation rules

- Strict SSH host-key verification; unknown and changed keys are rejected.
- No credentials are stored in inventory JSON.
- Finite connection, authentication, and command timeouts.
- Empty, clearly failed, or paginated output is rejected. More robust
  device-specific completeness validation is still required.
- Backups are not logged; SHA-256 is computed for successful files.
- Offline tests simulate network connections. No physical devices were contacted.
- Vendor adapters will be reusable for a future Docker service.

## Deferred work

Hardware backup and restoration validation; vendor completeness rules;
credential secret store; encrypted storage; retention; backup manifests;
airOS, TOUGHSwitch, Motorola, and SonicWall adapters; integration tests;
optional scheduling, structured logging, and a Docker job runner.

## Licensing discrepancy

Existing LICENSE is GPL-3.0 text, source comments say LGPL-3.0, and README
describes MIT. Resolve this before changing license claims or redistributing.
