"""
売上ダッシュボード用のローカルサーバー(FastAPI版)。

このフォルダ内のCSVファイルを一覧・提供し、売上ダッシュボード.html から
fetch でCSVデータを読み込めるようにする。
加えて /api/chat で OpenAI に問い合わせるAIチャットのバックエンドを提供する。

APIキーは .env の OPENAI_API_KEY にのみ置く(フロントエンドには一切渡さない)。

使い方:
    pip install -r requirements.txt
    .env を作成し OPENAI_API_KEY=sk-... を設定
    python server.py [ポート番号]

起動後、ブラウザで http://localhost:8000/売上ダッシュボード.html を開く。
"""

import sys
from pathlib import Path
from typing import List, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.responses import PlainTextResponse

import os

DIRECTORY = Path(__file__).resolve().parent
DEFAULT_PORT = 8000

load_dotenv(DIRECTORY / ".env")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = (
    "あなたは売上ダッシュボードの利用者をサポートするアシスタントです。"
    "簡潔で分かりやすい日本語で回答してください。"
)

app = FastAPI()


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


class ChatResponse(BaseModel):
    reply: str


@app.get("/api/csvs")
def list_csvs() -> List[str]:
    return sorted(p.name for p in DIRECTORY.glob("*.csv"))


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="サーバーにOPENAI_API_KEYが設定されていません。.envを確認してください。",
        )
    if not req.messages:
        raise HTTPException(status_code=400, detail="messagesが空です。")

    # openai ライブラリは環境変数OPENAI_API_KEYを読むため、ここでは遅延importして
    # サーバー起動時にキー未設定でも落ちないようにする。
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    api_messages += [{"role": m.role, "content": m.content} for m in req.messages]

    try:
        completion = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=api_messages,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI APIへの問い合わせに失敗しました: {e}")

    reply = completion.choices[0].message.content or ""
    return ChatResponse(reply=reply)


@app.middleware("http")
async def block_dotfiles(request, call_next):
    # .env や .git など、ドット始まりのパスは静的配信から除外する(APIキー漏洩防止)。
    segments = request.url.path.split("/")
    if any(seg.startswith(".") and seg not in ("", ".") for seg in segments):
        return PlainTextResponse("Not Found", status_code=404)
    return await call_next(request)


# API/ミドルウェア定義の後に置くことで、/api/* を優先させてから
# それ以外のパスを静的ファイルとして配信する。
app.mount("/", StaticFiles(directory=str(DIRECTORY)), name="static")


def main():
    import uvicorn

    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    if not OPENAI_API_KEY:
        print("警告: OPENAI_API_KEYが設定されていません。AIチャットは利用できません。")
        print("     .env ファイルに OPENAI_API_KEY=sk-... を設定してください。")
    print(f"サーバー起動: http://127.0.0.1:{port}/売上ダッシュボード.html")
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
