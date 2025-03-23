from typing import Dict, List, Any, Optional
from openai import OpenAI

from app.config import settings
from app.core.logging import logger
from app.core.exceptions import OpenAIAPIError


class OpenAIService:
    """
    OpenAI APIを使用してデータベースから取得した動画情報から様々な形式のレポートを生成するサービスクラス
    o1-miniモデルを利用して効率的に異なるフォーマットの資料を作成する
    """
    
    def __init__(self) -> None:
        """
        OpenAIServiceの初期化メソッド
        OpenAIクライアントを設定する
        """
        try:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = "o1-mini"  # o1-miniモデルを使用
            logger.info("OpenAI APIクライアントを初期化しました")
        except Exception as e:
            logger.error(f"OpenAI APIクライアントの初期化に失敗: {str(e)}")
            raise OpenAIAPIError(f"OpenAI APIクライアントの初期化に失敗しました: {str(e)}")
    
    def generate_report(self, 
                       video_data: Dict[str, Any], 
                       format_type: str,
                       custom_instructions: Optional[str] = None) -> Dict[str, Any]:
        """
        動画データから指定された形式のレポートを生成する
        
        Args:
            video_data (Dict[str, Any]): 動画データとセグメント情報を含む辞書
            format_type (str): レポート形式 ('summary', 'detailed', 'presentation', 'markdown', 'bullet_points')
            custom_instructions (Optional[str], optional): カスタム指示. Defaults to None.
            
        Returns:
            Dict[str, Any]: 生成されたレポート情報
            
        Raises:
            OpenAIAPIError: レポート生成に失敗した場合
        """
        try:
            # 動画データから必要な情報を抽出
            video_title = video_data.get("title", "タイトル不明")
            video_summary = video_data.get("summary", "")
            video_category = video_data.get("category", "")
            video_topics = video_data.get("topics", [])
            
            # セグメント情報を抽出
            segments = video_data.get("segments", [])
            segments_info = []
            
            for segment in segments:
                segment_info = {
                    "start_time": segment.get("start_time", 0),
                    "end_time": segment.get("end_time", 0),
                    "subcategory": segment.get("subcategory", ""),
                    "content_summary": segment.get("content_summary", ""),
                    "keywords": segment.get("keywords", [])
                }
                segments_info.append(segment_info)
            
            # 形式に基づいたプロンプトテンプレートの選択
            format_templates = {
                "summary": "動画の要点をまとめた簡潔な要約（800-1000文字）を作成してください。",
                "detailed": "動画の詳細な分析レポート（2000-3000文字）をセクションに分けて作成してください。各トピックに対する深い考察を含めてください。",
                "presentation": "プレゼンテーション用のスライド構成を作成してください。タイトルスライド、アジェンダ、各トピックのスライド（要点箇条書き）、結論スライドを含めてください。",
                "markdown": "Markdown形式の文書を作成してください。見出し、箇条書き、強調などのMarkdown記法を適切に使用してください。",
                "bullet_points": "動画の主要ポイントを箇条書きリストで作成してください。主要トピックごとにグループ化してください。"
            }
            
            template = format_templates.get(format_type, format_templates["summary"])
            
            # カスタム指示がある場合は追加
            if custom_instructions:
                template = f"{template}\n\n追加指示: {custom_instructions}"
            
            # プロンプトの構築
            prompt = f"""
            以下の動画情報を基にして、{format_type}形式のレポートを作成してください。

            # 動画情報
            タイトル: {video_title}
            カテゴリ: {video_category}
            概要: {video_summary}
            トピック: {', '.join(video_topics)}

            # セグメント情報
            {segments_info}

            # 指示
            {template}
            
            レポートは日本語で作成し、専門的かつ読みやすい文体を心がけてください。
            動画内の重要な情報をすべて含め、論理的に構成してください。
            """
            
            # OpenAI APIを呼び出し
            logger.info(f"OpenAI APIを呼び出し: {video_title}, 形式: {format_type}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "あなたは高品質なレポート作成の専門家です。与えられた動画情報から、指定された形式で魅力的かつ情報豊富なレポートを作成してください。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # クリエイティブさと一貫性のバランス
                max_tokens=4000
            )
            
            # レスポンスからレポート内容を抽出
            report_content = response.choices[0].message.content
            
            # レポートタイトルの生成
            report_title = f"{video_title} - {format_type.capitalize()} Report"
            
            # 結果の構築
            result = {
                "title": report_title,
                "format_type": format_type,
                "content": report_content
            }
            
            logger.info(f"レポート生成が完了: {report_title}")
            return result
            
        except Exception as e:
            logger.error(f"レポート生成中にエラーが発生: {str(e)}")
            raise OpenAIAPIError(f"レポート生成に失敗しました: {str(e)}")
