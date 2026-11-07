from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_title: str = "Random Star Trek Picker"
    app_base_path: str = ""
    prime_video_domain: str = "www.amazon.de"
    request_timeout_seconds: float = 20.0
    cache_ttl_seconds: int = 3600
    user_agent: str = "random-star-trek-app/1.0"
    persist_filters: bool = False
    tmdb_api_token: str = ""
    tmdb_language: str = "en-US"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def normalized_base_path(self) -> str:
        value = self.app_base_path.strip()
        if not value or value == "/":
            return ""
        if not value.startswith("/"):
            value = f"/{value}"
        return value.rstrip("/")

    @property
    def normalized_prime_video_domain(self) -> str:
        value = self.prime_video_domain.strip().lower()
        if value.startswith("http://"):
            value = value.removeprefix("http://")
        if value.startswith("https://"):
            value = value.removeprefix("https://")
        return value.rstrip("/")


settings = Settings()
