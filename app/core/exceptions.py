from typing import Any, Dict, Optional


class BaseAPIException(Exception):
    """
    APIエラーの基底クラス
    すべてのカスタム例外の基底となり、共通の機能を提供する
    """
    
    def __init__(self, message: str, status_code: int = 400):
        """
        BaseAPIExceptionの初期化メソッド
        
        Args:
            message (str): エラーメッセージ
            status_code (int, optional): HTTPステータスコード. Defaults to 400.
        """
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """
        例外情報を辞書形式に変換する
        
        Returns:
            Dict[str, Any]: 例外情報の辞書
        """
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "status_code": self.status_code
        }


class YouTubeExtractError(BaseAPIException):
    """
    YouTube動画情報の抽出に関するエラー
    YouTube APIや文字起こし取得に失敗した場合に使用
    """
    
    def __init__(self, message: str, status_code: int = 400):
        """
        YouTubeExtractErrorの初期化メソッド
        
        Args:
            message (str): エラーメッセージ
            status_code (int, optional): HTTPステータスコード. Defaults to 400.
        """
        super().__init__(message, status_code)


class ClaudeAPIError(BaseAPIException):
    """
    Claude APIに関するエラー
    Claude APIの呼び出しに失敗した場合に使用
    """
    
    def __init__(self, message: str, status_code: int = 400):
        """
        ClaudeAPIErrorの初期化メソッド
        
        Args:
            message (str): エラーメッセージ
            status_code (int, optional): HTTPステータスコード. Defaults to 400.
        """
        super().__init__(message, status_code)


class OpenAIAPIError(BaseAPIException):
    """
    OpenAI APIに関するエラー
    OpenAI APIの呼び出しに失敗した場合に使用
    """
    
    def __init__(self, message: str, status_code: int = 400):
        """
        OpenAIAPIErrorの初期化メソッド
        
        Args:
            message (str): エラーメッセージ
            status_code (int, optional): HTTPステータスコード. Defaults to 400.
        """
        super().__init__(message, status_code)


class DatabaseError(BaseAPIException):
    """
    データベース操作に関するエラー
    SQLAlchemyの操作に失敗した場合に使用
    """
    
    def __init__(self, message: str, status_code: int = 500):
        """
        DatabaseErrorの初期化メソッド
        
        Args:
            message (str): エラーメッセージ
            status_code (int, optional): HTTPステータスコード. Defaults to 500.
        """
        super().__init__(message, status_code)


class ValidationError(BaseAPIException):
    """
    入力バリデーションに関するエラー
    Pydanticのバリデーションに失敗した場合に使用
    """
    
    def __init__(self, message: str, status_code: int = 422):
        """
        ValidationErrorの初期化メソッド
        
        Args:
            message (str): エラーメッセージ
            status_code (int, optional): HTTPステータスコード. Defaults to 422.
        """
        super().__init__(message, status_code)


class AuthenticationError(BaseAPIException):
    """
    認証に関するエラー
    ユーザー認証に失敗した場合に使用
    """
    
    def __init__(self, message: str = "認証に失敗しました", status_code: int = 401):
        """
        AuthenticationErrorの初期化メソッド
        
        Args:
            message (str, optional): エラーメッセージ. Defaults to "認証に失敗しました".
            status_code (int, optional): HTTPステータスコード. Defaults to 401.
        """
        super().__init__(message, status_code)


class AuthorizationError(BaseAPIException):
    """
    認可に関するエラー
    アクセス権限がない場合に使用
    """
    
    def __init__(self, message: str = "この操作を実行する権限がありません", status_code: int = 403):
        """
        AuthorizationErrorの初期化メソッド
        
        Args:
            message (str, optional): エラーメッセージ. Defaults to "この操作を実行する権限がありません".
            status_code (int, optional): HTTPステータスコード. Defaults to 403.
        """
        super().__init__(message, status_code)


class ResourceNotFoundError(BaseAPIException):
    """
    リソースが見つからないエラー
    要求されたリソースが存在しない場合に使用
    """
    
    def __init__(self, resource_type: str, resource_id: Any, status_code: int = 404):
        """
        ResourceNotFoundErrorの初期化メソッド
        
        Args:
            resource_type (str): リソースタイプ
            resource_id (Any): リソースID
            status_code (int, optional): HTTPステータスコード. Defaults to 404.
        """
        message = f"{resource_type} ID:{resource_id} は見つかりません"
        super().__init__(message, status_code)


class RateLimitError(BaseAPIException):
    """
    レート制限に関するエラー
    API呼び出しの制限に達した場合に使用
    """
    
    def __init__(self, message: str = "リクエスト制限に達しました。しばらく待ってから再試行してください", status_code: int = 429):
        """
        RateLimitErrorの初期化メソッド
        
        Args:
            message (str, optional): エラーメッセージ. Defaults to "リクエスト制限に達しました。しばらく待ってから再試行してください".
            status_code (int, optional): HTTPステータスコード. Defaults to 429.
        """
        super().__init__(message, status_code)
