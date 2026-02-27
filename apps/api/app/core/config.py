from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Harmful Content Detector API"
    database_url: str = "postgresql+psycopg2://hcd_user:hcd_password@localhost:5432/harmful_content"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change_me_super_secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120
    demo_mode: bool = True
    twitter_bearer_token: str = ""
    twitter_default_query: str = "(violence OR abuse OR murder OR hate speech OR fight OR weapon) (lang:en OR lang:si)"
    twitter_poll_interval_sec: int = 30
    facebook_page_access_token: str = ""
    facebook_page_ids: str = ""
    facebook_poll_interval_sec: int = 60
    yolo_weights_path: str = "/app/models/yolo/weights.pt"
    nlp_model_path: str = "/app/models/nlp"
    nlp_adapter_path: str = "/app/models/nlp/infer.py"
    nlp_label_map_json: str = ""
    hf_model_url: str = ""
    hf_api_token: str = ""
    hf_timeout_sec: int = 30
    whisper_model: str = "small"
    violence_class_keywords: str = "knife,gun,weapon,fight,blood,violence"
    fusion_text_w: float = 0.4
    fusion_video_w: float = 0.4
    fusion_audio_w: float = 0.2
    alert_threshold: int = 70
    media_root: str = "/app/storage"
    demo_input_dir: str = "/app/data/demo_inputs"
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def violence_class_keywords_list(self) -> List[str]:
        return [value.strip().lower() for value in self.violence_class_keywords.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
