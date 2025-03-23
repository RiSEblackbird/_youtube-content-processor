from typing import Dict, List, Any, TypedDict, Annotated, Optional, Literal
from enum import Enum
import json
from sqlalchemy.orm import Session

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor, tools

from app.services.youtube import YouTubeService
from app.services.claude import ClaudeService
from app.db.models import Video, VideoSegment
from app.core.logging import logger
from app.core.exceptions import YouTubeExtractError, ClaudeAPIError, DatabaseError


class ProcessState(TypedDict):
    """
    動画処理グラフの状態を表す型定義
    LangGraphの状態管理に使用する
    """
    video_url: str
    video_id: Optional[str]
    metadata: Optional[Dict[str, Any]]
    transcript: Optional[List[Dict[str, Any]]]
    analysis: Optional[Dict[str, Any]]
    error: Optional[str]
    status: str


class ProcessStatus(str, Enum):
    """
    処理状態を表す列挙型
    グラフの流れ制御に使用する
    """
    INIT = "initialized"
    METADATA_EXTRACTED = "metadata_extracted"
    TRANSCRIPT_EXTRACTED = "transcript_extracted"
    ANALYSIS_COMPLETED = "analysis_completed"
    SAVED_TO_DB = "saved_to_db"
    ERROR = "error"
    COMPLETE = "complete"


class VideoProcessorGraph:
    """
    YouTubeの動画URLから情報を抽出し、Claudeで分析し、データベースに保存するLangGraphプロセス
    複数のステップを持つ処理フローを効率的に管理するために使用
    """
    
    def __init__(self, db: Session):
        """
        VideoProcessorGraphの初期化メソッド
        
        Args:
            db (Session): データベースセッション
        """
        self.db = db
        self.youtube_service = YouTubeService()
        self.claude_service = ClaudeService()
        self.graph = self._build_graph()
        logger.info("VideoProcessorGraphを初期化しました")
    
    def _extract_metadata(self, state: ProcessState) -> ProcessState:
        """
        動画URLからメタデータを抽出するノード
        
        Args:
            state (ProcessState): 現在の処理状態
            
        Returns:
            ProcessState: 更新された処理状態
        """
        try:
            url = state["video_url"]
            logger.info(f"メタデータ抽出を開始: {url}")
            
            video_id = self.youtube_service.extract_video_id(url)
            metadata = self.youtube_service.get_video_metadata(url)
            
            return {
                **state,
                "video_id": video_id,
                "metadata": metadata,
                "status": ProcessStatus.METADATA_EXTRACTED
            }
            
        except YouTubeExtractError as e:
            logger.error(f"メタデータ抽出中にエラーが発生: {str(e)}")
            return {
                **state,
                "error": str(e),
                "status": ProcessStatus.ERROR
            }
    
    def _extract_transcript(self, state: ProcessState) -> ProcessState:
        """
        動画IDから文字起こしを抽出するノード
        
        Args:
            state (ProcessState): 現在の処理状態
            
        Returns:
            ProcessState: 更新された処理状態
        """
        try:
            video_id = state["video_id"]
            logger.info(f"文字起こし抽出を開始: {video_id}")
            
            transcript = self.youtube_service.get_transcript(video_id)
            
            return {
                **state,
                "transcript": transcript,
                "status": ProcessStatus.TRANSCRIPT_EXTRACTED
            }
            
        except YouTubeExtractError as e:
            logger.error(f"文字起こし抽出中にエラーが発生: {str(e)}")
            return {
                **state,
                "error": str(e),
                "status": ProcessStatus.ERROR
            }
    
    def _analyze_content(self, state: ProcessState) -> ProcessState:
        """
        メタデータと文字起こしからコンテンツを分析するノード
        
        Args:
            state (ProcessState): 現在の処理状態
            
        Returns:
            ProcessState: 更新された処理状態
        """
        try:
            metadata = state["metadata"]
            transcript = state["transcript"]
            logger.info(f"コンテンツ分析を開始: {metadata.get('title', 'タイトル不明')}")
            
            analysis = self.claude_service.analyze_transcript(metadata, transcript)
            
            return {
                **state,
                "analysis": analysis,
                "status": ProcessStatus.ANALYSIS_COMPLETED
            }
            
        except ClaudeAPIError as e:
            logger.error(f"コンテンツ分析中にエラーが発生: {str(e)}")
            return {
                **state,
                "error": str(e),
                "status": ProcessStatus.ERROR
            }
    
    def _save_to_database(self, state: ProcessState) -> ProcessState:
        """
        分析結果をデータベースに保存するノード
        
        Args:
            state (ProcessState): 現在の処理状態
            
        Returns:
            ProcessState: 更新された処理状態
        """
        try:
            metadata = state["metadata"]
            analysis = state["analysis"]
            logger.info(f"データベース保存を開始: {metadata.get('title', 'タイトル不明')}")
            
            # Video エントリの作成
            video = Video(
                youtube_id=metadata["youtube_id"],
                title=metadata["title"],
                url=metadata["url"],
                channel_name=metadata.get("channel_name"),
                published_at=metadata.get("published_at"),
                duration_seconds=metadata.get("duration_seconds"),
                summary=analysis.get("summary"),
                category=analysis.get("category"),
                topics=analysis.get("topics"),
                processed=True
            )
            
            self.db.add(video)
            self.db.flush()  # IDを生成するためにフラッシュ
            
            # VideoSegment エントリの作成
            segments = analysis.get("segments", [])
            for segment in segments:
                video_segment = VideoSegment(
                    video_id=video.id,
                    start_time=segment.get("start_time", 0),
                    end_time=segment.get("end_time", 0),
                    transcript=segment.get("transcript", ""),
                    subcategory=segment.get("subcategory", ""),
                    content_summary=segment.get("content_summary", ""),
                    keywords=segment.get("keywords", [])
                )
                self.db.add(video_segment)
            
            # データベースにコミット
            self.db.commit()
            
            return {
                **state,
                "status": ProcessStatus.SAVED_TO_DB
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"データベース保存中にエラーが発生: {str(e)}")
            return {
                **state,
                "error": f"データベース保存に失敗しました: {str(e)}",
                "status": ProcessStatus.ERROR
            }
    
    def _finalize(self, state: ProcessState) -> ProcessState:
        """
        処理の最終ステップを実行するノード
        
        Args:
            state (ProcessState): 現在の処理状態
            
        Returns:
            ProcessState: 更新された処理状態
        """
        logger.info(f"プロセスを完了: {state.get('video_url')}")
        return {
            **state,
            "status": ProcessStatus.COMPLETE
        }
    
    def _should_continue(self, state: ProcessState) -> Literal["continue", "error", "complete"]:
        """
        状態に基づいて次のステップを決定する条件関数
        
        Args:
            state (ProcessState): 現在の処理状態
            
        Returns:
            Literal["continue", "error", "complete"]: 次のステップの指示
        """
        if state["status"] == ProcessStatus.ERROR:
            return "error"
        elif state["status"] == ProcessStatus.SAVED_TO_DB:
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
        graph = StateGraph(ProcessState)
        
        # ノードの追加
        graph.add_node("extract_metadata", self._extract_metadata)
        graph.add_node("extract_transcript", self._extract_transcript)
        graph.add_node("analyze_content", self._analyze_content)
        graph.add_node("save_to_database", self._save_to_database)
        graph.add_node("finalize", self._finalize)
        
        # エッジの追加（処理フローの定義）
        graph.add_edge("extract_metadata", "extract_transcript")
        graph.add_edge("extract_transcript", "analyze_content")
        graph.add_edge("analyze_content", "save_to_database")
        graph.add_edge("save_to_database", "finalize")
        
        # 条件分岐の設定
        graph.add_conditional_edges(
            "finalize",
            self._should_continue,
            {
                "continue": "extract_metadata",  # 通常はここには戻らない
                "error": END,
                "complete": END
            }
        )
        
        # 開始ノードの設定
        graph.set_entry_point("extract_metadata")
        
        return graph.compile()
    
    def process_video(self, video_url: str) -> Dict[str, Any]:
        """
        動画URLから処理を開始し、結果を返す
        
        Args:
            video_url (str): 処理するYouTube動画のURL
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        try:
            # 初期状態の設定
            initial_state: ProcessState = {
                "video_url": video_url,
                "video_id": None,
                "metadata": None,
                "transcript": None,
                "analysis": None,
                "error": None,
                "status": ProcessStatus.INIT
            }
            
            # グラフの実行
            logger.info(f"動画処理を開始: {video_url}")
            result = self.graph.invoke(initial_state)
            
            # エラーチェック
            if result["status"] == ProcessStatus.ERROR:
                logger.error(f"動画処理中にエラーが発生: {result.get('error', '不明なエラー')}")
                return {
                    "success": False,
                    "error": result.get("error", "処理中に不明なエラーが発生しました"),
                    "video_url": video_url
                }
            
            # 成功結果の構築
            return {
                "success": True,
                "video_url": video_url,
                "video_id": result.get("video_id"),
                "title": result.get("metadata", {}).get("title"),
                "segments_count": len(result.get("analysis", {}).get("segments", [])),
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"動画処理中に予期しないエラーが発生: {str(e)}")
            return {
                "success": False,
                "error": f"処理中に予期しないエラーが発生しました: {str(e)}",
                "video_url": video_url
            }
