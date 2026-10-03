from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str = ""
    # HTTPS-адрес Mini App (туннель или сервер): кнопка меню бота и «Открыть Каплю».
    webapp_url: str = ""
    database_url: str = "postgresql+asyncpg://kaplya:kaplya@localhost:5433/kaplya"
    cors_origins: list[str] = []

    # initData старше этого считается просроченной.
    init_data_max_age_seconds: int = 24 * 60 * 60

    # Только для разработки: при DEBUG=1 запросы без initData идут от имени DEV_USER_ID.
    debug: bool = False
    dev_user_id: int | None = None

    default_timezone: str = "Europe/Moscow"

    @field_validator("dev_user_id", mode="before")
    @classmethod
    def empty_is_none(cls, v: object) -> object:
        # «DEV_USER_ID=» в .env — значит, не задан.
        return None if v == "" else v


settings = Settings()
