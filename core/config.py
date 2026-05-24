from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    groq_api_key: str
    gemini_api_key: str

    # Voice store path — where speaker voice prints are persisted
    voice_store_path: str = "voice_store/speakers.json"
    voice_audio_dir: str = "voice_store/audio"

    # Kept for backward compatibility — no longer used by speaker service
    speaker_similarity_threshold: float = 0.82

    # Gemini model — swap if free tier quota exhausted (gemini-1.5-flash has separate pool)
    gemini_model: str = "gemini-2.5-flash"

    # TTS endpoint — swapped in at hackathon
    tts_endpoint: str = "http://localhost:9000/synthesize"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Module-level singleton — import either `settings` or `get_settings()` interchangeably.
# Both refer to the same lru_cache'd instance.
settings = get_settings()