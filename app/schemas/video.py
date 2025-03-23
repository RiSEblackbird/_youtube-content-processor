from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class VideoBase(BaseModel):
    """
    動画の基本情報を定義するスキーマ
    APIリクエスト/レスポンスの基本構造を提供する
    """
    title: str
    url: str
    channel_name: Optional[str] = None


class VideoCreate(VideoBase):
    """
    動画作成リクエスト用のスキーマ
    新規動画の追加に必要な情報を定義する
    """
    youtube_id: str
    published_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None


class VideoResponse(VideoBase):
    """
    動画一覧取得レスポンス用のスキーマ
    一覧表示に必要な最小限の情報を含む
    """
    id: int
    youtube_id: str
    summary: Optional[str] = None
    category: Optional[str] = None
    created_at: datetime
    processed: bool

    class Config:
        """
        Pydanticのモデル設定
        ORMモードを有効にしてSQLAlchemyモデルからの変換を可能にする
        """
        from_attributes = True


class VideoSegmentBase(BaseModel):
    """
    動画セグメントの基本情報を定義するスキーマ
    セグメントのタイムスタンプと内容を管理する
    """
    start_time: float
    end_time: float
    transcript: str
    subcategory: Optional[str] = None
    content_summary: Optional[str] = None
    keywords: Optional[List[str]] = None


class VideoSegmentCreate(VideoSegmentBase):
    """
    動画セグメント作成リクエスト用のスキーマ
    新規セグメントの追加に必要な情報を定義する
    """
    video_id: int


class VideoSegmentResponse(VideoSegmentBase):
    """
    動画セグメント取得レスポンス用のスキーマ
    セグメント情報の参照に必要な情報を含む
    """
    id: int

    class Config:
        from_attributes = True


class VideoDetail(VideoResponse):
    """
    動画詳細取得レスポンス用のスキーマ
    動画の全ての情報とセグメント一覧を含む
    """
    published_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    topics: Optional[List[str]] = None
    updated_at: datetime
    segments: List[VideoSegmentResponse]


class ProcessVideoRequest(BaseModel):
    """
    動画処理リクエスト用のスキーマ
    処理対象のYouTube URLを指定する
    """
    youtube_url: str = Field(..., description="処理するYouTubeのURL")


class ProcessVideoResponse(BaseModel):
    """
    動画処理レスポンス用のスキーマ
    処理結果のステータスと概要情報を含む
    """
    success: bool = Field(..., description="処理が成功したかどうか")
    message: str = Field(..., description="処理結果のメッセージ")
    video_id: Optional[str] = Field(None, description="処理された動画のID")
    title: Optional[str] = Field(None, description="処理された動画のタイトル")
    segments_count: Optional[int] = Field(None, description="抽出されたセグメント数")
