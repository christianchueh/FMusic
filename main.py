import os
import json
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp

app = FastAPI(title="雲端電台")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# 📃 playlist (記憶用)
# =========================
playlist = []

# =========================
# 🎧 搜尋（穩定版）
# =========================
@app.get("/api/search")
def search_songs(q: str = Query(...)):
    try:
        results = []

        # -------- YouTube --------
        with yt_dlp.YoutubeDL({
            "quiet": True,
            "extract_flat": True
        }) as ydl:

            yt = ydl.extract_info(f"ytsearch10:{q}", download=False)
            for e in yt.get("entries") or []:
                if not e:
                    continue
                results.append({
                    "title": "🎬 " + e.get("title", ""),
                    "url": e.get("url")
                })

        # -------- SoundCloud --------
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True}) as ydl:
                sc = ydl.extract_info(f"scsearch10:{q}", download=False)

                for e in sc.get("entries") or []:
                    if not e or not e.get("url"):
                        continue
                    results.append({
                        "title": "☁️ " + e.get("title", ""),
                        "url": e.get("url")
                    })
        except:
            pass

        # -------- 清理 --------
        clean = []
        seen = set()

        for r in results:
            if not r.get("url"):
                continue
            if r["url"] in seen:
                continue
            seen.add(r["url"])
            clean.append(r)

        return clean or [{"title": "❌ 沒找到結果", "url": None}]

    except Exception as e:
        return {"error": str(e)}

# =========================
# 🎧 轉 stream URL
# =========================
@app.get("/api/stream")
def stream(url: str = Query(...)):
    try:
        with yt_dlp.YoutubeDL({"format": "bestaudio", "quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return {"stream_url": info["url"]}
    except Exception as e:
        return {"error": str(e)}

# =========================
# 📃 playlist API（記憶）
# =========================
@app.get("/api/playlist")
def get_playlist():
    return playlist


@app.post("/api/playlist/add")
def add_song(song: dict):
    playlist.append(song)
    return {"ok": True}


@app.post("/api/playlist/delete")
def delete_song(index: int):
    if 0 <= index < len(playlist):
        playlist.pop(index)
    return {"ok": True}
