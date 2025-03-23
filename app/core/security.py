from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union

from jose import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.config import settings
from app.core.logging import logger

# パスワードハッシュコンテキスト
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2認証スキーム
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    平文パスワードとハッシュパスワードを比較検証する
    
    Args:
        plain_password (str): 平文パスワード
        hashed_password (str): ハッシュ化されたパスワード
        
    Returns:
        bool: パスワードが一致する場合はTrue
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    パスワードをハッシュ化する
    
    Args:
        password (str): 平文パスワード
        
    Returns:
        str: ハッシュ化されたパスワード
    """
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    アクセストークンを作成する
    
    Args:
        data (Dict[str, Any]): トークンに埋め込むデータ
        expires_delta (Optional[timedelta], optional): トークンの有効期間. Defaults to None.
        
    Returns:
        str: JWTトークン
    """
    to_encode = data.copy()
    
    # 有効期限の設定
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # クレームの設定
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    
    # トークンの生成
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    現在のユーザーを取得する依存性関数
    
    Args:
        token (str, optional): JWTトークン. Defaults to Depends(oauth2_scheme).
        
    Returns:
        Dict[str, Any]: ユーザー情報
        
    Raises:
        HTTPException: トークンが無効または期限切れの場合
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証情報が無効です",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # トークンのデコード
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: Optional[int] = payload.get("sub")
        
        if user_id is None:
            logger.warning("トークンにユーザーIDが含まれていません")
            raise credentials_exception
            
        # ユーザー情報をデータベースから取得する処理をここに追加
        # 現在はモックデータを返す
        user_data = {
            "id": user_id,
            "username": payload.get("username", "unknown"),
            "email": payload.get("email", "unknown@example.com"),
            "is_active": True,
            "is_admin": payload.get("is_admin", False)
        }
        
        return user_data
        
    except jwt.JWTError as e:
        logger.error(f"JWTトークンのデコードに失敗: {str(e)}")
        raise credentials_exception


async def get_current_active_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    現在のアクティブユーザーを取得する依存性関数
    
    Args:
        current_user (Dict[str, Any], optional): 現在のユーザー情報. Defaults to Depends(get_current_user).
        
    Returns:
        Dict[str, Any]: アクティブなユーザー情報
        
    Raises:
        HTTPException: ユーザーが非アクティブの場合
    """
    if not current_user.get("is_active", False):
        logger.warning(f"非アクティブユーザーがアクセスを試みました: {current_user.get('id')}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ユーザーは非アクティブです")
    return current_user


async def get_current_admin_user(current_user: Dict[str, Any] = Depends(get_current_active_user)) -> Dict[str, Any]:
    """
    現在の管理者ユーザーを取得する依存性関数
    
    Args:
        current_user (Dict[str, Any], optional): 現在のアクティブユーザー情報. Defaults to Depends(get_current_active_user).
        
    Returns:
        Dict[str, Any]: 管理者ユーザー情報
        
    Raises:
        HTTPException: ユーザーが管理者でない場合
    """
    if not current_user.get("is_admin", False):
        logger.warning(f"非管理者ユーザーが管理者機能へのアクセスを試みました: {current_user.get('id')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この操作には管理者権限が必要です"
        )
    return current_user
