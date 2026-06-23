import os
import json
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import pandas as pd
import gspread

app = FastAPI(title="雲端智慧電台")

# 允許跨網域存取
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 核心修改：讀取 Render 環境變數中的 Google 憑證 ---
def get_gspread_client():
    # 我們等一下會在 Render 設定一個叫 GOOGLE_CREDENTIALS 的環境變數
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise ValueError("找不到 GOOGLE_CREDENTIALS 環境變數，請在 Render 後台設定！")
    
    creds_dict = json.loads(creds_json)
    gc = gspread.service_account_from_dict(creds_dict)
    return gc

# 取得指定工作表資料的共用函式
def get_sheet_data():
    gc = get_gspread_client()
    # 填入你原本 Google Sheet 的名稱（例如 "music_db" 之類的）
    # 如果你的 Sheet 網址有固定，也可以用 gc.open_by_key("你的Sheet金鑰")
    sh = gc.open("你的GoogleSheet名稱") 
    worksheet = sh.worksheet("playlists")
    return worksheet

# --- API 1: 取得 admin 的歌單 ---
@app.get("/api/playlist")
def get_playlist():
    try:
        worksheet = get_sheet_data()
        records = worksheet.get_all_records()
        df = pd.DataFrame(records)
        if df.empty:
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
        df_all = pd.DataFrame(records)
        
        # 篩選出非 admin 的資料
        if not df_all.empty and 'username' in df_all.columns:
            df_others = df_all[df_all['username'] != 'admin']
        else:
            df_others = pd.DataFrame(columns=['username', 'title', 'url'])
            
        # 建立 admin 的新資料
        new_data = pd.DataFrame(playlist)
        if not new_data.empty:
            new_data['username'] = 'admin'
            df_final = pd.concat([df_others, new_data], ignore_index=True)
        else:
            df_final = df_others
            
        # 清空工作表並重新寫入（含標題列）
        worksheet.clear()
        worksheet.update([df_final.columns.values.tolist()] + df_final.values.tolist())
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}

# --- API 3: 搜尋歌曲與解析串流 ---
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

# --- 讓根網址直接顯示前端網頁 ---
@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()
