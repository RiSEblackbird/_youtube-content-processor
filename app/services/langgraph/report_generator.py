from typing import Dict, List, Any, TypedDict, Annotated, Optional, Literal
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from langgraph.graph import StateGraph, END

from app.services.openai import OpenAIService
from app.db.models import Video, VideoSegment, Report
from app.core.logging import logger
from app.core.exceptions import OpenAIAPIError, DatabaseError


class ReportState(TypedDict):
    """
    レポート生成グラフの状態を表す型定義
    LangGraphの状態管理に使用する
    """
    video_id: int
    format_type: str
    custom_instructions: Optional[str]
    video_data: Optional[Dict[str, Any]]
    report_content: Optional[Dict[str, Any]]
    saved_report_id: Optional[int]
    error: Optional[str]
    status: str


class ReportStatus(str, Enum):
    """
    レポート生成状態を表す列挙型
    グラフの流れ制御に使用する
    """
    INIT = "initialized"
    VIDEO_LOADED = "video_loaded"
    REPORT_GENERATED = "report_generated"
    REPORT_SAVED = "report_saved"
    ERROR = "error"
    COMPLETE = "complete"


class ReportGeneratorGraph:
    """
    指定された動画IDとフォーマットタイプからレポートを生成するLangGraphプロセス
    レポート生成フローを効率的に管理するために使用
    """
    
    def __init__(self, db: Session):
        """
        ReportGeneratorGraphの初期化メソッド
        
        Args:
            db (Session): データベースセッション
        """
        self.db = db
        self.openai_service = OpenAIService()
        self.graph = self._build_graph()
        logger.info("ReportGeneratorGraphを初期化しました")
    
    def _load_video_data(self, state: ReportState) -> ReportState:
        """
        指定された動画IDからデータを読み込むノード
        
        Args:
            state (ReportState): 現在の処理状態
            
        Returns:
            ReportState: 更新された処理状態
        """
        try:
            video_id = state["video_id"]
            logger.info(f"動画データ読み込みを開始: ID {video_id}")
            
            # データベースから動画情報を取得
            video = self.db.query(Video).filter(Video.id == video_id).first()
            
            if not video:
                raise DatabaseError(f"指定されたID {video_id} の動画が見つかりません")
            
            # セグメント情報を取得
            segments = self.db.query(VideoSegment).filter(VideoSegment.video_id == video_id).all()
            
            # 結果を構築
            video_data = {
                "id": video.id,
                "title": video.title,
                "url": video.url,
                "channel_name": video.channel_name,
                "summary": video.summary,
                "category": video.category,
                "topics": video.topics,
                "segments": [
                    {
                        "start_time": segment.start_time,
                        "end_time": segment.end_time,
                        "transcript": segment.transcript,
                        "subcategory": segment.subcategory,
                        "content_summary": segment.content_summary,
                        "keywords": segment.keywords
                    }
                    for segment in segments
                ]
            }
            
            return {
                **state,
                "video_data": video_data,
                "status": ReportStatus.VIDEO_LOADED
            }
            
        except Exception as e:
            logger.error(f"動画データ読み込み中にエラーが発生: {str(e)}")
            return {
                **state,
                "error": str(e),
                "status": ReportStatus.ERROR
            }
    
    def _generate_report(self, state: ReportState) -> ReportState:
        """
        動画データからレポートを生成するノード
        
        Args:
            state (ReportState): 現在の処理状態
            
        Returns:
            ReportState: 更新された処理状態
        """
        try:
            video_data = state["video_data"]
            format_type = state["format_type"]
            custom_instructions = state.get("custom_instructions")
            
            logger.info(f"レポート生成を開始: {video_data.get('title')}, 形式: {format_type}")
            
            # OpenAI APIを使用してレポートを生成
            report_content = self.openai_service.generate_report(
                video_data, 
                format_type, 
                custom_instructions
            )
            
            return {
                **state,
                "report_content": report_content,
                "status": ReportStatus.REPORT_GENERATED
            }
            
        except OpenAIAPIError as e:
            logger.error(f"レポート生成中にエラーが発生: {str(e)}")
            return {
                **state,
                "error": str(e),
                "status": ReportStatus.ERROR
            }
    
    def _save_report(self, state: ReportState) -> ReportState:
        """
        生成されたレポートをデータベースに保存するノード
        
        Args:
            state (ReportState): 現在の処理状態
            
        Returns:
            ReportState: 更新された処理状態
        """
        try:
            video_id = state["video_id"]
            report_content = state["report_content"]
            logger.info(f"レポート保存を開始: {report_content.get('title')}")
            
            # Report エントリの作成
            report = Report(
                video_id=video_id,
                title=report_content["title"],
                format_type=report_content["format_type"],
                content=report_content["content"]
            )
            
            self.db.add(report)
            self.db.flush()  # IDを生成するためにフラッシュ
            
            # データベースにコミット
            self.db.commit()
            
            return {
                **state,
                "saved_report_id": report.id,
                "status": ReportStatus.REPORT_SAVED
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"レポート保存中にエラーが発生: {str(e)}")
            return {
                **state,
                "error": f"レポート保存に失敗しました: {str(e)}",
                "status": ReportStatus.ERROR
            }
    
    def _finalize(self, state: ReportState) -> ReportState:
        """
        処理の最終ステップを実行するノード
        
        Args:
            state (ReportState): 現在の処理状態
            
        Returns:
            ReportState: 更新された処理状態
        """
        logger.info(f"プロセスを完了: レポートID {state.get('saved_report_id')}")
        return {
            **state,
            "status": ReportStatus.COMPLETE
        }
    
    def _should_continue(self, state: ReportState) -> Literal["continue", "error", "complete"]:
        """
        状態に基づいて次のステップを決定する条件関数
        
        Args:
            state (ReportState): 現在の処理状態
            
        Returns:
            Literal["continue", "error", "complete"]: 次のステップの指示
        """
        if state["status"] == ReportStatus.ERROR:
            return "error"
        elif state["status"] == ReportStatus.REPORT_SAVED:
            return "complete"
        else:
            return "continue"
    
    def _build_graph(self) -> StateGraph:
        """
        LangGraphの処理フローを構築する
        
        Returns:
            StateGraph: 構築されたグラフ
        """
        # グラフの初期化
        graph = StateGraph(ReportState)
        
        # ノードの追加
        graph.add_node("load_video_data", self._load_video_data)
        graph.add_node("generate_report", self._generate_report)
        graph.add_node("save_report", self._save_report)
        graph.add_node("finalize", self._finalize)
        
        # エッジの追加（処理フローの定義）
        graph.add_edge("load_video_data", "generate_report")
        graph.add_edge("generate_report", "save_report")
        graph.add_edge("save_report", "finalize")
        
        # 条件分岐の設定
        graph.add_conditional_edges(
            "finalize",
            self._should_continue,
            {
                "continue": "load_video_data",  # 通常はここには戻らない
                "error": END,
                "complete": END
            }
        )
        
        # 開始ノードの設定
        graph.set_entry_point("load_video_data")
        
        return graph.compile()
    
    def generate_report(self, video_id: int, format_type: str, custom_instructions: Optional[str] = None) -> Dict[str, Any]:
        """
        指定された動画IDとフォーマットタイプからレポートを生成する
        
        Args:
            video_id (int): 動画ID
            format_type (str): レポート形式
            custom_instructions (Optional[str], optional): カスタム指示. Defaults to None.
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        try:
            # 初期状態の設定
            initial_state: ReportState = {
                "video_id": video_id,
                "format_type": format_type,
                "custom_instructions": custom_instructions,
                "video_data": None,
                "report_content": None,
                "saved_report_id": None,
                "error": None,
                "status": ReportStatus.INIT
            }
            
            # グラフの実行
            logger.info(f"レポート生成プロセスを開始: 動画ID {video_id}, 形式 {format_type}")
            result = self.graph.invoke(initial_state)
            
            # エラーチェック
            if result["status"] == ReportStatus.ERROR:
                logger.error(f"レポート生成中にエラーが発生: {result.get('error', '不明なエラー')}")
                return {
                    "success": False,
                    "error": result.get("error", "処理中に不明なエラーが発生しました"),
                    "video_id": video_id,
                    "format_type": format_type
                }
            
            # 成功結果の構築
            return {
                "success": True,
                "video_id": video_id,
                "report_id": result.get("saved_report_id"),
                "title": result.get("report_content", {}).get("title"),
                "format_type": format_type,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"レポート生成中に予期しないエラーが発生: {str(e)}")
            return {
                "success": False,
                "error": f"処理中に予期しないエラーが発生しました: {str(e)}",
                "video_id": video_id,
                "format_type": format_type
            }
