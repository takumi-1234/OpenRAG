# OpenRAG 🚀

**OpenRAG**は、独自のドキュメントに基づいた対話型AI環境を、ローカルで、かつ無料で構築するためのオープンソースプロジェクトです。

ユーザー認証、ワークスペース管理、ゲストモードなどの機能を備えており、個人利用からチームでのナレッジベース共有まで、幅広い用途に対応可能です。

## 主な機能 (Features)

- **ユーザー認証**: 安全なJWTベースのユーザー登録・ログイン機能。
- **ワークスペース管理**: プロジェクトや目的に応じてドキュメントを分離・管理。
- **ドキュメントアップロード**: PDF, DOCX, TXT形式のファイルをアップロードし、AIの知識源として活用。
- **RAGチャット**: アップロードしたドキュメントの内容に基づき、AIが根拠を示しながら質問に回答。
- **ゲストモード**: ログイン不要で、手軽にアプリケーションのコア機能を試せる一時利用モード。
- **マイクロサービスアーキテクチャ**: GoとPythonの得意分野を活かした、スケーラブルでメンテナンス性の高い設計。

## アーキテクチャ (Architecture)

```mermaid
graph TD
    subgraph "ユーザー"
        User[<fa:fa-user> ユーザー]
    end

    subgraph "フロントエンド (Docker)"
        Frontend[<fa:fa-window-maximize> Streamlit UI <br> localhost:8501]
    end

    subgraph "バックエンド (Docker)"
        ApiGo[<fa:fa-server> Go API (Gin) <br> 認証・ワークスペース管理 <br> localhost:8000]
        RagPython[<fa:fa-brain> Python RAG API (FastAPI) <br> RAG処理・LLM連携 <br> localhost:8001]
    end

    subgraph "データストア (Docker)"
        MySQL[<fa:fa-database> MySQL <br> ユーザー・ワークスペース情報]
        ChromaDB[<fa:fa-vector-square> ChromaDB <br> ベクトルデータ]
    end

    subgraph "外部サービス"
        Gemini[<fa:fa-robot> Google Gemini API]
    end

    User -- HTTPS --> Frontend
    Frontend -- APIリクエスト --> ApiGo
    Frontend -- APIリクエスト --> RagPython
    ApiGo -- CRUD --> MySQL
    RagPython -- ベクトル化・検索 --> ChromaDB
    RagPython -- 応答生成 --> Gemini
```

- **`frontend-streamlit` (Port 8501)**: ユーザーインターフェース。
- **`api-go` (Port 8000)**: 認証、ユーザー・講義・チャット履歴管理を担当する高速APIサーバー。
- **`rag-python` (Port 8001)**: ドキュメント処理、Embedding、LLM連携など、計算集約的なAI処理を担当。
- **`db` (Port 3306)**: MySQLデータベース。ユーザー情報や講義設定などを保存。

## 🛠️ 技術スタック

- **フロントエンド**: Streamlit
- **バックエンド**:
  - **API Gateway/認証**: Go, Gin
  - **RAGコア**: Python, FastAPI, LangChain, Sentence Transformers
- **データベース**: MySQL, ChromaDB
- **LLM**: Google Gemini
- **コンテナ化**: Docker, Docker Compose

## 🚀 セットアップと起動

### 前提条件

- Docker
- Docker Compose
- Google Gemini API キー

### 手順

1.  **リポジトリのクローン:**
    ```bash
    git clone <repository_url>
    cd OpenRAG
    ```

2.  **環境変数の設定:**
    - `.env` ファイルをプロジェクトルートに作成します（リポジトリには含まれていません）。
    - 以下の内容を参考に、ご自身の環境に合わせて値を設定してください。特に `GEMINI_API_KEY` は必須です。
      ```env
      # .env
      MYSQL_DATABASE=open_rag_db
      MYSQL_USER=rag_user
      MYSQL_PASSWORD=rag_password
      MYSQL_ROOT_PASSWORD=rag_root_password
      DB_SOURCE=rag_user:rag_password@tcp(db:3306)/open_rag_db?parseTime=true
      SERVER_ADDRESS=0.0.0.0:8000
      JWT_SECRET_KEY=your-super-secret-jwt-key
      GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
      API_GO_URL=http://api-go:8000
      API_PYTHON_RAG_URL=http://rag-python:8001
      ```

3.  **データディレクトリの作成:**
    - データを永続化するためのディレクトリをホスト側に作成します。
    ```bash
    mkdir -p data/mysql data/chroma .cache/huggingface
    ```

4.  **Dockerイメージのビルド:**
    ```bash
    docker compose build
    ```

5.  **Dockerコンテナの起動:**
    ```bash
    docker compose up -d
    ```
    - `-d` オプションでバックグラウンドで起動します。ログを確認する場合は `docker compose logs -f` を実行します。

### アクセス

- **Streamlit UI**: `http://localhost:8501`
- **Go API (Swagger等なし)**: `http://localhost:8000`
- **Python RAG API (Docs)**: `http://localhost:8001/docs`

## 停止

```bash
docker compose down
```
- コンテナを停止し、ネットワークを削除します。
- ボリューム（`data/` 内のデータ）は削除されません。データを完全に削除したい場合は `docker compose down -v` を使用してください。