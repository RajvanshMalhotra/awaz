from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    groq_api_key: str
    silk_api_key: str
    sarvam_api_key: str
    silk_default_speaker: str = "speaker_1"
    silk_default_f0_up_key: int = 0
    user_profile_path: str = "user_profile.json"
    groq_llm_model: str = "llama-3.3-70b-versatile"
    tts_endpoint: str = "http://localhost:9000/synthesize"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Module-level singleton — import either `settings` or `get_settings()` interchangeably.
# Both refer to the same lru_cache'd instance.
settings = get_settings()
