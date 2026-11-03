"""Configuración de la aplicación (variables de entorno / archivo .env).

Los secretos de EMOTIV (``EMOTIV_CLIENT_ID`` y ``EMOTIV_CLIENT_SECRET``) se leen
únicamente en el backend y jamás se exponen por la API ni al frontend.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
DEFAULT_CA_FILE = Path(__file__).resolve().parent / "acquisition" / "certs" / "emotiv_rootCA.pem"

# Streams que la aplicación está autorizada a pedir a Cortex. 'eeg' (licencia de pago)
# y 'met' (métricas de rendimiento/afectivas, restringidas) quedan fuera por diseño.
ALLOWED_EMOTIV_STREAMS = ("dev", "eq", "pow")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(PROJECT_DIR / ".env"), str(BACKEND_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # --- Backend ---
    database_url: str = Field(
        default=f"sqlite:///{(BACKEND_DIR / 'data' / 'neurosync.db').as_posix()}",
        alias="NEUROSYNC_DATABASE_URL",
    )
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        alias="NEUROSYNC_CORS_ORIGINS",
    )
    simulator_seed: int = Field(default=42, alias="NEUROSYNC_SIMULATOR_SEED")

    # Política de persistencia: las muestras se agregan (media) en ventanas de N segundos.
    persist_bin_seconds: float = Field(default=1.0, gt=0, alias="NEUROSYNC_PERSIST_BIN_SECONDS")
    # Mínimo de ventanas válidas para calcular estadísticas de una fase.
    min_valid_bins: int = Field(default=3, ge=1, alias="NEUROSYNC_MIN_VALID_BINS")

    # --- EMOTIV Cortex ---
    emotiv_url: str = Field(default="wss://localhost:6868", alias="EMOTIV_URL")
    emotiv_client_id: str = Field(default="", alias="EMOTIV_CLIENT_ID")
    emotiv_client_secret: SecretStr = Field(default=SecretStr(""), alias="EMOTIV_CLIENT_SECRET")
    emotiv_headset_id: str = Field(default="", alias="EMOTIV_HEADSET_ID")
    emotiv_ca_file: Path = Field(default=DEFAULT_CA_FILE, alias="EMOTIV_CA_FILE")
    emotiv_streams: list[str] = Field(default=list(ALLOWED_EMOTIV_STREAMS), alias="EMOTIV_STREAMS")
    emotiv_discovery_timeout_s: float = Field(default=15.0, alias="EMOTIV_DISCOVERY_TIMEOUT_S")
    emotiv_retry_delay_s: float = Field(default=5.0, alias="EMOTIV_RETRY_DELAY_S")

    @field_validator("emotiv_streams")
    @classmethod
    def _restrict_streams(cls, value: list[str]) -> list[str]:
        allowed = [s for s in value if s in ALLOWED_EMOTIV_STREAMS]
        return allowed or list(ALLOWED_EMOTIV_STREAMS)

    @property
    def has_emotiv_credentials(self) -> bool:
        return bool(self.emotiv_client_id.strip() and self.emotiv_client_secret.get_secret_value().strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()

