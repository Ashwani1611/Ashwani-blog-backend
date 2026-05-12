from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./blog.db"

    # JWT
    secret_key: str = "dev-secret-change-in-prod"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # Gemini AI
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # Cloudinary
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    # App
    app_name: str = "Ashwani Kumar Blog API"
    debug: bool = True
    frontend_origins: str = "http://localhost:3000,http://127.0.0.1:5500"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()