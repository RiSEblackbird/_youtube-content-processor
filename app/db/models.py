from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# SQLAlchemyのベースクラス
Base = declarative_base()


class Video(Base):
    """
    YouTube動画のメタデータと文字起こしデータを格納するモデル
    動画情報とクロード処理後のメタデータを一元管理するために使用
    """
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    youtube_id = Column(String(20), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    url = Column(String(255), nullable=False)
    channel_name = Column(String(255))
    published_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # クロードによる処理結果
    summary = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    topics = Column(JSON, nullable=True)  # トピックリストをJSON形式で保存
    
    # システムメタデータ
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    processed = Column(Boolean, default=False)
    
    # リレーションシップ
    segments = relationship("VideoSegment", back_populates="video", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="video", cascade="all, delete-orphan")


class VideoSegment(Base):
    """
    動画の特定セグメント（部分）に関する情報を格納するモデル
    時間的に区切られた動画の部分ごとに詳細情報を管理するために使用
    """
    __tablename__ = "video_segments"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    
    # セグメント時間情報
    start_time = Column(Float, nullable=False)  # 秒単位
    end_time = Column(Float, nullable=False)  # 秒単位
    
    # セグメント内容
    transcript = Column(Text, nullable=False)  # 元の文字起こし
    subcategory = Column(String(100), nullable=True)  # このセグメントのサブカテゴリ
    content_summary = Column(Text, nullable=True)  # セグメント要約
    keywords = Column(JSON, nullable=True)  # キーワードリスト
    
    # システムメタデータ
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # リレーションシップ
    video = relationship("Video", back_populates="segments")


class Report(Base):
    """
    OpenAIのo1-miniによって生成されたレポートを格納するモデル
    動画に基づいた様々な形式のレポートを管理するために使用
    """
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    
    # レポート情報
    title = Column(String(255), nullable=False)
    format_type = Column(String(50), nullable=False)  # 'summary', 'detailed', 'presentation', etc.
    content = Column(Text, nullable=False)
    
    # システムメタデータ
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # リレーションシップ
    video = relationship("Video", back_populates="reports")
