import os
import secrets
from typing import Optional, Tuple
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

from .exceptions import VaultCryptoError
from .params import Argon2Params

class VaultEngine:
    """S"t"a"teful cryptographic session manager for a single vault."""
    NONCE_LEN = 12

    def __init__(self, params: Optional[Argon2Params] = None) -> None:
        self._params = params or Argon2Params()
        self._key: Optional[bytes] = None

    @property
    def is_unlocked(self) -> bool:
        return self._key is not None

    @staticmethod
    def generate_salt(length: int = 16) -> bytes:
        return secrets.token_bytes(length)

    def derive_key(self, master_password: str, salt: bytes) -> bytes:
        try:
            kdf = Argon2id(
                salt=salt,
                length=self._params.key_len,
                iterations=self._params.time_cost,
                lanes=self._params.parallelism,
                memory_cost=self._params.memory_cost,
            )
            self._key = kdf.derive(master_password.encode("utf-8"))
            return self._key
        except Exception as exc:
            raise VaultCryptoError("Key derivation failed.") from exc

    def unlock(self, master_password: str, salt: bytes) -> None:
        self.derive_key(master_password, salt)

    def lock(self) -> None:
        self._key = None

    def encrypt(self, plaintext: bytes, associated_data: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        if not self._key:
            raise VaultCryptoError("Vault is locked. Call unlock() first.")
        nonce = os.urandom(self.NONCE_LEN)
        try:
            ciphertext = AESGCM(self._key).encrypt(nonce, plaintext, associated_data)
            return nonce, ciphertext
        except Exception as exc:
            raise VaultCryptoError("Encryption failed.") from exc

    def decrypt(self, nonce: bytes, ciphertext: bytes, associated_data: Optional[bytes] = None) -> bytes:
        if not self._key:
            raise VaultCryptoError("Vault is locked. Call unlock() first.")
        try:
            return AESGCM(self._key).decrypt(nonce, ciphertext, associated_data)
        except InvalidTag as exc:
            raise VaultCryptoError("Decryption failed: Invalid master password or corrupted data.") from exc
        except Exception as exc:
            raise VaultCryptoError("Decryption failed.") from exc
