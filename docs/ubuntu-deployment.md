# Ubuntu deployment: experimental v1.1

The new CLI is read-only and currently enables only Cisco IOS / IOS-XE and Ubiquiti EdgeSwitch. **Do not replace working production backups before validating output and a restore on lab devices.** Use a non-privileged Linux service account and avoid committing secrets or backups to Git. This example targets **Ubuntu 24.04 LTS or newer** (systemd with encrypted-credential support).

## Install the application

```bash
sudo apt update
sudo apt install -y git python3-venv python3-pip openssh-client nano
sudo useradd --system --home-dir /var/lib/network-backup --shell /usr/sbin/nologin network-backup
# git clone creates its destination; do not create that directory first.
sudo git clone --branch modernization/v1.1 https://github.com/spatran137/Network-Device-Backup.git /opt/network-device-backup
sudo python3 -m venv /opt/network-device-backup/.venv
sudo /opt/network-device-backup/.venv/bin/python -m pip install -e /opt/network-device-backup
sudo install -d -o root -g root -m 0755 /etc/network-backup
sudo install -d -o network-backup -g network-backup -m 0700 /var/lib/network-backup
sudo install -d -o network-backup -g network-backup -m 0700 /var/lib/network-backup/backups
```

**Note:** If `/opt/network-device-backup` already exists, make sure it is empty or clone to another root-owned directory. Keep the source and Python virtualenv root-owned; the service should only write backup files under `/var/lib/network-backup/backups`.

## Inventory and host keys

Copy the version-controlled sample inventory and edit your **local** copy with Nano. The sample IPs below (`192.0.2.10` and `192.0.2.11`) are documentation placeholders, **not actual device addresses**.

```bash
sudo install -o root -g root -m 0644 /opt/network-device-backup/examples/devices.profiles.example.json /etc/network-backup/devices.json
sudo nano /etc/network-backup/devices.json
```

Example contents of `/etc/network-backup/devices.json`:

```json
{
  "devices": [
    {
      "name": "lab-catalyst",
      "host": "192.0.2.10",
      "device_type": "cisco_ios",
      "credential_profile": "cisco-switches"
    },
    {
      "name": "lab-edgeswitch",
      "host": "192.0.2.11",
      "device_type": "ubiquiti_edgeswitch",
      "credential_profile": "ubiquiti-switches"
    }
  ]
}
```

Replace `host` with each switch's management IP or DNS name; choose a unique, safe `name` for each device. `device_type` must be exactly `cisco_ios` or `ubiquiti_edgeswitch` for this experimental engine. `credential_profile` references a matching name in the **separate** `profiles.json` credential file below. Devices can share profiles if they use the same login. An optional `"port": 2222` field changes SSH from its default port 22. **Never put passwords in `devices.json`.**

**SSH host keys:** The engine requires a trusted `/etc/network-backup/known_hosts` file. Independently obtain each device's SSH host-key fingerprint from its console or another trusted channel. `ssh-keyscan` only retrieves the presented key; **it does not verify identity**. To stage keys for the two example IPs, run:

```bash
ssh-keyscan -T 10 192.0.2.10 192.0.2.11 > /tmp/network-backup-hostkeys
ssh-keygen -lf /tmp/network-backup-hostkeys
```

**STOP and compare** each fingerprint with its independently verified fingerprint. Only after both keys match, install the staged file:

```bash
sudo install -o root -g root -m 0644 /tmp/network-backup-hostkeys /etc/network-backup/known_hosts
rm /tmp/network-backup-hostkeys
```

Replace those IPs with your real host addresses in both commands. For a nonstandard SSH port, scan the host separately with `ssh-keyscan -p PORT HOST`; the corresponding `known_hosts` entry must match `[host]:port`. If a key does not match, **do not install it**—investigate first.

Validate the device inventory without opening any device connections:

```bash
sudo /opt/network-device-backup/.venv/bin/network-backup --inventory /etc/network-backup/devices.json --list
```

`sudoedit` (equivalent to `sudo -e`) is also valid on Ubuntu, but this guide uses `sudo nano` consistently; Nano is installed in the prerequisite step.

## Set up encrypted credential profiles

The Python engine reads a JSON profile file; encryption is performed **by systemd**, not by the application. Profile names in the inventory must match the entries in the profile file. A profile can be shared among many devices. The example file contains **placeholder values only**.

1. Copy the placeholder credential template **outside the repository** as a root-owned, owner-readable-only file, then edit it. The filename is kept separate from `devices.json`:

```bash
sudo install -o root -g root -m 0600 /opt/network-device-backup/examples/credential-profiles.example.json /etc/network-backup/profiles.json
sudo nano /etc/network-backup/profiles.json
```

Example contents of `/etc/network-backup/profiles.json` (replace every placeholder with your own values):

```json
{
  "profiles": {
    "cisco-switches": {
      "username": "REPLACE_ME",
      "password": "REPLACE_ME",
      "enable_secret": "REPLACE_ME"
    },
    "ubiquiti-switches": {
      "username": "REPLACE_ME",
      "password": "REPLACE_ME"
    }
  }
}
```

`enable_secret` is optional; omit it if the Cisco device does not require a separate enable password. The `cisco-switches` and `ubiquiti-switches` keys must match the inventory's `credential_profile` values exactly. Do not commit this file, paste real passwords into shell command arguments, or give it group/world read access. Verify its permissions with `sudo stat -c '%a %U:%G %n' /etc/network-backup/profiles.json` (expected `600 root:root`).
2. Encrypt it on the deployment host:

```bash
sudo systemd-creds encrypt --name=profiles.json /etc/network-backup/profiles.json /etc/network-backup/profiles.json.cred
sudo chmod 0600 /etc/network-backup/profiles.json.cred
sudo chown root:root /etc/network-backup/profiles.json.cred
```

3. Remove the plaintext staging file once encryption is verified; use care with filesystem snapshots, SSDs and temporary editor files, because ordinary deletion does **not** guarantee forensic erasure. For best hygiene, stage initial plaintext in protected temporary memory rather than on persistent disk.
4. `LoadCredentialEncrypted=` in the service decrypts the profile file only when the service starts and exposes it under `%d/profiles.json`. The CLI receives its **path**, not secret values, so passwords are not exposed in process arguments or systemd unit environment variables.

For an initial deployment **without at-rest encryption**, change the service directive to `LoadCredential=profiles.json:/etc/network-backup/profiles.json` and keep the root-owned source file mode `0600`. This is portable but **not encrypted at rest**. Do not enable both credential directives. For non-systemd execution, pass the protected credential-file path directly via `--credentials-file`; the CLI rejects group/world-readable files on POSIX systems. Environment-variable-based inventory entries continue to work without a profiles file.

Systemd credentials are for unattended services, not a vault: root or a compromised account running the backup job may read the decrypted credentials. The encrypted file may also be bound to this installation/TPM, so maintain a secure recovery method for credentials during a server rebuild.

## Schedule and initial manual backup

```bash
sudo install -o root -g root -m 0644 /opt/network-device-backup/deploy/systemd/network-backup.service /etc/systemd/system/network-backup.service
sudo install -o root -g root -m 0644 /opt/network-device-backup/deploy/systemd/network-backup.timer /etc/systemd/system/network-backup.timer
sudo systemd-analyze verify /etc/systemd/system/network-backup.service /etc/systemd/system/network-backup.timer
systemd-analyze calendar '*-*-* 05:00:00'
sudo systemctl daemon-reload
# Carefully test one device first. Temporarily replace --all in ExecStart with
# --device lab-catalyst in the copied service, then reload systemd.
sudo systemctl start network-backup.service
sudo systemctl status network-backup.service --no-pager
sudo journalctl -u network-backup.service -n 60 --no-pager
# Check backup files, content, permissions, and independently test restoration.
# After hardware validation, restore --all in ExecStart, reload, and enable:
sudo systemctl enable --now network-backup.timer
systemctl list-timers network-backup.timer --all
```

The timer runs once per day at **05:00 server-local time**; verify the host time zone (`timedatectl`). `Persistent=true` requests a catch-up run when the timer was inactive and a scheduled event was missed, so enabling the timer may immediately start a backup. Do not enable it until device testing is complete. The service uses a root-owned venv, least-privileged Linux user, restrictive umask, and a writable backup directory only.

## Limitations and operational security

* Neither offline unit tests nor `systemd-analyze verify` can establish real-world device compatibility. Test `show running-config` output and restore on representative hardware.
* Backup files can include passwords, keys, and other secrets: restrict filesystem permissions, encrypt backup storage, apply retention, and avoid placing them in public shares or Git.
* SSH host keys must be verified outside the app. Unexpected key changes should be investigated, not accepted automatically.
* AirOS point-to-point radios, Ubiquiti TOUGHSwitch, Motorola RFS, and SonicWall remain disabled in the new engine pending separate adapters and testing.
* Root-owned file credentials, systemd encrypted credentials, environment variables, and future container secret mounts all work through the same provider-independent CLI interface. No Windows functionality is required.

Primary references: [systemd credentials](https://systemd.io/CREDENTIALS/), [systemd.exec](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html), [systemd.timer](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html).
