import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.services.youtube import YouTubeService
from app.core.exceptions import YouTubeExtractError


class TestYouTubeService:
    """YouTubeServiceのテストクラス"""

    def test_extract_video_id_valid_url(self):
        """有効なYouTube URLからビデオIDを抽出するテスト"""
        # 通常のYouTube URL
        url1 = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert YouTubeService.extract_video_id(url1) == "dQw4w9WgXcQ"
        
        # 短縮URL
        url2 = "https://youtu.be/dQw4w9WgXcQ"
        assert YouTubeService.extract_video_id(url2) == "dQw4w9WgXcQ"
        
        # 埋め込みURL
        url3 = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        assert YouTubeService.extract_video_id(url3) == "dQw4w9WgXcQ"

    def test_extract_video_id_invalid_url(self):
        """無効なYouTube URLからビデオIDを抽出する際の例外テスト"""
        # 無効なURL
        url = "https://example.com/video"
        with pytest.raises(YouTubeExtractError):
            YouTubeService.extract_video_id(url)

    @patch('app.services.youtube.YouTube')
    def test_get_video_metadata(self, mock_youtube):
        """ビデオメタデータ取得のテスト"""
        # モックのセットアップ
        mock_instance = MagicMock()
        mock_instance.title = "テスト動画"
        mock_instance.author = "テストチャンネル"
        mock_instance.publish_date = datetime(2021, 1, 1)
        mock_instance.length = 600
        mock_youtube.return_value = mock_instance
        
        # テスト対象の実行
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        metadata = YouTubeService.get_video_metadata(url)
        
        # 検証
        assert metadata["youtube_id"] == "dQw4w9WgXcQ"
        assert metadata["title"] == "テスト動画"
        assert metadata["url"] == url
        assert metadata["channel_name"] == "テストチャンネル"
        assert metadata["published_at"] == datetime(2021, 1, 1)
        assert metadata["duration_seconds"] == 600

    @patch('app.services.youtube.YouTube')
    def test_get_video_metadata_error(self, mock_youtube):
        """ビデオメタデータ取得エラーのテスト"""
        # モックのセットアップ - 例外を発生させる
        mock_youtube.side_effect = Exception("API error")
        
        # テスト対象の実行と検証
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        with pytest.raises(YouTubeExtractError):
            YouTubeService.get_video_metadata(url)

    @patch('app.services.youtube.YouTubeTranscriptApi')
    def test_get_transcript(self, mock_transcript_api):
        """文字起こし取得のテスト"""
        # モックのセットアップ
        mock_transcript_list = MagicMock()
        mock_transcript = MagicMock()
        mock_transcript.language = "ja"
        mock_transcript.fetch.return_value = [
            {"text": "こんにちは", "start": 0.0, "duration": 1.0},
            {"text": "テストです", "start": 1.0, "duration": 1.0}
        ]
        mock_transcript_list.find_transcript.return_value = mock_transcript
        mock_transcript_api.list_transcripts.return_value = mock_transcript_list
        
        # テスト対象の実行
        video_id = "dQw4w9WgXcQ"
        transcript = YouTubeService.get_transcript(video_id)
        
        # 検証
        assert len(transcript) == 2
        assert transcript[0]["text"] == "こんにちは"
        assert transcript[1]["text"] == "テストです"

    @patch('app.services.youtube.YouTubeTranscriptApi')
    def test_get_transcript_language_fallback(self, mock_transcript_api):
        """指定した言語が見つからない場合の文字起こし取得のテスト"""
        # モックのセットアップ
        mock_transcript_list = MagicMock()
        mock_transcript = MagicMock()
        mock_transcript.language = "en"
        mock_transcript.fetch.return_value = [
            {"text": "Hello", "start": 0.0, "duration": 1.0},
            {"text": "This is a test", "start": 1.0, "duration": 1.0}
        ]
        
        # 最初の find_transcript で例外を発生させ、自動生成の探索をテスト
        mock_transcript_list.find_transcript.side_effect = [Exception("Not found"), mock_transcript]
        mock_transcript_list.find_generated_transcript.return_value = mock_transcript
        mock_transcript_api.list_transcripts.return_value = mock_transcript_list
        
        # テスト対象の実行
        video_id = "dQw4w9WgXcQ"
        transcript = YouTubeService.get_transcript(video_id, "ja")
        
        # 検証
        assert len(transcript) == 2
        assert transcript[0]["text"] == "Hello"
        assert transcript[1]["text"] == "This is a test"

    @patch('app.services.youtube.YouTubeTranscriptApi')
    def test_get_transcript_error(self, mock_transcript_api):
        """文字起こし取得エラーのテスト"""
        # モックのセットアップ - 例外を発生させる
        from youtube_transcript_api import TranscriptsDisabled
        mock_transcript_api.list_transcripts.side_effect = TranscriptsDisabled("Transcripts disabled")
        
        # テスト対象の実行と検証
        video_id = "dQw4w9WgXcQ"
        with pytest.raises(YouTubeExtractError):
            YouTubeService.get_transcript(video_id)

    @patch.object(YouTubeService, 'extract_video_id')
    @patch.object(YouTubeService, 'get_video_metadata')
    @patch.object(YouTubeService, 'get_transcript')
    def test_process_video_url(self, mock_get_transcript, mock_get_metadata, mock_extract_id):
        """動画URL処理の統合テスト"""
        # モックのセットアップ
        mock_extract_id.return_value = "dQw4w9WgXcQ"
        mock_get_metadata.return_value = {
            "youtube_id": "dQw4w9WgXcQ",
            "title": "テスト動画",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "channel_name": "テストチャンネル",
            "published_at": datetime(2021, 1, 1),
            "duration_seconds": 600
        }
        mock_get_transcript.return_value = [
            {"text": "こんにちは", "start": 0.0, "duration": 1.0},
            {"text": "テストです", "start": 1.0, "duration": 1.0}
        ]
        
        # テスト対象の実行
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        metadata, transcript = YouTubeService.process_video_url(url)
        
        # 検証
        assert metadata["youtube_id"] == "dQw4w9WgXcQ"
        assert metadata["title"] == "テスト動画"
        assert len(transcript) == 2
        assert transcript[0]["text"] == "こんにちは"
        
        # モックが正しく呼ばれたことを確認
        mock_extract_id.assert_called_once_with(url)
        mock_get_metadata.assert_called_once_with(url)
        mock_get_transcript.assert_called_once_with("dQw4w9WgXcQ", "ja")

    @patch.object(YouTubeService, 'extract_video_id')
    def test_process_video_url_error(self, mock_extract_id):
        """動画URL処理エラーのテスト"""
        # モックのセットアップ - 例外を発生させる
        mock_extract_id.side_effect = YouTubeExtractError("Invalid URL")
        
        # テスト対象の実行と検証
        url = "https://example.com/video"
        with pytest.raises(YouTubeExtractError):
            YouTubeService.process_video_url(url)
