# GCPセットアップ手順

## 1. 必要なサービスの有効化

以下のGCPサービスを有効化します：

```bash
gcloud services enable \
  cloudbuild.googleapis.com \
  cloudrun.googleapis.com \
  secretmanager.googleapis.com \
  sqladmin.googleapis.com \
  artifactregistry.googleapis.com
```

## 2. データベースのセットアップ

### Cloud SQL Postgresインスタンスの作成

```bash
gcloud sql instances create youtube-content-processor-db \
  --database-version=POSTGRES_14 \
  --cpu=2 \
  --memory=4GB \
  --region=asia-northeast1 \
  --root-password=<安全なパスワード> \
  --storage-type=SSD \
  --storage-size=10GB \
  --availability-type=zonal
```

### データベースとユーザーの作成

```bash
gcloud sql databases create youtube_content_db \
  --instance=youtube-content-processor-db

gcloud sql users create app_user \
  --instance=youtube-content-processor-db \
  --password=<安全なパスワード>
```

## 3. Secretの作成

環境変数を安全に管理するためのSecretを作成します：

```bash
# Secret Managerにシークレットを作成
gcloud secrets create app-secrets --replication-policy=automatic

# .envファイルの内容をシークレットとして保存
gcloud secrets versions add app-secrets --data-file=.env
```

## 4. Artifact Registryの設定

コンテナイメージを保存するためのリポジトリを作成します：

```bash
gcloud artifacts repositories create youtube-content-processor \
  --repository-format=docker \
  --location=asia-northeast1 \
  --description="YouTube Content Processor コンテナリポジトリ"
```

## 5. Docker イメージのビルドとプッシュ

```bash
# プロジェクトIDを環境変数に設定
export PROJECT_ID=$(gcloud config get-value project)

# Dockerイメージをビルド
docker build -t asia-northeast1-docker.pkg.dev/$PROJECT_ID/youtube-content-processor/api:latest .

# イメージをArtifact Registryにプッシュ
docker push asia-northeast1-docker.pkg.dev/$PROJECT_ID/youtube-content-processor/api:latest
```

## 6. Cloud Runのデプロイ

```bash
gcloud run deploy youtube-content-processor \
  --image=asia-northeast1-docker.pkg.dev/$PROJECT_ID/youtube-content-processor/api:latest \
  --region=asia-northeast1 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --min-instances=1 \
  --max-instances=10 \
  --set-secrets=/app/.env=app-secrets:latest \
  --add-cloudsql-instances=$PROJECT_ID:asia-northeast1:youtube-content-processor-db \
  --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID"
```

## 7. データベースマイグレーション（初期化）

データベースのマイグレーションを実行するための一時的なJobを作成します：

```bash
cat <<EOF > migration-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration
spec:
  template:
    spec:
      containers:
      - name: migration
        image: asia-northeast1-docker.pkg.dev/$PROJECT_ID/youtube-content-processor/api:latest
        command: ["alembic", "upgrade", "head"]
        env:
          - name: DATABASE_URI
            valueFrom:
              secretKeyRef:
                name: app-secrets
                key: DATABASE_URI
      restartPolicy: Never
  backoffLimit: 4
EOF

kubectl apply -f migration-job.yaml
```

## 8. Cloud Run サービスの更新

必要に応じてサービスを更新します：

```bash
gcloud run services update youtube-content-processor \
  --region=asia-northeast1 \
  --image=asia-northeast1-docker.pkg.dev/$PROJECT_ID/youtube-content-processor/api:latest
```

## 9. 監視設定

Cloud Monitoringでアラートとダッシュボードを設定します：

```bash
# CPU使用率が80%を超えた場合のアラート
gcloud beta monitoring policies create \
  --policy-from-file=monitoring/cpu-alert-policy.json

# エラーログアラート
gcloud beta monitoring policies create \
  --policy-from-file=monitoring/error-alert-policy.json
```

## 10. 定期的なバックアップ設定

Cloud SQLの自動バックアップを設定します：

```bash
gcloud sql instances patch youtube-content-processor-db \
  --backup-start-time=23:00 \
  --enable-bin-log \
  --retained-backups-count=7
```

## 11. IAMロールの設定

必要なIAMロールを設定します：

```bash
# サービスアカウントの作成
gcloud iam service-accounts create youtube-processor-sa \
  --display-name="YouTube Content Processor Service Account"

# 必要なロールの付与
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:youtube-processor-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:youtube-processor-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"
```
