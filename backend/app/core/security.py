from cryptography.fernet import Fernet

from app.config import get_settings


class Encryption:
    _fernet: Fernet | None = None

    @classmethod
    def _get_fernet(cls) -> Fernet:
        if cls._fernet is None:
            settings = get_settings()
            key = settings.ENCRYPTION_KEY
            if not key:
                raise ValueError("ENCRYPTION_KEY is not configured")
            cls._fernet = Fernet(key.encode() if len(key) == 44 else key.encode())
        return cls._fernet

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        return cls._get_fernet().encrypt(plaintext.encode()).decode()

    @classmethod
    def decrypt(cls, ciphertext: str) -> str:
        return cls._get_fernet().decrypt(ciphertext.encode()).decode()

    @classmethod
    def mask(cls, value: str) -> str:
        if len(value) <= 8:
            return "****"
        return value[:4] + "****" + value[-4:]
