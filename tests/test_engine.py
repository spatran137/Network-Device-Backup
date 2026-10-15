"""Offline tests. No hardware connections, no real credentials."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from network_backup.cli import main
from network_backup.engine import BackupError, Device, backup_device, load_inventory, validate_output


class FakeConnection:
    def __init__(self, response="! Current configuration\nhostname lab-switch\ninterface GigabitEthernet1/0/1\n"):
        self.response = response
        self.closed = False
        self.commands = []
        self.enabled = False

    def send_command(self, command, **kwargs):
        self.commands.append(command)
        return self.response

    def enable(self):
        self.enabled = True

    def disconnect(self):
        self.closed = True


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.hostfile = self.base / "known_hosts"
        self.hostfile.write_text("lab.example ssh-ed25519 FAKE_KEY_FOR_TESTING_ONLY\n", encoding="utf-8")
        self.device = Device("lab-switch", "lab.example", "cisco_ios", "LAB_USERNAME", "LAB_PASSWORD")
        self.patcher = patch.dict(os.environ, {"LAB_USERNAME": "test-user", "LAB_PASSWORD": "test-password"})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_success_and_strict_key_policy(self):
        fake = FakeConnection()
        kwargs = {}
        def connect(**options):
            kwargs.update(options)
            return fake
        result = backup_device(self.device, self.base / "backups", self.hostfile, connector=connect)
        self.assertEqual(fake.commands, ["show running-config"])
        self.assertTrue(fake.closed)
        self.assertTrue(kwargs["ssh_strict"])
        self.assertTrue(kwargs["alt_host_keys"])
        self.assertFalse(kwargs["system_host_keys"])
        self.assertEqual(result.bytes_written, len(result.path.read_bytes()))
        self.assertEqual(len(result.sha256_hex), 64)
        self.assertEqual(result.path.stat().st_mode & 0o777, 0o600)

    def test_device_requires_known_hosts(self):
        with self.assertRaisesRegex(BackupError, "known_hosts"):
            backup_device(self.device, self.base, self.base / "does-not-exist", connector=lambda **kw: None)

    def test_missing_environment_credential(self):
        with patch.dict(os.environ, {"LAB_PASSWORD": ""}):
            with self.assertRaisesRegex(BackupError, "Missing credentials"):
                backup_device(self.device, self.base, self.hostfile, connector=lambda **kw: None)

    def test_invalid_output_rejected_without_file(self):
        fake = FakeConnection("% Invalid input detected at '^' marker.\n")
        with self.assertRaises(BackupError):
            backup_device(self.device, self.base / "backups", self.hostfile, connector=lambda **kw: fake)
        self.assertTrue(fake.closed)
        self.assertFalse((self.base / "backups").exists())

    def test_bad_inventory_and_path_traversal_rejected(self):
        inventory = self.base / "devices.json"
        def sample(name="test-switch", typ="cisco_ios"):
            return {"devices": [{"name": name, "host": "192.0.2.10", "device_type": typ,
                                  "username_env": "LAB_USERNAME", "password_env": "LAB_PASSWORD"}]}
        inventory.write_text(json.dumps(sample("../escape")), encoding="utf-8")
        with self.assertRaisesRegex(BackupError, "safe filename"):
            load_inventory(inventory)
        inventory.write_text(json.dumps(sample(typ="airos")), encoding="utf-8")
        with self.assertRaisesRegex(BackupError, "unsupported device type"):
            load_inventory(inventory)
        inventory.write_text(json.dumps(sample()), encoding="utf-8")
        self.assertEqual(load_inventory(inventory)[0].name, "test-switch")

    def test_list_has_no_connections(self):
        inventory = self.base / "devices.json"
        inventory.write_text(json.dumps({"devices": [{"name": "test-switch", "host": "192.0.2.10",
            "device_type": "ubiquiti_edgeswitch", "username_env": "LAB_USERNAME", "password_env": "LAB_PASSWORD"}]}), encoding="utf-8")
        self.assertEqual(main(["--inventory", str(inventory), "--list"]), 0)

    def test_pagination_rejected(self):
        with self.assertRaisesRegex(BackupError, "paginated"):
            validate_output("! Current config\nhostname lab-switch\n" + "--More--\n")


if __name__ == "__main__":
    unittest.main()
