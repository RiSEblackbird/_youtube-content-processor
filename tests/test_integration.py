import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import get_db
from app.db.models import Base
from app.schemas.video import ProcessVideoRequest
from app.schemas.report import GenerateReportRequest


# テスト用のin-memoryデータベース設定
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# テスト用のデータベースセッション依存性関数を上書き
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# テスト用のクライアント
@pytest.fixture
def client():
    # テスト用のデータベースの設定
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # テスト後のクリーンアップ
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides = {}


# YouTubeサービスのモック
@pytest.fixture
def mock_youtube_service(monkeypatch):
    """YouTubeServiceをモックする"""
    from app.services.youtube import YouTubeService
    from unittest.mock import MagicMock
    
    # モックメソッドの作成
    mock_process = MagicMock()
    mock_process.return_value = (
        {
            "youtube_id": "test123",
            "title": "テスト動画",
            "url": "https://www.youtube.com/watch?v=test123",
            "channel_name": "テストチャンネル",
            "published_at": None,
            "duration_seconds": 600
        },
        [
            {"text": "こんにちは", "start": 0.0, "duration": 1.0},
            {"text": "テストです", "start": 1.0, "duration": 1.0}
        ]
    )
    
    # モンキーパッチを適用
    monkeypatch.setattr(YouTubeService, "process_video_url", mock_process)
    
    return mock_process


# Claudeサービスのモック
@pytest.fixture
def mock_claude_service(monkeypatch):
    """ClaudeServiceをモックする"""
    from app.services.claude import ClaudeService
    from unittest.mock import MagicMock
    
    # モックインスタンスの作成
    mock_claude = MagicMock()
    
    # analyze_transcript メソッドのモック
    mock_analyze = MagicMock()
    mock_analyze.return_value = {
        "summary": "これはテスト動画の要約です。",
        "category": "テスト",
        "topics": ["テスト1", "テスト2", "テスト3"],
        "segments": [
            {
                "start_time": 0.0,
                "end_time": 10.0,
                "transcript": "こんにちは、テストです。",
                "subcategory": "挨拶",
                "content_summary": "挨拶部分です。",
                "keywords": ["挨拶", "テスト"]
            },
            {
                "start_time": 10.0,
                "end_time": 20.0,
                "transcript": "これはテスト動画です。",
                "subcategory": "説明",
                "content_summary": "説明部分です。",
                "keywords": ["説明", "テスト動画"]
            }
        ]
    }
    
    # __init__とanalyze_transcriptをモック
    monkeypatch.setattr(ClaudeService, "__init__", lambda self: None)
    monkeypatch.setattr(ClaudeService, "analyze_transcript", mock_analyze)
    
    return mock_analyze


# OpenAIサービスのモック
@pytest.fixture
def mock_openai_service(monkeypatch):
    """OpenAIServiceをモックする"""
    from app.services.openai import OpenAIService
    from unittest.mock import MagicMock
    
    # モックインスタンスの作成
    mock_openai = MagicMock()
    
    # generate_report メソッドのモック
    mock_generate = MagicMock()
    mock_generate.return_value = {
        "title": "テスト動画 - Summary Report",
        "format_type": "summary",
        "content": "これはテスト動画のサマリーレポートです。内容は省略されています。"
    }
    
    # __init__とgenerate_reportをモック
    monkeypatch.setattr(OpenAIService, "__init__", lambda self: None)
    monkeypatch.setattr(OpenAIService, "generate_report", mock_generate)
    
    return mock_generate


# 統合テスト
class TestIntegration:
    """APIエンドポイントの統合テスト"""
    
    def test_root_endpoint(self, client):
        """ルートエンドポイントのテスト"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
    
    def test_health_check(self, client):
        """ヘルスチェックエンドポイントのテスト"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_process_video(self, client, mock_youtube_service, mock_claude_service):
        """動画処理エンドポイントのテスト"""
        # リクエストデータ
        request_data = {
            "youtube_url": "https://www.youtube.com/watch?v=test123"
        }
        
        # APIリクエスト
        response = client.post("/api/v1/videos/", json=request_data)
        
        # レスポンス検証
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data
        assert "video_id" in data
        assert "title" in data
        
        # モックが正しく呼ばれたことを確認
        mock_youtube_service.assert_called_once_with("https://www.youtube.com/watch?v=test123", "ja")
        mock_claude_service.assert_called_once()
    
    def test_list_videos(self, client, mock_youtube_service, mock_claude_service):
        """動画リスト取得エンドポイントのテスト"""
        # 事前に動画を登録
        request_data = {
            "youtube_url": "https://www.youtube.com/watch?v=test123"
        }
        client.post("/api/v1/videos/", json=request_data)
        
        # APIリクエスト
        response = client.get("/api/v1/videos/")
        
        # レスポンス検証
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert "id" in data[0]
        assert "title" in data[0]
    
    def test_get_video_detail(self, client, mock_youtube_service, mock_claude_service):
        """動画詳細取得エンドポイントのテスト"""
        # 事前に動画を登録
        request_data = {
            "youtube_url": "https://www.youtube.com/watch?v=test123"
        }
        response = client.post("/api/v1/videos/", json=request_data)
        video_id = response.json()["video_id"]
        
        # APIリクエスト
        response = client.get(f"/api/v1/videos/{video_id}")
        
        # レスポンス検証
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == int(video_id)
        assert data["title"] == "テスト動画"
        assert "segments" in data
        assert len(data["segments"]) > 0
    
    def test_generate_report(self, client, mock_youtube_service, mock_claude_service, mock_openai_service):
        """レポート生成エンドポイントのテスト"""
        # 事前に動画を登録
        request_data = {
            "youtube_url": "https://www.youtube.com/watch?v=test123"
        }
        response = client.post("/api/v1/videos/", json=request_data)
        video_id = response.json()["video_id"]
        
        # レポート生成リクエスト
        report_request = {
            "video_id": int(video_id),
            "format_type": "summary",
            "custom_instructions": "テスト用の指示"
        }
        
        # APIリクエスト
        response = client.post("/api/v1/reports/generate", json=report_request)
        
        # レスポンス検証
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["video_id"] == int(video_id)
        assert "report_id" in data
        assert data["format_type"] == "summary"
        
        # モックが正しく呼ばれたことを確認
        mock_openai_service.assert_called_once()
    
    def test_list_reports(self, client, mock_youtube_service, mock_claude_service, mock_openai_service):
        """レポートリスト取得エンドポイントのテスト"""
        # 事前に動画を登録
        request_data = {
            "youtube_url": "https://www.youtube.com/watch?v=test123"
        }
        response = client.post("/api/v1/videos/", json=request_data)
        video_id = response.json()["video_id"]
        
        # レポート生成
        report_request = {
            "video_id": int(video_id),
            "format_type": "summary"
        }
        client.post("/api/v1/reports/generate", json=report_request)
        
        # APIリクエスト
        response = client.get("/api/v1/reports/")
        
        # レスポンス検証
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert "id" in data[0]
        assert "title" in data[0]
        assert "format_type" in data[0]
    
    def test_get_report_detail(self, client, mock_youtube_service, mock_claude_service, mock_openai_service):
        """レポート詳細取得エンドポイントのテスト"""
        # 事前に動画を登録
        request_data = {
            "youtube_url": "https://www.youtube.com/watch?v=test123"
        }
        response = client.post("/api/v1/videos/", json=request_data)
        video_id = response.json()["video_id"]
        
        # レポート生成
        report_request = {
            "video_id": int(video_id),
            "format_type": "summary"
        }
        response = client.post("/api/v1/reports/generate", json=report_request)
        report_id = response.json()["report_id"]
        
        # APIリクエスト
        response = client.get(f"/api/v1/reports/{report_id}")
        
        # レスポンス検証
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == report_id
        assert data["video_id"] == int(video_id)
        assert "content" in data
        assert data["format_type"] == "summary"
