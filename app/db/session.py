from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings
from app.core.logging import logger

# SQLAlchemyエンジンの設定
engine = create_engine(str(settings.DATABASE_URI))

# セッションファクトリー
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    データベースセッションを取得するための依存性関数
    FastAPIエンドポイントから使用され、トランザクション管理を自動で行う
    
    Yields:
        Generator[Session, None, None]: データベースセッション
    """
    db = SessionLocal()
    try:
        logger.debug("データベースセッションを開始")
        yield db
    except Exception as e:
        logger.error(f"データベース操作中にエラーが発生: {str(e)}")
        db.rollback()
        raise
    finally:
        logger.debug("データベースセッションを終了")
        db.close()
