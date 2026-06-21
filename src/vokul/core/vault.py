import base64
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .crypto import VaultEngine
from .exceptions import VaultStorageError

class VaultManager:
    def __init__(self, filepath: Path, engine: VaultEngine) -> None:
        self.filepath = Path(filepath)
        self.engine = engine
        self._records: Dict[str, Dict[str, Any]] = {}

    def exists(self) -> bool:
        # The vault exists if the main file is there...
        if self.filepath.exists():
            return True
        # OR if the main file is missing but backups exist!
        backup_dir = self.filepath.parent / "backups"
        if backup_dir.exists() and list(backup_dir.glob(f"{self.filepath.name}.bak_*")):
            return True
        return False

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
            
            self.engine.unlock(master_password, salt)
            plaintext_bytes = self.engine.decrypt(nonce, ciphertext)
            
        except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError) as exc:
            # Main vault file missing OR corrupted: Attempt self-healing from backups
            backup_records = self._attempt_backup_recovery(master_password)
            if backup_records is not None:
                if isinstance(exc, FileNotFoundError):
                    print("\n⚠️  Notice: Main vault file missing! Restored automatically from latest backup.", file=sys.stderr)
                else:
                    print("\n⚠️  Warning: Main vault file corrupted! Restored automatically from latest backup.", file=sys.stderr)
                self._records = backup_records
                self.save()  # This will instantly repair/recreate the missing main file
                return
                
            if isinstance(exc, FileNotFoundError):
                raise VaultStorageError("Vault file is missing and no valid backups were found.") from exc
            raise VaultStorageError("Corrupted vault file format and backup recovery failed.") from exc
            
        except Exception as exc:
            # Decryption failed (usually wrong password, but could be severe corruption)
            backup_records = self._attempt_backup_recovery(master_password)
            if backup_records is not None:
                print("\n⚠️  Warning: Main file decryption failed! Restored automatically from latest valid backup.", file=sys.stderr)
                self._records = backup_records
                self.save()
                return
            raise VaultStorageError("Invalid master password or unreadable vault data.") from exc

        raw_records = json.loads(plaintext_bytes.decode("utf-8"))
        self._records = {}
        for k, v in raw_records.items():
            if isinstance(v, list):
                self._records[k] = {"pass": v, "totp": None}
            else:
                self._records[k] = v

    def _attempt_backup_recovery(self, master_password: str) -> Optional[Dict[str, Any]]:
        backup_dir = self.filepath.parent / "backups"
        if not backup_dir.exists():
            return None
            
        backups = sorted(backup_dir.glob(f"{self.filepath.name}.bak_*"), key=lambda p: p.stat().st_mtime, reverse=True)
        for backup_path in backups:
            try:
                with open(backup_path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                salt = base64.b64decode(payload["salt"])
                nonce = base64.b64decode(payload["nonce"])
                ciphertext = base64.b64decode(payload["ciphertext"])
                
                self.engine.unlock(master_password, salt)
                plaintext_bytes = self.engine.decrypt(nonce, ciphertext)
                raw_records = json.loads(plaintext_bytes.decode("utf-8"))
                
                recovered: Dict[str, Dict[str, Any]] = {}
                for k, v in raw_records.items():
                    if isinstance(v, list):
                        recovered[k] = {"pass": v, "totp": None}
                    else:
                        recovered[k] = v
                return recovered
            except Exception:
                continue  # Password might be wrong, or this backup is also corrupted. Try the next older one.
        return None

    def backup_vault(self) -> None:
        # Prevent trying to backup a file that doesn't exist yet (important during recovery)
        if not self.filepath.exists():
            return
        backup_dir = self.filepath.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"{self.filepath.name}.bak_{timestamp}"
        shutil.copy2(self.filepath, backup_path)

    def save(self, salt: Optional[bytes] = None) -> None:
        if not self.engine.is_unlocked:
            raise VaultStorageError("Cannot save data while engine is locked.")
        
        if salt is None and self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    salt = base64.b64decode(json.load(f)["salt"])
            except Exception:
                pass
                
        if salt is None:
            salt = self.engine.generate_salt()

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
        
        if password:
            if not self._records[service]["pass"] or self._records[service]["pass"][0] != password:
                self._records[service]["pass"].insert(0, password)
                self._records[service]["pass"] = self._records[service]["pass"][:3]
        
        if totp_secret:
            self._records[service]["totp"] = totp_secret

    def delete_secret(self, service: str) -> bool:
        if service in self._records:
            del self._records[service]
            return True
        return False

    def get_secret(self, service: str) -> Optional[Dict[str, Any]]:
        return self._records.get(service)

    def export_vault_data(self) -> Dict[str, Any]:
        return self._records

    def get_history(self, service: str) -> List[str]:
        return self._records.get(service, {}).get("pass", [])

    def list_services(self) -> List[str]:
        return sorted(self._records.keys())

    def search_services(self, query: str) -> List[str]:
        query_lower = query.lower()
        return sorted(k for k in self._records.keys() if query_lower in k.lower())