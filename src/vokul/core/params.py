from dataclasses import dataclass

@dataclass(frozen=True)
class Argon2Params:
    """Tunable Argon2id cost parameters matching modern security standards."""
    time_cost: int = 3
    memory_cost: int = 65536  # 64 MiB
    parallelism: int = 4
    salt_len: int = 16
    key_len: int = 32         # 256-bit key for AES-256