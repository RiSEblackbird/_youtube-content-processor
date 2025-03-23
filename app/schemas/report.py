from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ReportBase(BaseModel):
    """
    レポートの基本情報を定義するスキーマ
    APIリクエスト/レスポンスの基本構造を提供する
    """
    title: str
    format_type: str
    video_id: int


class ReportCreate(ReportBase):
    """
    レポート作成リクエスト用のスキーマ
    新規レポートの追加に必要な情報を定義する
    """
    content: str


class ReportResponse(ReportBase):
    """
    レポート一覧取得レスポンス用のスキーマ
    一覧表示に必要な最小限の情報を含む
    """
    id: int
    created_at: datetime

    class Config:
        """
        Pydanticのモデル設定
        ORMモードを有効にしてSQLAlchemyモデルからの変換を可能にする
        """
        from_attributes = True


class ReportDetail(ReportResponse):
    """
    レポート詳細取得レスポンス用のスキーマ
    レポートの全ての情報を含む
    """
    content: str
    video_title: Optional[str] = None
    updated_at: datetime


class GenerateReportRequest(BaseModel):
    """
    レポート生成リクエスト用のスキーマ
    レポート生成に必要なパラメータを定義する
    """
    video_id: int = Field(..., description="レポートを生成する動画のID")
    format_type: str = Field(..., description="生成するレポートの形式タイプ")
    custom_instructions: Optional[str] = Field(None, description="レポート生成のためのカスタム指示")


class GenerateReportResponse(BaseModel):
    """
    レポート生成レスポンス用のスキーマ
    生成結果のステータスと概要情報を含む
    """
    success: bool = Field(..., description="生成が成功したかどうか")
    message: str = Field(..., description="生成結果のメッセージ")
    video_id: int = Field(..., description="関連する動画のID")
    report_id: Optional[int] = Field(None, description="生成されたレポートのID")
    title: Optional[str] = Field(None, description="生成されたレポートのタイトル")
    format_type: str = Field(..., description="生成されたレポートの形式タイプ")
