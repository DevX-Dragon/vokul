import base64
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .crypto import VaultEngine
from .exceptions import VaultStorageError

class VaultManager:
    def __init__(self, filepath: Path, engine: VaultEngine) -> None:
        self.filepath = Path(filepath)
        self.engine = engine
        # Data structure: {"service_name": {"pass": ["current", "old1", "old2"], "totp": "secret_key"}}
        self._records: Dict[str, Dict[str, Any]] = {}

    def exists(self) -> bool:
        return self.filepath.exists()

    def create_new_vault(self, master_password: str) -> None:
        salt = self.engine.generate_salt()
        self.engine.unlock(master_password, salt)
        self._records = {}
        self.save(salt)

    def load_and_decrypt(self, master_password: str) -> None:
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                payload = json.load(f)
            
            salt = base64.b64decode(payload["salt"])
            nonce = base64.b64decode(payload["nonce"])
            ciphertext = base64.b64decode(payload["ciphertext"])
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            raise VaultStorageError("Invalid or corrupted vault file format.") from exc

        self.engine.unlock(master_password, salt)
        plaintext_bytes = self.engine.decrypt(nonce, ciphertext)
        raw_records = json.loads(plaintext_bytes.decode("utf-8"))
        
        self._records = {}
        for k, v in raw_records.items():
            # Migration logic: if an old record is just a list, convert it to the new dict structure
            if isinstance(v, list):
                self._records[k] = {"pass": v, "totp": None}
            else:
                self._records[k] = v

    def backup_vault(self) -> None:
        if not self.exists():
            return
        backup_dir = self.filepath.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"{self.filepath.name}.bak_{timestamp}"
        shutil.copy2(self.filepath, backup_path)

    def save(self, salt: Optional[bytes] = None) -> None:
        if not self.engine.is_unlocked:
            raise VaultStorageError("Cannot save data while engine is locked.")
        
        if salt is None:
            with open(self.filepath, "r", encoding="utf-8") as f:
                salt = base64.b64decode(json.load(f)["salt"])

        # Auto-backup before saving changes
        self.backup_vault()
        
        plaintext_bytes = json.dumps(self._records).encode("utf-8")
        nonce, ciphertext = self.engine.encrypt(plaintext_bytes)

        payload = {
            "salt": base64.b64encode(salt).decode("utf-8"),
            "nonce": base64.b64encode(nonce).decode("utf-8"),
            "ciphertext": base64.b64encode(ciphertext).decode("utf-8")
        }

        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def set_secret(self, service: str, password: Optional[str] = None, totp_secret: Optional[str] = None) -> None:
        if service not in self._records:
            self._records[service] = {"pass": [], "totp": None}
        
        # Only add to history if a non-empty password is provided
        if password:
            if not self._records[service]["pass"] or self._records[service]["pass"][0] != password:
                self._records[service]["pass"].insert(0, password)
                self._records[service]["pass"] = self._records[service]["pass"][:3] # Keep last 3
        
        if totp_secret:
            self._records[service]["totp"] = totp_secret

    def get_secret(self, service: str) -> Optional[Dict[str, Any]]:
        return self._records.get(service)

    def get_history(self, service: str) -> List[str]:
        return self._records.get(service, {}).get("pass", [])

    def list_services(self) -> List[str]:
        return sorted(self._records.keys())

    def search_services(self, query: str) -> List[str]:
        query_lower = query.lower()
        return sorted(k for k in self._records.keys() if query_lower in k.lower())