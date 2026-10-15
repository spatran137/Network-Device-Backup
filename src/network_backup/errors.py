"""Expected errors that can be reported without revealing secrets."""


class BackupError(Exception):
    """An expected inventory, transport, or backup validation failure."""
