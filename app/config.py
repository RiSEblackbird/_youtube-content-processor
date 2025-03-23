import os
from typing import Dict, Optional, Any
from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    アプリケーション設定を管理するクラス
    環境変数から設定を読み込み、適切な型に変換する
    """
    # アプリケーション設定
    PROJECT_NAME: str = "YouTube Content Processor"
    API_V1_STR: str = "/api/v1"
    
    # データベース設定
    DB_HOST: str
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_PORT: str = "5432"
    DATABASE_URI: Optional[PostgresDsn] = None

    @field_validator("DATABASE_URI", mode='before')
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        """
        データベースURIを構築するバリデータ
        各コンポーネント（ホスト、ユーザー、パスワードなど）から完全なURIを作成する
        """
        if isinstance(v, str):
            return v
        
        return PostgresDsn.build(
            scheme="postgresql",
            username=values.data.get("DB_USER"),
            password=values.data.get("DB_PASSWORD"),
            host=values.data.get("DB_HOST"),
            port=values.data.get("DB_PORT"),
            path=f"{values.data.get('DB_NAME') or ''}",
        )
    
    # API認証設定
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8日間
    
    # 外部APIキー設定
    ANTHROPIC_API_KEY: str
    OPENAI_API_KEY: str

    # GCP設定
    GCP_PROJECT_ID: str
    GCP_REGION: str = "us-central1"
    
    # ロギング設定
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


# 設定インスタンスの作成
settings = Settings()
