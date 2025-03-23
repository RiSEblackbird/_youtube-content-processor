from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import video, report
from app.config import settings
from app.core.logging import logger
from app.db.session import engine
from app.db.models import Base

# データベースの初期化
Base.metadata.create_all(bind=engine)

# FastAPIアプリケーションの作成
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に制限すること
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターの登録
app.include_router(video.router, prefix=settings.API_V1_STR)
app.include_router(report.router, prefix=settings.API_V1_STR)


@app.get("/")
def read_root():
    """
    ルートエンドポイント
    アプリケーションが正常に動作していることを確認するためのシンプルなレスポンスを返す
    """
    return {
        "message": "YouTube Content Processor API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """
    ヘルスチェックエンドポイント
    アプリケーションの状態を確認するための情報を返す
    """
    return {
        "status": "healthy",
        "api_version": "v1"
    }


# アプリケーション起動時のロギング
@app.on_event("startup")
async def startup_event():
    """
    アプリケーション起動時に実行される処理
    初期化ログを出力する
    """
    logger.info(f"{settings.PROJECT_NAME} アプリケーションを起動しました")


# アプリケーション終了時のロギング
@app.on_event("shutdown")
async def shutdown_event():
    """
    アプリケーション終了時に実行される処理
    終了ログを出力する
    """
    logger.info(f"{settings.PROJECT_NAME} アプリケーションを終了しました")
