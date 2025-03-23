# YouTube Content Processor

YouTube動画の内容から様々な資料を作成するWebアプリケーション

## 当Projectの前提

- 各技術要素についての学習準備用のサンプル
- 各技術要素の体系的学習は別途実施
- 要件のプロンプトをClaude 3.7 Sonnetに入力してワンショットで出力したものでスタート
- 適宜編集して実用できるものにしていく

## 機能概要

1. **YouTube動画の文字起こし取得**
   - YouTubeのURLから自動的に文字起こしを取得
   - 複数言語対応

2. **Claude APIによるコンテンツ分析**
   - 動画の概要、カテゴリ、トピックを抽出
   - 意味のあるセグメントに分解
   - タイムスタンプ情報と共に構造化

3. **OpenAI o1-miniによるレポート生成**
   - 様々なフォーマットのレポートを生成
   - サマリー、詳細レポート、プレゼンテーション形式など
   - カスタム指示に基づく柔軟な出力

4. **LangGraphによる処理フロー管理**
   - 各ステップを効率的に管理
   - エラーハンドリングの強化
   - 処理状態の追跡

## 技術スタック

- **バックエンド**: Python 3.11+, FastAPI
- **データベース**: PostgreSQL
- **コンテナ化**: Docker, Docker Compose
- **AI/LLMサービス**: Claude API (Anthropic), OpenAI API
- **処理フロー**: LangGraph
- **クラウドプラットフォーム**: Google Cloud Platform (GCP)
- **テスト**: pytest

## プロジェクト構造

```
youtube-content-processor/
├── docker-compose.yml      # Dockerコンテナ構成
├── Dockerfile              # アプリケーションコンテナ定義
├── requirements.txt        # Pythonパッケージ依存関係
├── Makefile                # 開発・デプロイコマンド集
├── .env.example            # 環境変数テンプレート
├── app/                    # アプリケーションコード
│   ├── main.py             # FastAPIエントリーポイント
│   ├── config.py           # 設定管理
│   ├── api/                # APIエンドポイント
│   │   ├── routes/         # ルーター定義
│   │   │   ├── video.py    # 動画関連エンドポイント
│   │   │   └── report.py   # レポート関連エンドポイント
│   │   └── dependencies.py # APIの依存性関数
│   ├── core/               # コア機能
│   │   ├── security.py     # 認証・認可
│   │   ├── logging.py      # ロギング設定
│   │   └── exceptions.py   # カスタム例外
│   ├── db/                 # データベース
│   │   ├── session.py      # DBセッション管理
│   │   ├── models.py       # SQLAlchemyモデル
│   │   └── crud/           # CRUD操作
│   │       ├── video.py    # 動画のDB操作
│   │       └── report.py   # レポートのDB操作
│   ├── schemas/            # Pydanticスキーマ
│   │   ├── video.py        # 動画関連スキーマ
│   │   └── report.py       # レポート関連スキーマ
│   └── services/           # ビジネスロジック
│       ├── youtube.py      # YouTube API連携
│       ├── claude.py       # Claude API連携
│       ├── openai.py       # OpenAI API連携
│       └── langgraph/      # LangGraph処理フロー
│           ├── video_processor.py  # 動画処理グラフ
│           └── report_generator.py # レポート生成グラフ
└── tests/                  # テストコード
    ├── conftest.py         # テスト構成
    ├── test_integration.py # 統合テスト
    └── test_services/      # サービステスト
        └── test_youtube.py # YouTube機能テスト
```

### 主要コンポーネント

- **API層**: FastAPIを使用したRESTful APIエンドポイント
- **サービス層**: 外部APIとの連携とビジネスロジック
- **データ層**: SQLAlchemyを使用したORMとデータアクセス
- **スキーマ層**: Pydanticによるデータバリデーション
- **LangGraph**: 複雑なAI処理のワークフロー管理

## セットアップ手順

### 事前準備

以下のツールがインストールされていることを確認してください：

- Docker と Docker Compose
- Python 3.11以上（ローカル開発の場合）
- Make（オプション）

### ローカル開発環境のセットアップ

1. リポジトリをクローン：
   ```bash
   git clone https://github.com/yourusername/youtube-content-processor.git
   cd youtube-content-processor
   ```

2. 環境変数の設定：
   ```bash
   cp .env.example .env
   # .envファイルを編集して適切な値を設定
   ```

3. APIキーの設定：
   以下のAPIキーを.envファイルに設定してください：
   - `ANTHROPIC_API_KEY`: Claude APIのキー
   - `OPENAI_API_KEY`: OpenAI APIのキー

4. アプリケーションの構築と起動：
   ```bash
   # Makefileを使用する場合
   make setup
   make run

   # または直接Docker Composeを使用
   docker-compose up -d
   ```

5. APIドキュメントへのアクセス：
   ブラウザで http://localhost:8000/docs を開いてAPI仕様を確認

### GCPへのデプロイ

1. GCP環境のセットアップ：
   ```bash
   make gcp-setup
   ```

2. イメージのビルドとプッシュ：
   ```bash
   make gcp-build
   make gcp-push
   ```

3. Cloud Runへのデプロイ：
   ```bash
   make gcp-deploy
   ```

詳細な手順は `GCPセットアップ手順.md` を参照してください。

## 使用方法

### 1. 動画処理

1. APIを使用して動画を処理します：
   ```bash
   curl -X POST "http://localhost:8000/api/v1/videos/" \
     -H "Content-Type: application/json" \
     -d '{"youtube_url": "https://www.youtube.com/watch?v=your_video_id"}'
   ```

2. 処理結果を確認：
   ```bash
   curl "http://localhost:8000/api/v1/videos/{video_id}"
   ```

### 2. レポート生成

1. 処理済み動画からレポートを生成：
   ```bash
   curl -X POST "http://localhost:8000/api/v1/reports/generate" \
     -H "Content-Type: application/json" \
     -d '{
       "video_id": 1,
       "format_type": "summary",
       "custom_instructions": "簡潔に要約してください"
     }'
   ```

2. 生成されたレポートを取得：
   ```bash
   curl "http://localhost:8000/api/v1/reports/{report_id}"
   ```

## 開発者向け情報

### コードスタイル

- PEP 8に準拠したコードスタイル
- 型ヒントの使用
- 関数とクラスの詳細なドキュメンテーション
- 日本語コメントの使用

### テスト実行

```bash
# 全テストの実行
make test

# カバレッジ付きでテスト実行
make test-cov
```

### リンティングとフォーマット

```bash
# リンティング
make lint

# コードフォーマット
make format
```

## アーキテクチャ

アプリケーションは以下のコンポーネントで構成されています：

- **API**: FastAPIベースのRESTful API
- **サービス層**: YouTube、Claude、OpenAIとの連携
- **LangGraph**: プロセスフローの管理
- **データベース**: PostgreSQLによるデータ永続化
- **GCP統合**: Cloud Run、Cloud SQL、Secret Managerなど

## ライセンス

MITライセンスで提供されています。詳細は `LICENSE` ファイルを参照してください。
