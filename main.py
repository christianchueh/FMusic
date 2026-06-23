import os
import json
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import pandas as pd
import gspread

app = FastAPI(title="雲端智慧電台")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_sheet_data():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS 找不到")
    creds_dict = json.loads(creds_json)
    gc = gspread.service_account_from_dict(creds_dict)
    
    # 💥 請確保這裡改成你真正的 Google Sheet 試算表名稱！
    sh = gc.open("你的GoogleSheet名稱") 
    worksheet = sh.worksheet("playlists")
    return worksheet

# --- API 1: 取得歌單 (防呆確保必有欄位) ---
@app.get("/api/playlist")
def get_playlist():
    try:
        worksheet = get_sheet_data()
        records = worksheet.get_all_records()
        if not records:
            return []
        df = pd.DataFrame(records)
        # 強制將所有欄位轉小寫，防止欄位名稱對不上的問題
        df.columns = [str(c).lower().strip() for c in df.columns]
        
        if 'username' not in df.columns:
            return []
            
        return df[df['username'] == 'admin'].to_dict('records')
    except Exception as e:
        return {"error": str(e)}

# --- API 2: 同步歌單 ---
@app.post("/api/playlist/sync")
def sync_playlist(playlist: list):
    try:
        worksheet = get_sheet_data()
        records = worksheet.get_all_records()
        
        if records:
            df_all = pd.DataFrame(records)
            df_all.columns = [str(c).lower().strip() for c in df_all.columns]
            df_others = df_all[df_all['username'] != 'admin']
        else:
            df_others = pd.DataFrame(columns=['username', 'title', 'url'])
            
        new_data = pd.DataFrame(playlist)
        if not new_data.empty:
            new_data.columns = [str(c).lower().strip() for c in new_data.columns]
            new_data['username'] = 'admin'
            # 確保欄位順序固定
            new_data = new_data[['username', 'title', 'url']]
            df_final = pd.concat([df_others, new_data], ignore_index=True)
        else:
            df_final = df_others[['username', 'title', 'url']] if 'username' in df_others.columns else pd.DataFrame(columns=['username', 'title', 'url'])
            
        worksheet.clear()
        # 寫入包含標準標題列的資料
        worksheet.update([['username', 'title', 'url']] + df_final[['username', 'title', 'url']].values.tolist())
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}

# --- API 3: 搜尋與串流 ---
@app.get("/api/search")
def search_songs(q: str = Query(...)):
    with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
        res = ydl.extract_info(f"scsearch20:{q}", download=False)
        return res.get('entries', [])

@app.get("/api/stream")
def get_stream_url(url: str = Query(...)):
    with yt_dlp.YoutubeDL({'format': 'bestaudio', 'quiet': True}) as ydl:
        info = ydl.extract_info(url, download=False)
        return {"stream_url": info['url']}

@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()
