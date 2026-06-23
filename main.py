import os
import json
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import gspread

app = FastAPI(title="雲端智慧綜合電台")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =======================================================
# 🔒 100% 純淨的 gspread 初始化機制（絕無內鬼）
# =======================================================
def get_sheet_data():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise ValueError("系統找不到 GOOGLE_CREDENTIALS 環境變數。")
    
    creds_dict = json.loads(creds_json)
    gc = gspread.service_account_from_dict(creds_dict)
    
    # 💥 請務必確認這裡的名字跟你 Google 試算表名稱一模一樣！
    sh = gc.open("你的GoogleSheet名稱") 
    worksheet = sh.worksheet("playlists")
    return worksheet

# --- API 1: 取得歌單 ---
@app.get("/api/playlist")
def get_playlist():
    try:
        worksheet = get_sheet_data()
        records = worksheet.get_all_records()
        if not records:
            return []
        
        # 用標準 Python 處理欄位名稱防呆，完全不靠 Pandas
        cleaned_records = []
        for r in records:
            clean_row = {str(k).lower().strip(): v for k, v in r.items()}
            if clean_row.get('username') == 'admin':
                cleaned_records.append({
                    "username": "admin",
                    "title": clean_row.get("title", "無題"),
                    "url": clean_row.get("url", "")
                })
        return cleaned_records
    except Exception as e:
        return {"error": f"資料庫連線失敗: {str(e)}"}

# --- API 2: 同步歌單 ---
@app.post("/api/playlist/sync")
def sync_playlist(playlist: list):
    try:
        worksheet = get_sheet_data()
        records = worksheet.get_all_records()
        
        # 篩選出非 admin 的留下來
        final_rows = []
        if records:
            for r in records:
                clean_row = {str(k).lower().strip(): v for k, v in r.items()}
                if clean_row.get('username') != 'admin' and clean_row.get('username') != '':
                    final_rows.append([
                        clean_row.get('username'),
                        clean_row.get('title', '無題'),
                        clean_row.get('url', '')
                    ])
                    
        # 把新編輯的 admin 歌單加進去
        for song in playlist:
            final_rows.append([
                "admin",
                song.get("title", "無題"),
                song.get("url", "")
            ])
            
        worksheet.clear()
        # 直接更新：標題列 + 所有的資料列
        worksheet.update([['username', 'title', 'url']] + final_rows)
        return {"status": "success"}
    except Exception as e:
        return {"error": f"同步失敗: {str(e)}"}

# --- API 3: 搜尋歌曲 (完全移除 Streamlit 殘留) ---
@app.get("/api/search")
def search_songs(q: str = Query(...)):
    try:
        # 用純 yt_dlp 進行搜尋，不夾帶任何特定的連線快取
        with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True, 'playlistend': 20}) as ydl:
            res = ydl.extract_info(f"ytsearch20:{q}", download=False)
            entries = res.get('entries', [])
            
            # 標準化回傳格式，確保前端拿到乾淨的 title 與 url
            results = []
            for item in entries:
                if item.get('url') or item.get('id'):
                    url = item.get('url') if item.get('url') else f"https://www.youtube.com/watch?v={item.get('id')}"
                    results.append({
                        "title": item.get("title", "未知歌曲"),
                        "url": url
                    })
            return results
    except Exception as e:
        return {"error": f"搜尋失敗: {str(e)}"}

@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()
