import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Union

from loguru import logger as loguru_logger

from app.config import settings


class InterceptHandler(logging.Handler):
    """
    標準のloggingモジュールからloguruへリダイレクトするハンドラ
    FastAPIなどの標準ロギングをloguruで一元管理するために使用する
    """

    def emit(self, record: logging.LogRecord) -> None:
        """
        ログレコードをloguruに送信する
        
        Args:
            record (logging.LogRecord): ログレコード
        """
        # loguruへ転送する適切なログレベルを取得
        try:
            level = loguru_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 発信元の名前を取得
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        # loguruでログを出力
        loguru_logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


class JsonSink:
    """
    JSON形式でログを出力するためのカスタムシンク
    構造化ロギングを実現し、ログ分析ツールでの処理を容易にする
    """
    
    def __init__(self, sink: Union[str, Path], level: str = "INFO"):
        """
        JsonSinkの初期化メソッド
        
        Args:
            sink (Union[str, Path]): ログの出力先（ファイルパスまたはストリーム）
            level (str, optional): 最小ログレベル. Defaults to "INFO".
        """
        self.sink = sink
        self.level = level
    
    def __call__(self, message: Dict[str, Any]) -> None:
        """
        ログメッセージをJSON形式で出力する
        
        Args:
            message (Dict[str, Any]): ログメッセージ
        """
        record = message.record
        
        # JSON形式に変換するための辞書を作成
        log_entry = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "message": record["message"],
            "module": record["name"],
            "function": record["function"],
            "line": record["line"],
        }
        
        # 例外情報があれば追加
        if record["exception"]:
            log_entry["exception"] = str(record["exception"])
        
        # 追加のコンテキスト情報があれば追加
        if record["extra"]:
            log_entry["extra"] = record["extra"]
        
        # JSONをシンクに書き込み
        if isinstance(self.sink, (str, Path)):
            with open(self.sink, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        else:
            # ストリームの場合（sys.stdout, sys.stderrなど）
            print(json.dumps(log_entry), file=self.sink)


def setup_logging() -> None:
    """
    アプリケーション全体のロギング設定を構成する
    標準ロギングとloguruを統合し、複数の出力先を構成する
    """
    # loguruのデフォルト設定を削除
    loguru_logger.remove()
    
    # ログレベルを取得
    log_level = settings.LOG_LEVEL
    
    # コンソール出力の設定
    loguru_logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
    )
    
    # ログディレクトリがなければ作成
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    
    # ファイル出力の設定（ローテーション付き）
    loguru_logger.add(
        str(log_dir / "app_{time}.log"),
        rotation="10 MB",
        retention="1 week",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level=log_level,
    )
    
    # JSON形式の出力設定
    loguru_logger.add(
        JsonSink(str(log_dir / "app_json_{time}.log")),
        level=log_level,
    )
    
    # 標準のloggingモジュールをloguruにリダイレクト
    logging.basicConfig(handlers=[InterceptHandler()], level=0)
    
    # 重要なライブラリのロガーを明示的に設定
    for logger_name in ("uvicorn", "uvicorn.access", "fastapi", "sqlalchemy"):
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
    
    loguru_logger.info("ロギングシステムが初期化されました")


# ロギングの初期化
setup_logging()

# エクスポート用のロガーインスタンス
logger = loguru_logger
