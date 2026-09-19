from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Lumina Stars"
    app_env: str = "development"
    debug: bool = False
    secret_key: str = Field(default="change-me-in-production-please-32chars")
    jwt_secret: str = Field(default="change-me-jwt-secret-please-32chars")
    jwt_ttl_hours: int = 24 * 14

    database_url: str = "sqlite:///./lumina.db"
    redis_url: Optional[str] = None

    cors_origins: str = "*"

    telegram_bot_token: str = ""
    telegram_webapp_url: str = ""
    telegram_webhook_secret: str = "lumina-hook"
    telegram_bot_username: str = ""

    tgstars_api_url: str = "https://tgstars.tg/api/v1/client"
    tgstars_api_key: str = ""

    demo_mode: bool = True
    demo_login_enabled: bool = True
    bootstrap_balance_rub: str = "5000.00"
    fallback_star_price_rub: str = "1.32"

    tgstars_enabled: bool = False
    payments_enabled: bool = True
    referral_enabled: bool = True
    referral_percent: str = "5"
    mirrors_enabled: bool = True

    trust_pay_fee_percent: str = "3"
    trust_pay_min_amount: str = "30.00"
    trust_pay_card_number: str = "5599002144955509"
    trust_pay_card_holder: str = ""
    trust_pay_expire_minutes: int = 60
    yoomoney_wallet: str = "4100119621450464"

    owner_telegram_id: int = 8565986003

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        if url.startswith("postgresql://") and "sslmode=" not in url:
            if "render.com" in url:
                url += ("&" if "?" in url else "?") + "sslmode=require"
        return url

    @property
    def is_sqlite(self) -> bool:
        return self.sqlalchemy_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
