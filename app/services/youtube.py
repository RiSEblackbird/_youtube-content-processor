import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from pytube import YouTube

from app.core.logging import logger
from app.core.exceptions import YouTubeExtractError


class YouTubeService:
    """
    YouTubeの動画情報と文字起こしを取得するためのサービスクラス
    動画IDからメタデータと字幕情報を抽出し、処理しやすい形式に変換する
    """

    @staticmethod
    def extract_video_id(url: str) -> str:
        """
        YouTubeのURLから動画IDを抽出する

        Args:
            url (str): YouTubeのURL

        Returns:
            str: 抽出された動画ID

        Raises:
            YouTubeExtractError: URLから動画IDを抽出できない場合
        """
        # YouTubeの標準的なURLパターン
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
            r'(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
            r'(?:youtube\.com\/v\/)([a-zA-Z0-9_-]{11})'
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        # パターンに一致しない場合はエラー
        logger.error(f"無効なYouTube URL: {url}")
        raise YouTubeExtractError(f"無効なYouTube URLです: {url}")

    @staticmethod
    def get_video_metadata(url: str) -> Dict[str, Any]:
        """
        YouTubeの動画メタデータを取得する

        Args:
            url (str): YouTubeのURL

        Returns:
            Dict[str, Any]: 動画のメタデータ

        Raises:
            YouTubeExtractError: メタデータの取得に失敗した場合
        """
        try:
            video_id = YouTubeService.extract_video_id(url)
            youtube = YouTube(url)

            # 公開日時の処理
            published_at = None
            if youtube.publish_date:
                published_at = youtube.publish_date

            metadata = {
                "youtube_id": video_id,
                "title": youtube.title,
                "url": url,
                "channel_name": youtube.author,
                "published_at": published_at,
                "duration_seconds": youtube.length
            }

            logger.info(f"動画メタデータを取得: {video_id}")
            return metadata

        except Exception as e:
            logger.error(f"動画メタデータの取得中にエラーが発生: {str(e)}")
            raise YouTubeExtractError(f"動画メタデータの取得に失敗しました: {str(e)}")

    @staticmethod
    def get_transcript(video_id: str, language: str = "ja") -> List[Dict[str, Any]]:
        """
        YouTubeの文字起こしを取得する

        Args:
            video_id (str): YouTubeの動画ID
            language (str, optional): 文字起こしの言語コード. Defaults to "ja".

        Returns:
            List[Dict[str, Any]]: 文字起こしデータのリスト

        Raises:
            YouTubeExtractError: 文字起こしの取得に失敗した場合
        """
        try:
            # 指定された言語で文字起こしを取得
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # 指定言語の文字起こしを探す
            try:
                transcript = transcript_list.find_transcript([language])
            except:
                # 指定言語が見つからない場合は自動生成の字幕を試みる
                logger.warning(f"指定された言語 '{language}' の文字起こしが見つかりません。自動生成字幕を試行")
                try:
                    transcript = transcript_list.find_generated_transcript([language])
                except:
                    # 最初の言語を使用
                    logger.warning(f"自動生成字幕も見つかりません。利用可能な最初の言語を使用")
                    transcript = transcript_list.find_transcript(transcript_list.transcript_data.keys())

            # 文字起こしデータの取得
            transcript_data = transcript.fetch()

            logger.info(f"文字起こしを取得: {video_id}, 言語: {transcript.language}, エントリ数: {len(transcript_data)}")
            return transcript_data

        except TranscriptsDisabled:
            logger.error(f"この動画には文字起こしが無効になっています: {video_id}")
            raise YouTubeExtractError(f"この動画には文字起こしが無効になっています")

        except Exception as e:
            logger.error(f"文字起こしの取得中にエラーが発生: {str(e)}")
            raise YouTubeExtractError(f"文字起こしの取得に失敗しました: {str(e)}")

    @classmethod
    def process_video_url(cls, url: str, language: str = "ja") -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        YouTubeのURLからメタデータと文字起こしを一度に取得する

        Args:
            url (str): YouTubeのURL
            language (str, optional): 文字起こしの言語コード. Defaults to "ja".

        Returns:
            Tuple[Dict[str, Any], List[Dict[str, Any]]]: (メタデータ, 文字起こしデータのリスト)

        Raises:
            YouTubeExtractError: 処理に失敗した場合
        """
        try:
            video_id = cls.extract_video_id(url)
            metadata = cls.get_video_metadata(url)
            transcript = cls.get_transcript(video_id, language)

            return metadata, transcript

        except YouTubeExtractError as e:
            # 既に適切にログとエラーが処理されているため、そのまま再送出
            raise

        except Exception as e:
            logger.error(f"YouTubeの処理中に予期しないエラーが発生: {str(e)}")
            raise YouTubeExtractError(f"YouTubeの処理中に予期しないエラーが発生しました: {str(e)}")
