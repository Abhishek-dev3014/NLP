from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT / '.env'), extra='ignore')
    database_url: str = f'sqlite:///{ROOT / "verifact.db"}'
    model_type: str = 'baseline'
    model_path: str = str(ROOT / 'artifacts/baseline.joblib')
    metrics_path: str = str(ROOT / 'artifacts/metrics.json')
    session_secret: str = ''
    frontend_origin: str = 'http://127.0.0.1:3000'
    cookie_secure: bool = False
    fact_check_api_key: str = ''
    evidence_enabled: bool = False
    uncertainty_threshold: float = 0.65
    max_text_chars: int = 60000
    max_upload_bytes: int = 5 * 1024 * 1024

settings = Settings()
