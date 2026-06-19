import base64
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .crypto import VaultEngine
from .exceptions import VaultStorageError

class VaultManager:
    
    def __init__(self, filepath: Path, engine: VaultEngine) -> None:
        self.filepath = Path(filepath)
        self.engine = engine
        self._records: Dict[str, List[str]] = {}

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
            if isinstance(v, str):
                self._records[k] = [v]
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

    def set_secret(self, service: str, password: str) -> None:
        if service in self._records:
            if self._records[service][0] != password:
                self._records[service].insert(0, password)
                self._records[service] = self._records[service][:3]
        else:
            self._records[service] = [password]

    def get_secret(self, service: str) -> Optional[str]:
        if service in self._records and self._records[service]:
            return self._records[service][0]
        return None

    def get_history(self, service: str) -> List[str]:
        return self._records.get(service, [])

    def list_services(self) -> List[str]:
        return sorted(self._records.keys())

    def search_services(self, query: str) -> List[str]:
        query_lower = query.lower()
        return sorted(k for k in self._records.keys() if query_lower in k.lower())
