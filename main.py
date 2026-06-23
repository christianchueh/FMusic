from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# 🔍 搜尋（只回 ID，不回 stream）
# =========================
@app.get("/api/search")
def search(q: str = Query(...)):
    try:
        results = []

        with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True}) as ydl:
            data = ydl.extract_info(f"ytsearch10:{q}", download=False)

            for e in data.get("entries") or []:
                if not e:
                    continue

                # YouTube video id
                vid = e.get("id")

                if vid:
                    results.append({
                        "title": "🎬 " + e.get("title", ""),
                        "source": "youtube",
                        "id": vid
                    })

        return results

    except Exception as e:
        return {"error": str(e)}
