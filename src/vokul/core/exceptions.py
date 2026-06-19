class VaultError(Exception):
    """Base exception for all VOKUL operations."""

class VaultCryptoError(VaultError):
    """Raised for failure during key derivation or AEAD operations."""

class VaultStorageError(VaultError):
    """Raised for file reading, writing, or parsing failures."""