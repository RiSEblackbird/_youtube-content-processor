from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Video, VideoSegment
from app.schemas.video import (
    VideoCreate, 
    VideoResponse, 
    VideoDetail, 
    VideoSegmentResponse,
    ProcessVideoRequest,
    ProcessVideoResponse
)
from app.services.langgraph.video_processor import VideoProcessorGraph
from app.core.logging import logger
from app.core.exceptions import YouTubeExtractError, ClaudeAPIError, DatabaseError


router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("/", response_model=ProcessVideoResponse)
async def process_video(
    request: ProcessVideoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    YouTubeの動画URLを処理し、文字起こしと分析を行うエンドポイント
    
    Args:
        request (ProcessVideoRequest): 処理リクエスト（YouTubeのURL）
        background_tasks (BackgroundTasks): バックグラウンドタスク
        db (Session, optional): データベースセッション. Defaults to Depends(get_db).
        
    Returns:
        ProcessVideoResponse: 処理結果レスポンス
    """
    try:
        # 動画処理グラフの初期化
        processor = VideoProcessorGraph(db)
        
        # 処理を実行
        result = processor.process_video(request.youtube_url)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "処理に失敗しました"))
        
        # レスポンスを構築
        return ProcessVideoResponse(
            success=True,
            message="動画処理が完了しました",
            video_id=result.get("video_id"),
            title=result.get("title"),
            segments_count=result.get("segments_count", 0)
        )
        
    except (YouTubeExtractError, ClaudeAPIError) as e:
        logger.error(f"動画処理中にエラーが発生: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(f"予期しないエラーが発生: {str(e)}")
        raise HTTPException(status_code=500, detail=f"サーバーエラー: {str(e)}")


@router.get("/", response_model=List[VideoResponse])
async def list_videos(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    処理済みの動画リストを取得するエンドポイント
    
    Args:
        skip (int, optional): スキップする件数. Defaults to 0.
        limit (int, optional): 取得する最大件数. Defaults to 100.
        db (Session, optional): データベースセッション. Defaults to Depends(get_db).
        
    Returns:
        List[VideoResponse]: 動画リスト
    """
    try:
        videos = db.query(Video).order_by(Video.created_at.desc()).offset(skip).limit(limit).all()
        return videos
        
    except Exception as e:
        logger.error(f"動画リスト取得中にエラーが発生: {str(e)}")
        raise HTTPException(status_code=500, detail=f"サーバーエラー: {str(e)}")


@router.get("/{video_id}", response_model=VideoDetail)
async def get_video(
    video_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """
    指定されたIDの動画詳細を取得するエンドポイント
    
    Args:
        video_id (int): 動画ID
        db (Session, optional): データベースセッション. Defaults to Depends(get_db).
        
    Returns:
        VideoDetail: 動画詳細情報
    """
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        
        if not video:
            raise HTTPException(status_code=404, detail=f"ID {video_id} の動画は見つかりません")
        
        segments = db.query(VideoSegment).filter(VideoSegment.video_id == video_id).all()
        
        return VideoDetail(
            id=video.id,
            youtube_id=video.youtube_id,
            title=video.title,
            url=video.url,
            channel_name=video.channel_name,
            published_at=video.published_at,
            duration_seconds=video.duration_seconds,
            summary=video.summary,
            category=video.category,
            topics=video.topics,
            created_at=video.created_at,
            updated_at=video.updated_at,
            processed=video.processed,
            segments=[
                VideoSegmentResponse(
                    id=segment.id,
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    transcript=segment.transcript,
                    subcategory=segment.subcategory,
                    content_summary=segment.content_summary,
                    keywords=segment.keywords
                )
                for segment in segments
            ]
        )
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"動画詳細取得中にエラーが発生: {str(e)}")
        raise HTTPException(status_code=500, detail=f"サーバーエラー: {str(e)}")


@router.delete("/{video_id}", response_model=Dict[str, Any])
async def delete_video(
    video_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """
    指定されたIDの動画を削除するエンドポイント
    
    Args:
        video_id (int): 動画ID
        db (Session, optional): データベースセッション. Defaults to Depends(get_db).
        
    Returns:
        Dict[str, Any]: 削除結果
    """
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        
        if not video:
            raise HTTPException(status_code=404, detail=f"ID {video_id} の動画は見つかりません")
        
        db.delete(video)
        db.commit()
        
        return {"success": True, "message": f"ID {video_id} の動画を削除しました"}
        
    except HTTPException:
        raise
        
    except Exception as e:
        db.rollback()
        logger.error(f"動画削除中にエラーが発生: {str(e)}")
        raise HTTPException(status_code=500, detail=f"サーバーエラー: {str(e)}")
