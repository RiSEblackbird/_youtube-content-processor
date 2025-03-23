import json
from typing import Dict, List, Any, Optional
from anthropic import Anthropic

from app.config import settings
from app.core.logging import logger
from app.core.exceptions import ClaudeAPIError


class ClaudeService:
    """
    Claude APIを使用して動画文字起こしの内容を分析・構造化するサービスクラス
    文字起こしから意味のあるセグメント、カテゴリ、サマリーなどを抽出する
    """
    
    def __init__(self) -> None:
        """
        ClaudeServiceの初期化メソッド
        Anthropicクライアントを設定する
        """
        try:
            self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            self.model = "claude-3-opus-20240229"  # 最新の高性能モデルを使用
            logger.info("Claude APIクライアントを初期化しました")
        except Exception as e:
            logger.error(f"Claude APIクライアントの初期化に失敗: {str(e)}")
            raise ClaudeAPIError(f"Claude APIクライアントの初期化に失敗しました: {str(e)}")
    
    def analyze_transcript(self, 
                          video_metadata: Dict[str, Any], 
                          transcript_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        動画の文字起こしを分析し、構造化された情報を返す
        
        Args:
            video_metadata (Dict[str, Any]): 動画のメタデータ
            transcript_data (List[Dict[str, Any]]): 文字起こしデータのリスト
            
        Returns:
            Dict[str, Any]: 構造化された分析結果
            
        Raises:
            ClaudeAPIError: 分析に失敗した場合
        """
        try:
            # 文字起こしデータを連結してフルトランスクリプトを作成
            full_transcript = " ".join([item["text"] for item in transcript_data])
            
            # メタデータから必要な情報を抽出
            video_title = video_metadata.get("title", "タイトル不明")
            channel_name = video_metadata.get("channel_name", "チャンネル不明")
            
            # Claudeへのプロンプト設計
            prompt = f"""
            あなたは動画コンテンツアナライザーです。以下のYouTube動画の文字起こしを分析し、構造化された形式で情報を提供してください。

            # 動画情報
            タイトル: {video_title}
            チャンネル: {channel_name}

            # 文字起こし
            {full_transcript}

            # 指示
            以下の情報を抽出してJSON形式で返してください。他の文章は一切含めないでください。

            1. summary: 動画の概要（400-600文字）
            2. category: 動画の主要カテゴリ（1つのみ）
            3. topics: 動画で扱われている主要トピックのリスト（3-7項目）
            4. segments: 動画の意味のある区切り（セグメント）のリスト。各セグメントには以下を含めてください:
               - start_time: おおよその開始時間（秒）を推測してください
               - end_time: おおよその終了時間（秒）を推測してください
               - transcript: このセグメントの文字起こし部分
               - subcategory: このセグメントのサブカテゴリ
               - content_summary: このセグメントの要約（100-200文字）
               - keywords: このセグメントの重要なキーワード（3-5項目）

            文字起こしの内容を基に、動画全体の流れを理解し、論理的かつ意味のあるセグメントに分割してください。
            返却するJSONは、必ず上記の構造に準拠し、他の文章やメタ情報は含めないでください。
            """
            
            # Claude APIを呼び出し
            logger.info(f"Claude APIを呼び出し: {video_title}")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.2,  # より決定論的な結果のために低い温度を設定
                system="あなたは動画コンテンツ分析の専門家です。JSONフォーマットで構造化された分析結果のみを提供してください。",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # レスポンスをJSONとしてパース
            result_text = response.content[0].text
            # JSON部分だけを抽出（余分なテキストがある場合）
            json_start = result_text.find('{')
            json_end = result_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = result_text[json_start:json_end]
                result = json.loads(json_text)
            else:
                # JSON形式でなかった場合のエラーハンドリング
                logger.error("Claude APIから有効なJSON応答を受信できませんでした")
                raise ClaudeAPIError("Claude APIから有効なJSON応答を受信できませんでした")
            
            logger.info(f"文字起こしの分析が完了: {video_title}, セグメント数: {len(result.get('segments', []))}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Claude APIレスポンスのJSONパースに失敗: {str(e)}")
            raise ClaudeAPIError(f"Claude APIレスポンスのJSONパースに失敗しました: {str(e)}")
            
        except Exception as e:
            logger.error(f"文字起こしの分析中にエラーが発生: {str(e)}")
            raise ClaudeAPIError(f"文字起こしの分析に失敗しました: {str(e)}")
