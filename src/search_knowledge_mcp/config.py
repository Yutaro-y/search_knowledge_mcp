"""設定モジュール。

このモジュールでは、MCPサーバ全体で利用する環境変数を一元管理します。
配布後は、MCPクライアントがサーバ起動時に渡すプロセス環境変数を主な設定源として扱い、
`.env` はローカル開発・手元検証を補助するための任意手段として扱います。
将来 GitHub / PyPI 公開することを見据え、設定値の意味が第三者にも伝わるよう
明示的なフィールド名とコメント方針を採用しています。
"""

from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """アプリケーション設定。

    起動時の環境変数を優先しつつ、必要に応じて `.env` からも値を読み取り、
    検索クライアントやMCPサーバの挙動を制御します。
    MCPクライアントごとに異なる API キーを渡せるよう、配布利用時は
    環境変数経由の設定を前提とします。
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    openai_base_url: str | None = Field(
        default="https://api.openai.com/v1",
        alias="OPENAI_BASE_URL",
    )
    openai_timeout_seconds: int = Field(default=30, alias="OPENAI_TIMEOUT_SECONDS")
    default_language: str = Field(default="ja", alias="DEFAULT_LANGUAGE")
    default_max_results: int = Field(default=8, alias="DEFAULT_MAX_RESULTS")
    default_freshness_days: int = Field(default=365, alias="DEFAULT_FRESHNESS_DAYS")
    search_provider: str = Field(default="openai", alias="SEARCH_PROVIDER")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("openai_base_url", mode="before")
    @classmethod
    def normalize_openai_base_url(cls, value: str | None) -> str | None:
        """空文字や空白のみの値を None に正規化します。"""

        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("openai_model", mode="before")
    @classmethod
    def normalize_openai_model(cls, value: str) -> str:
        """モデル名の前後空白を除去します。"""

        return value.strip()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """設定をキャッシュして返します。"""

    return Settings()
