# rag-python/app/main.py

import logging
import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request, Path
from fastapi.responses import JSONResponse
from werkzeug.utils import secure_filename

from app.core.config import settings
from app.rag.chroma_manager import ChromaManager
from app.rag.document_processor import process_documents, SUPPORTED_EXTENSIONS
from app.rag.llm_gemini import GeminiChat
from app.auth.middleware import auth_middleware, AuthClaims

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPIアプリケーションの初期化
app = FastAPI(title="OpenRAG - RAG Service")

# サービスインスタンスの初期化 (シングルトン)
chroma_manager = ChromaManager(persist_directory=settings.CHROMA_DB_PATH, embedding_model_name=settings.EMBEDDING_MODEL_NAME)
gemini_chat = GeminiChat(api_key=settings.GEMINI_API_KEY, model_name=settings.GEMINI_MODEL_NAME)

# ミドルウェアの適用
app.middleware("http")(auth_middleware)

@app.on_event("startup")
async def startup_event():
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info("RAG Service Started")

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/v1/lectures/{lecture_id}/upload", tags=["RAG"])
async def upload_document(
    lecture_id: int = Path(..., title="講義ID", ge=1),
    file: UploadFile = File(..., description="アップロードするファイル"),
    claims: AuthClaims = Depends(lambda request: request.state.claims) # 認証ミドルウェアからClaimsを取得
):
    # ここでclaims.user_idを使って、アップロード権限があるかなどをチェック可能（ロジックはapi-go側にあると仮定）
    logger.info(f"User {claims.user_id} uploading file for lecture {lecture_id}")

    if not file.filename:
        raise HTTPException(status_code=400, detail="ファイル名がありません。")

    safe_filename = secure_filename(file.filename)
    file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)
    file_ext = os.path.splitext(safe_filename)[1].lower()

    if file_ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"サポートされていないファイル形式です: {file_ext}")

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        documents = process_documents(file_path)
        if not documents:
            raise HTTPException(status_code=400, detail="ファイルからテキストを抽出できませんでした。")

        # 講義IDからコレクション名を生成
        collection_name = f"lecture_{lecture_id}"
        chroma_manager.add_documents(documents, collection_name=collection_name)

        return {"filename": safe_filename, "chunks_added": len(documents), "collection_name": collection_name}

    except Exception as e:
        logger.error(f"File upload failed for lecture {lecture_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"ファイル処理中にエラーが発生しました: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        await file.close()

from pydantic import BaseModel
class ChatRequest(BaseModel):
    query: str
    system_prompt: str | None = None

@app.post("/api/v1/lectures/{lecture_id}/chat", tags=["RAG"])
async def chat_with_document(
    request: ChatRequest,
    lecture_id: int = Path(..., title="講義ID", ge=1),
    claims: AuthClaims = Depends(lambda request: request.state.claims)
):
    logger.info(f"User {claims.user_id} chatting with lecture {lecture_id}")
    collection_name = f"lecture_{lecture_id}"

    try:
        # 1. ベクトル検索
        search_results = chroma_manager.search(request.query, collection_name=collection_name, k=3)
        sources = sorted(list(set(doc.metadata.get("source", "不明") for doc in search_results)))

        # 2. LLMによる回答生成
        response_text = gemini_chat.generate_response(
            query=request.query,
            context_docs=search_results,
            system_prompt_override=request.system_prompt # カスタムプロンプトを渡す
        )

        return {"response": response_text, "sources": sources}

    except Exception as e:
        logger.error(f"Chat failed for lecture {lecture_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"チャット処理中にエラーが発生しました: {str(e)}")