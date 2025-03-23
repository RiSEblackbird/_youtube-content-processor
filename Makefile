.PHONY: build run test lint clean setup logs deploy db-migrate db-upgrade gcp-setup

# アプリケーション設定
APP_NAME := youtube-content-processor
PORT := 8000

# GCP設定
GCP_PROJECT := $(shell gcloud config get-value project)
GCP_REGION := asia-northeast1
GCP_REPOSITORY := youtube-content-processor

# Dockerコマンド
build:
	docker-compose build

run:
	docker-compose up

run-d:
	docker-compose up -d

stop:
	docker-compose down

restart:
	docker-compose restart

# テストコマンド
test:
	docker-compose run --rm app pytest -xvs

test-cov:
	docker-compose run --rm app pytest --cov=app tests/

# リンティングとフォーマット
lint:
	docker-compose run --rm app flake8 app/ tests/

format:
	docker-compose run --rm app black app/ tests/

# 開発補助
logs:
	docker-compose logs -f app

shell:
	docker-compose run --rm app bash

# データベース操作
db-init:
	docker-compose run --rm app python -c "from app.db.models import Base; from app.db.session import engine; Base.metadata.create_all(bind=engine)"

db-migrate:
	docker-compose run --rm app alembic revision --autogenerate -m "$(message)"

db-upgrade:
	docker-compose run --rm app alembic upgrade head

db-downgrade:
	docker-compose run --rm app alembic downgrade -1

# セットアップ
setup:
	cp .env.example .env
	@echo "Please update .env file with your credentials"
	docker-compose build

# デプロイ関連
gcp-build:
	docker build -t $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT)/$(GCP_REPOSITORY)/api:latest .

gcp-push:
	docker push $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT)/$(GCP_REPOSITORY)/api:latest

gcp-deploy:
	gcloud run deploy $(APP_NAME) \
		--image=$(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT)/$(GCP_REPOSITORY)/api:latest \
		--region=$(GCP_REGION) \
		--platform=managed \
		--allow-unauthenticated \
		--memory=2Gi \
		--cpu=2 \
		--min-instances=1 \
		--max-instances=10 \
		--set-secrets=/app/.env=app-secrets:latest \
		--add-cloudsql-instances=$(GCP_PROJECT):$(GCP_REGION):$(APP_NAME)-db \
		--set-env-vars="GCP_PROJECT_ID=$(GCP_PROJECT)"

gcp-setup:
	./scripts/gcp-setup.sh

# クリーンアップ
clean:
	docker-compose down -v
	rm -rf __pycache__
	rm -rf .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

help:
	@echo "利用可能なコマンド:"
	@echo "  make build        - Dockerイメージをビルド"
	@echo "  make run          - アプリケーションをフォアグラウンドで実行"
	@echo "  make run-d        - アプリケーションをバックグラウンドで実行"
	@echo "  make stop         - アプリケーションを停止"
	@echo "  make restart      - アプリケーションを再起動"
	@echo "  make test         - テストを実行"
	@echo "  make test-cov     - カバレッジ付きでテストを実行"
	@echo "  make lint         - コードの静的解析を実行"
	@echo "  make format       - コードフォーマットを実行"
	@echo "  make logs         - アプリケーションのログを表示"
	@echo "  make shell        - アプリケーションコンテナのシェルを起動"
	@echo "  make db-init      - データベースを初期化"
	@echo "  make db-migrate   - データベースマイグレーションファイルを作成 (message=必須)"
	@echo "  make db-upgrade   - データベースをアップグレード"
	@echo "  make db-downgrade - データベースを1バージョン戻す"
	@echo "  make setup        - 初期セットアップを実行"
	@echo "  make gcp-build    - GCP用のDockerイメージをビルド"
	@echo "  make gcp-push     - GCPにDockerイメージをプッシュ"
	@echo "  make gcp-deploy   - GCP Cloud Runにデプロイ"
	@echo "  make gcp-setup    - GCP環境のセットアップを実行"
	@echo "  make clean        - 一時ファイルをクリーンアップ"
	@echo "  make help         - このヘルプを表示"