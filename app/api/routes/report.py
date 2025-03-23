from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Report, Video
from app.schemas.report import (
    ReportCreate,
    ReportResponse,
    ReportDetail,
    GenerateReportRequest,
    GenerateReportResponse
)
from app.services.langgraph.report_generator import ReportGeneratorGraph
from app.core.logging import logger
from app.core.exceptions import OpenAIAPIError, DatabaseError


router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate", response_model=GenerateReportResponse)
async def generate_report(
    request: GenerateReportRequest,
    db: Session = Depends(get_db)
):
    """
    指定された動画IDとフォーマットタイプでレポートを生成するエンドポイント
    
    Args:
        request (GenerateReportRequest): 生成リクエスト（動画ID、フォーマットタイプ、カスタム指示）
        db (Session, optional): データベースセッション. Defaults to Depends(get_db).
        
    Returns:
        GenerateReportResponse: 生成結果レスポンス
    """
    try:
        # 動画の存在確認
        video = db.query(Video).filter(Video.id == request.video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail=f"ID {request.video_id} の動画は見つかりません")
        
        # レポート生成グラフの初期化
        generator = ReportGeneratorGraph(db)
        
        # レポート生成を実行
        result = generator.generate_report(
            request.video_id, 
            request.format_type, 
            request.custom_instructions
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "レポート生成に失敗しました"))
        
        # レスポンスを構築
        return GenerateReportResponse(
            success=True,
            message="レポート生成が完了しました",
            video_id=result.get("video_id"),
            report_id=result.get("report_id"),
            title=result.get("title"),
            format_type=result.get("format_type")
        )
        
    except HTTPException:
        raise
        
    except (OpenAIAPIError, DatabaseError) as e:
        logger.error(f"レポート生成中にエラーが発生: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(f"予期しないエラーが発生: {str(e)}")
        raise HTTPException(status_code=500, detail=f"サーバーエラー: {str(e)}")


@router.get("/", response_model=List[ReportResponse])
async def list_reports(
    video_id: Optional[int] = Query(None, ge=1),
    format_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    レポートリストを取得するエンドポイント
    
    Args:
        video_id (Optional[int], optional): フィルタリングする動画ID. Defaults to None.
        format_type (Optional[str], optional): フィルタリングするフォーマットタイプ. Defaults to None.
        skip (int, optional): スキップする件数. Defaults to 0.
        limit (int, optional): 取得する最大件数. Defaults to 100.
        db (Session, optional): データベースセッション. Defaults to Depends(get_db).
        
    Returns:
        List[ReportResponse]: レポートリスト
    """
    try:
        query = db.query(Report)
        
        if video_id:
            query = query.filter(Report.video_id == video_id)
        
        if format_type:
            query = query.filter(Report.format_type == format_type)
        
        reports = query.order_by(Report.created_at.desc()).offset(skip).limit(limit).all()
        return reports
        
    except Exception as e:
        logger.error(f"レポートリスト取得中にエラーが発生: {str(e)}")
        raise HTTPException(status_code=500, detail=f"サーバーエラー: {str(e)}")


@router.get("/{report_id}", response_model=ReportDetail)
async def get_report(
    report_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """
    指定されたIDのレポート詳細を取得するエンドポイント
    
    Args:
        report_id (int): レポートID
        db (Session, optional): データベースセッション. Defaults to Depends(get_db).
        
    Returns:
        ReportDetail: レポート詳細情報
    """
    try:
        report = db.query(Report).filter(Report.id == report_id).first()
        
        if not report:
            raise HTTPException(status_code=404, detail=f"ID {report_id} のレポートは見つかりません")
        
        # 関連する動画情報を取得
        video = db.query(Video).filter(Video.id == report.video_id).first()
        
        if not video:
            video_title = "不明"
        else:
            video_title = video.title
        
        return ReportDetail(
            id=report.id,
            video_id=report.video_id,
            video_title=video_title,
            title=report.title,
            format_type=report.format_type,
            content=report.content,
            created_at=report.created_at,
            updated_at=report.updated_at
        )
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"レポート詳細取得中にエラーが発生: {str(e)}")
        raise HTTPException(status_code=500, detail=f"サーバーエラー: {str(e)}")


@router.delete("/{report_id}", response_model=Dict[str, Any])
async def delete_report(
    report_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """
    指定されたIDのレポートを削除するエンドポイント
    
    Args:
        report_id (int): レポートID
        db (Session, optional): データベースセッション. Defaults to Depends(get_db).
        
    Returns:
        Dict[str, Any]: 削除結果
    """
    try:
        report = db.query(Report).filter(Report.id == report_id).first()
        
        if not report:
            raise HTTPException(status_code=404, detail=f"ID {report_id} のレポートは見つかりません")
        
        db.delete(report)
        db.commit()
        
        return {"success": True, "message": f"ID {report_id} のレポートを削除しました"}
        
    except HTTPException:
        raise
        
    except Exception as e:
        db.rollback()
        logger.error(f"レポート削除中にエラーが発生: {str(e)}")
        raise HTTPException(status_code=500, detail=f"サーバーエラー: {str(e)}")
