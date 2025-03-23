from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import Video, VideoSegment
from app.schemas.video import VideoCreate, VideoSegmentCreate
from app.core.logging import logger
from app.core.exceptions import DatabaseError, ResourceNotFoundError


def create_video(db: Session, video: VideoCreate) -> Video:
    """
    新しい動画エントリを作成する
    
    Args:
        db (Session): データベースセッション
        video (VideoCreate): 作成する動画データ
        
    Returns:
        Video: 作成された動画モデル
        
    Raises:
        DatabaseError: データベース操作に失敗した場合
    """
    try:
        # 同じYouTube IDのビデオが既に存在するか確認
        existing = db.query(Video).filter(Video.youtube_id == video.youtube_id).first()
        if existing:
            logger.info(f"YouTube ID {video.youtube_id} の動画は既に存在します: ID {existing.id}")
            return existing
        
        # 新しい動画モデルを作成
        db_video = Video(
            youtube_id=video.youtube_id,
            title=video.title,
            url=video.url,
            channel_name=video.channel_name,
            published_at=video.published_at,
            duration_seconds=video.duration_seconds,
            processed=False
        )
        
        # データベースに追加してコミット
        db.add(db_video)
        db.commit()
        db.refresh(db_video)
        
        logger.info(f"新しい動画を作成しました: ID {db_video.id}, YouTube ID {db_video.youtube_id}")
        return db_video
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"動画作成中にデータベースエラーが発生: {str(e)}")
        raise DatabaseError(f"動画の作成に失敗しました: {str(e)}")


def get_video(db: Session, video_id: int) -> Video:
    """
    指定されたIDの動画を取得する
    
    Args:
        db (Session): データベースセッション
        video_id (int): 動画ID
        
    Returns:
        Video: 取得された動画モデル
        
    Raises:
        ResourceNotFoundError: 指定されたIDの動画が見つからない場合
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        logger.warning(f"ID {video_id} の動画は見つかりません")
        raise ResourceNotFoundError("動画", video_id)
    
    return video


def get_video_by_youtube_id(db: Session, youtube_id: str) -> Optional[Video]:
    """
    指定されたYouTube IDの動画を取得する
    
    Args:
        db (Session): データベースセッション
        youtube_id (str): YouTube ID
        
    Returns:
        Optional[Video]: 取得された動画モデル、見つからない場合はNone
    """
    return db.query(Video).filter(Video.youtube_id == youtube_id).first()


def get_videos(db: Session, skip: int = 0, limit: int = 100) -> List[Video]:
    """
    動画リストを取得する
    
    Args:
        db (Session): データベースセッション
        skip (int, optional): スキップする件数. Defaults to 0.
        limit (int, optional): 取得する最大件数. Defaults to 100.
        
    Returns:
        List[Video]: 動画モデルのリスト
    """
    return db.query(Video).order_by(Video.created_at.desc()).offset(skip).limit(limit).all()


def update_video(db: Session, video_id: int, video_data: Dict[str, Any]) -> Video:
    """
    指定されたIDの動画を更新する
    
    Args:
        db (Session): データベースセッション
        video_id (int): 動画ID
        video_data (Dict[str, Any]): 更新するデータ
        
    Returns:
        Video: 更新された動画モデル
        
    Raises:
        ResourceNotFoundError: 指定されたIDの動画が見つからない場合
        DatabaseError: データベース操作に失敗した場合
    """
    try:
        # 動画の存在確認
        db_video = get_video(db, video_id)
        
        # 更新するフィールドを設定
        for key, value in video_data.items():
            if hasattr(db_video, key):
                setattr(db_video, key, value)
        
        # 更新日時を現在時刻に設定
        db_video.updated_at = datetime.utcnow()
        
        # データベースを更新
        db.commit()
        db.refresh(db_video)
        
        logger.info(f"ID {video_id} の動画を更新しました")
        return db_video
        
    except ResourceNotFoundError:
        raise
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"動画更新中にデータベースエラーが発生: {str(e)}")
        raise DatabaseError(f"動画の更新に失敗しました: {str(e)}")


def delete_video(db: Session, video_id: int) -> bool:
    """
    指定されたIDの動画を削除する
    
    Args:
        db (Session): データベースセッション
        video_id (int): 動画ID
        
    Returns:
        bool: 削除に成功した場合はTrue
        
    Raises:
        ResourceNotFoundError: 指定されたIDの動画が見つからない場合
        DatabaseError: データベース操作に失敗した場合
    """
    try:
        # 動画の存在確認
        db_video = get_video(db, video_id)
        
        # 動画を削除
        db.delete(db_video)
        db.commit()
        
        logger.info(f"ID {video_id} の動画を削除しました")
        return True
        
    except ResourceNotFoundError:
        raise
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"動画削除中にデータベースエラーが発生: {str(e)}")
        raise DatabaseError(f"動画の削除に失敗しました: {str(e)}")


def create_video_segment(db: Session, segment: VideoSegmentCreate) -> VideoSegment:
    """
    新しい動画セグメントを作成する
    
    Args:
        db (Session): データベースセッション
        segment (VideoSegmentCreate): 作成するセグメントデータ
        
    Returns:
        VideoSegment: 作成されたセグメントモデル
        
    Raises:
        ResourceNotFoundError: 関連する動画が見つからない場合
        DatabaseError: データベース操作に失敗した場合
    """
    try:
        # 関連する動画の存在確認
        _ = get_video(db, segment.video_id)
        
        # 新しいセグメントモデルを作成
        db_segment = VideoSegment(
            video_id=segment.video_id,
            start_time=segment.start_time,
            end_time=segment.end_time,
            transcript=segment.transcript,
            subcategory=segment.subcategory,
            content_summary=segment.content_summary,
            keywords=segment.keywords
        )
        
        # データベースに追加してコミット
        db.add(db_segment)
        db.commit()
        db.refresh(db_segment)
        
        logger.info(f"新しい動画セグメントを作成しました: ID {db_segment.id}, 動画ID {db_segment.video_id}")
        return db_segment
        
    except ResourceNotFoundError:
        raise
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"セグメント作成中にデータベースエラーが発生: {str(e)}")
        raise DatabaseError(f"セグメントの作成に失敗しました: {str(e)}")


def get_video_segments(db: Session, video_id: int) -> List[VideoSegment]:
    """
    指定された動画のセグメントを取得する
    
    Args:
        db (Session): データベースセッション
        video_id (int): 動画ID
        
    Returns:
        List[VideoSegment]: セグメントモデルのリスト
        
    Raises:
        ResourceNotFoundError: 指定されたIDの動画が見つからない場合
    """
    # 動画の存在確認
    _ = get_video(db, video_id)
    
    # セグメントを取得
    segments = db.query(VideoSegment).filter(VideoSegment.video_id == video_id).order_by(VideoSegment.start_time).all()
    
    return segments


def get_segment(db: Session, segment_id: int) -> VideoSegment:
    """
    指定されたIDのセグメントを取得する
    
    Args:
        db (Session): データベースセッション
        segment_id (int): セグメントID
        
    Returns:
        VideoSegment: 取得されたセグメントモデル
        
    Raises:
        ResourceNotFoundError: 指定されたIDのセグメントが見つからない場合
    """
    segment = db.query(VideoSegment).filter(VideoSegment.id == segment_id).first()
    
    if not segment:
        logger.warning(f"ID {segment_id} のセグメントは見つかりません")
        raise ResourceNotFoundError("動画セグメント", segment_id)
    
    return segment


def update_segment(db: Session, segment_id: int, segment_data: Dict[str, Any]) -> VideoSegment:
    """
    指定されたIDのセグメントを更新する
    
    Args:
        db (Session): データベースセッション
        segment_id (int): セグメントID
        segment_data (Dict[str, Any]): 更新するデータ
        
    Returns:
        VideoSegment: 更新されたセグメントモデル
        
    Raises:
        ResourceNotFoundError: 指定されたIDのセグメントが見つからない場合
        DatabaseError: データベース操作に失敗した場合
    """
    try:
        # セグメントの存在確認
        db_segment = get_segment(db, segment_id)
        
        # 更新するフィールドを設定
        for key, value in segment_data.items():
            if hasattr(db_segment, key):
                setattr(db_segment, key, value)
        
        # 更新日時を現在時刻に設定
        db_segment.updated_at = datetime.utcnow()
        
        # データベースを更新
        db.commit()
        db.refresh(db_segment)
        
        logger.info(f"ID {segment_id} のセグメントを更新しました")
        return db_segment
        
    except ResourceNotFoundError:
        raise
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"セグメント更新中にデータベースエラーが発生: {str(e)}")
        raise DatabaseError(f"セグメントの更新に失敗しました: {str(e)}")


def delete_segment(db: Session, segment_id: int) -> bool:
    """
    指定されたIDのセグメントを削除する
    
    Args:
        db (Session): データベースセッション
        segment_id (int): セグメントID
        
    Returns:
        bool: 削除に成功した場合はTrue
        
    Raises:
        ResourceNotFoundError: 指定されたIDのセグメントが見つからない場合
        DatabaseError: データベース操作に失敗した場合
    """
    try:
        # セグメントの存在確認
        db_segment = get_segment(db, segment_id)
        
        # セグメントを削除
        db.delete(db_segment)
        db.commit()
        
        logger.info(f"ID {segment_id} のセグメントを削除しました")
        return True
        
    except ResourceNotFoundError:
        raise
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"セグメント削除中にデータベースエラーが発生: {str(e)}")
        raise DatabaseError(f"セグメントの削除に失敗しました: {str(e)}")
