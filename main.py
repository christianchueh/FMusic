import os
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import yt_dlp

app = FastAPI()

# ======================
# 🌐 CORS（前端必須）
# ======================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# 📄 首頁（重點）
# ======================
@app.get("/")
def home():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


# ======================
# 🔍 搜尋（穩定版）
# ======================
@app.get("/api/search")
def search(q: str = Query(...)):
    try:
        results = []

        # YouTube
        with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True}) as ydl:
            yt = ydl.extract_info(f"ytsearch10:{q}", download=False)

            for e in yt.get("entries") or []:
                if e:
                    results.append({
                        "title": "🎬 " + e.get("title", ""),
                        "url": e.get("url")
                    })

        # 清理
        results = [r for r in results if r.get("url")]

        return results or [{"title": "❌ 無結果", "url": None}]

    except Exception as e:
        return {"error": str(e)}


# ======================
# 🎧 stream 轉換
# ======================
@app.get("/api/stream")
def stream(url: str = Query(...)):
    try:
        with yt_dlp.YoutubeDL({"format": "bestaudio", "quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return {"stream_url": info["url"]}
    except Exception as e:
        return {"error": str(e)}
