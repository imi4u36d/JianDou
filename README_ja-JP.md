<p align="center">
  <a href="README.md">English</a> | <a href="README_zh-CN.md">简体中文</a> | <strong>日本語</strong>
</p>

<p align="center">
  <img src="static/web/brand/logo.png" alt="JianDou Logo" width="120" />
</p>

<h1 align="center">JianDou（煎豆）</h1>

<p align="center">
  オープンソースのテキストからビデオへの変換ワークステーション。設定可能なマルチモデルパイプラインを搭載。
</p>

<p align="center">
  <a href="https://github.com/imi4u36d/JianDou/blob/main/License"><img src="https://img.shields.io/badge/license-Apache--2.0-blue.svg" alt="License" /></a>
  <a href="https://github.com/imi4u36d/JianDou/releases"><img src="https://img.shields.io/badge/release-0.1.0-orange.svg" alt="Release" /></a>
  <a href="https://github.com/imi4u36d/JianDou"><img src="https://img.shields.io/badge/python-3.12%2B-green.svg" alt="Python" /></a>
  <a href="https://github.com/imi4u36d/JianDou"><img src="https://img.shields.io/badge/node-20%2B-brightgreen.svg" alt="Node" /></a>
</p>

---

小説の章をアップロード、テキストを貼り付け、またはプロンプトを入力 — JianDou は設定可能なAIモデルチェーン（テキスト、ビジュアル、キーフレーム、ビデオ）を通じてテキストをビデオに変換します。各ステージはプロバイダーとモデルバージョンを個別に選択でき、生成パイプラインを完全に制御できます。

## 主な機能

**柔軟な入力**
- `.txt`ファイルのアップロードまたはテキストの直接貼り付け — コンテンツはプロンプト生成のために自動抽出されます。
- カスタムプロンプトで完全なクリエイティブコントロール。
- 参照画像を最初または最後のキーフレームとして添付可能。

**マルチモデルパイプライン**
- 4つの独立して設定可能なステージ：テキストモデル（スクリプト/絵コンテ）→ ビジュアルモデル（参照画像理解）→ キーフレームモデル（最初/最後のフレーム生成）→ ビデオモデル（ビデオ合成）。
- プロバイダーの自由な組み合わせ：Alibaba Cloud（Qwen/Wanxiang）、Volcengine（Doubao/Seedream/Seedance）、および OpenAI 互換エンドポイント。
- 出力パラメータ（アスペクト比、解像度、尺、生成数、Seed）は選択したモデルの機能に基づいて自動フィルタリングされ、無効な設定を防止します。

**タスク管理**
- ステージレベルのステータス、経過時間、ビデオプレビューを含むリアルタイム進捗追跡。
- 完全なタスクライフサイクル：作成、フィルタ、詳細表示、リトライ、一時停止、再開、中止、削除、評価。
- Seed管理：高評価のSeedを自動収集し、ワンクリックでバックフィルして安定した結果を得られます。

**管理コンソール**
- ユーザー向けフロントエンドから分離された専用管理ポータル。
- ロールベースのアクセス制御（管理者/ユーザー）、招待コード登録対応。
- コンテンツ制作チームと運用管理向けに設計。

**セキュリティとデプロイメント**
- 認証エンドポイントのレート制限、オリジン検証、API キーの暗号化ストレージ。
- 自動データベースマイグレーションとヘルスチェックを備えた Docker ファーストのデプロイメント。
- 環境変数とYAMLファイルによる包括的な設定。

## アーキテクチャ

```
テキスト入力 --> テキストモデル（スクリプト/絵コンテ生成）
                  --> ビジュアルモデル（参照画像理解）
                          --> キーフレームモデル（最初/最後のフレーム生成）
                                  --> ビデオモデル（ビデオ合成）
                                          --> プレビュー / ダウンロード / 評価
```

各パイプラインステージは、独自のプロバイダーとモデルバージョンで独立して設定可能です。

## クイックスタート

### 前提条件

- **Python** 3.12+
- **Node.js** 20+
- **npm**（Node.jsに同梱）
- **[uv](https://docs.astral.sh/uv/)**（Pythonパッケージマネージャー）

### 方法1：Docker（推奨）

```bash
# 1. 環境の準備
cp .env.docker.example .env.docker

# 2. ビルドして実行
docker build -t jiandou .
docker run -d -p 8100:8000 \
  --env-file .env.docker \
  -v ./config:/app/config \
  -v ./data:/app/data \
  -v ./storage:/app/storage \
  jiandou
```

イメージはコンテナ内でポート `8000` をリッスンし、起動時にデータベースマイグレーションを実行します。自動マイグレーションをスキップするには `JIANDOU_AUTO_MIGRATE=false` を設定してください。

### 方法2：ローカル開発

```bash
# 1. 環境設定
cp .env.dev.example .env
cp config/model/providers.secrets.example.yml config/model/providers.secrets.yml
# providers.secrets.yml に API キーを入力

# 2. 依存関係のインストール
npm install
uv sync

# 3. データベースマイグレーションの適用
uv run jiandou db migrate

# 4. サーバーの起動
npm run serve
```

起動後のアクセス先：
- **ユーザーフロントエンド**：`http://127.0.0.1:8100`
- **管理ポータル**：`http://127.0.0.1:8100/admin`

### ヘルスチェック

- **生存確認**：`GET /api/v3/health`
- **準備確認**：`GET /api/v3/ready`（データベースとストレージの可用性を検証）

## モデル設定

モデル設定は `config/model/` ディレクトリにあります：

```
config/model/
├── models.yml                    # 利用可能なモデル定義
├── providers/                    # プロバイダー基本設定（base_url など）
│   ├── volcengine.yml
│   ├── deepseek.yml
│   └── openai.yml
├── providers.secrets.example.yml # API キーテンプレート（コミット済み）
└── providers.secrets.yml         # あなたの API キー（ローカル、コミットしない）
```

対応プロバイダー：
- **Alibaba Cloud** — Qwen（通義千問）、Wanxiang（万相）
- **Volcengine** — Doubao（豆包）、Seedream、Seedance
- **OpenAI 互換** — OpenAI 互換の任意の API エンドポイント

## 設定

すべてのランタイム設定は環境変数で制御されます。完全なリファレンスは [docs/configuration.md](docs/configuration.md) を参照してください。

主要変数：

| 変数 | 説明 | デフォルト |
|---|---|---|
| `JIANDOU_SERVER_PORT` | バックエンドのリッスンポート | `8100` |
| `JIANDOU_DATABASE_URL` | データベース接続文字列 | `sqlite+aiosqlite:///./data/jiandou.db` |
| `JIANDOU_SECRET_KEY` | JWT 署名キー | （必須設定） |
| `JIANDOU_WEB_ORIGIN` | フロントエンドオリジン（CORS） | `http://127.0.0.1:8100` |
| `JIANDOU_TRUSTED_ORIGINS` | 追加の信頼オリジン（カンマ区切り） | — |
| `JIANDOU_COOKIE_SECURE` | セキュア Cookie + HSTS を有効化 | `false` |
| `JIANDOU_WORKER_CONCURRENCY` | 非同期ワーカースレッド数 | `2` |
| `JIANDOU_DEFAULT_ASPECT_RATIO` | デフォルトのビデオアスペクト比 | `16:9` |
| `JIANDOU_DEFAULT_DURATION_SECONDS` | デフォルトのビデオ尺 | `8` |

認証エンドポイントにはレート制限が組み込まれています。`JIANDOU_AUTH_LOGIN_RATE_LIMIT`、`JIANDOU_AUTH_INVITE_ACTIVATION_RATE_LIMIT`、`JIANDOU_AUTH_RATE_LIMIT_WINDOW_SECONDS` で調整可能です。

## 開発

### フロントエンド

フロントエンドは **Vue 3 + TypeScript + Element Plus + Tailwind CSS** で構築され、Vite を開発サーバーとして使用し、API プロキシを自動で行います。

```bash
# フロントエンド環境変数テンプレートのコピー
cp frontends/web/.env.example frontends/web/.env

# 開発サーバー（デフォルト http://localhost:5173）
npm run web:dev

# 型チェック
npm run web:typecheck

# リントとフォーマット
npm run web:lint
npm run web:format

# ユニットテスト
npm run web:test

# テストカバレッジ
npx vitest run --coverage
```

詳細なアーキテクチャは [docs/frontend-architecture.md](docs/frontend-architecture.md) を参照してください。

### バックエンド

バックエンドは **FastAPI + SQLAlchemy + Alembic** で構築され、aiosqlite 経由で SQLite を使用します。

```bash
# リント（ruff、ゼロエラーが期待）
uv run ruff check backend/

# 全テスト実行（314テスト、ゼロ失敗が期待）
uv run pytest

# カテゴリ別テスト実行
uv run pytest -m unit      # 高速ユニットテスト（64）
uv run pytest -m api       # API エンドポイントテスト（90）
uv run pytest -m domain    # ドメイン層テスト（33）
uv run pytest -m "not slow" # 遅いテストをスキップ

# OpenAPI スキーマのエクスポート
uv run jiandou openapi --output docs/openapi.json

# API のみ開発サーバー
npm run api:dev
```

モジュール構成は [docs/backend-architecture.md](docs/backend-architecture.md)、データベース設計は [docs/database-design.md](docs/database-design.md) を参照してください。

### 検証

```bash
# フルテストスイート（バックエンドリント + テスト + フロントエンド型チェック）
npm test

# 新規一時データベースでのマイグレーション検証
TMP_DB=$(mktemp -t jiandou.XXXXXX.db) && \
  JIANDOU_DATABASE_URL="sqlite+aiosqlite:///$TMP_DB" uv run alembic upgrade head && \
  rm -f "$TMP_DB"

# パッケージ型チェック
npm run packages:typecheck
npm run web:typecheck

# リリース前プレフライト（生成物のクリーンアップ）
npm run release:check
```

## ドキュメント

| ドキュメント | 説明 |
|---|---|
| [設定リファレンス](docs/configuration.md) | 環境変数の完全リファレンス |
| [バックエンドアーキテクチャ](docs/backend-architecture.md) | モジュール構成と変更境界 |
| [フロントエンドアーキテクチャ](docs/frontend-architecture.md) | Monorepo構成とコンポーネント規約 |
| [データベース設計](docs/database-design.md) | スキーマ制約とマイグレーションルール |
| [リリースプロセス](docs/release-process.md) | バージョニングとリリースワークフロー |
| [API リファレンス](docs/openapi.json) | OpenAPI 3.1 仕様（自動生成） |

## コミュニティとサポート

- **QQ グループ**：`1090387362`
- [バグ報告 / 機能リクエスト](https://github.com/imi4u36d/JianDou/issues)
- セキュリティ問題については [SECURITY.md](SECURITY.md) を参照
- 使用方法の質問と貢献ガイドラインは [SUPPORT.md](SUPPORT.md) と [CONTRIBUTING.md](CONTRIBUTING.md) を参照

## スター履歴

<a href="https://www.star-history.com/?repos=imi4u36d%2FJianDou&type=date&legend=top-left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=imi4u36d/JianDou&type=date&theme=dark&legend=top-left" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=imi4u36d/JianDou&type=date&legend=top-left" />
    <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=imi4u36d/JianDou&type=date&legend=top-left" />
  </picture>
</a>

## ライセンス

本プロジェクトは [Apache License 2.0](./License) の下でライセンスされています。
