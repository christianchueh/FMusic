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

# --- 💥 修正：真正標準的 gspread 連線機制 ---
def get_sheet_data():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise ValueError("系統找不到 GOOGLE_CREDENTIALS 環境變數，請檢查 Render 設定。")
    
    # 解析 Render 後台的 JSON 憑證
    creds_dict = json.loads(creds_json)
    
    # 這是 gspread 的標準授權方式，完全繞過 Streamlit 機制
    gc = gspread.service_account_from_dict(creds_dict)
    
    # 💥 請務必確認這裡的名字跟你的 Google 試算表名稱一模一樣！
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
        
        df = pd.DataFrame(records)
        # 強制轉小寫並去除空白
        df.columns = [str(c).lower().strip() for c in df.columns]
        
        if 'username' not in df.columns:
            return []
            
        return df[df['username'] == 'admin'].to_dict('records')
    except Exception as e:
        return {"error": f"資料庫連線失敗: {str(e)}"}

# --- API 2: 同步歌單 ---
@app.post("/api/playlist/sync")
def sync_playlist(playlist: list):
    try:
        worksheet = get_sheet_data()
        try:
            records = worksheet.get_all_records()
            if records:
                df_all = pd.DataFrame(records)
                df_all.columns = [str(c).lower().strip() for c in df_all.columns]
                df_others = df_all[df_all['username'] != 'admin']
            else:
                df_others = pd.DataFrame(columns=['username', 'title', 'url'])
        except:
            df_others = pd.DataFrame(columns=['username', 'title', 'url'])
            
        new_data = pd.DataFrame(playlist)
        if not new_data.empty:
            new_data.columns = [str(c).lower().strip() for c in new_data.columns]
            new_data['username'] = 'admin'
            new_data = new_data[['username', 'title', 'url']]
            df_final = pd.concat([df_others, new_data], ignore_index=True)
        else:
            df_final = df_others[['username', 'title', 'url']] if 'username' in df_others.columns else pd.DataFrame(columns=['username', 'title', 'url'])
            
        worksheet.clear()
        # gspread 寫入全量資料的標準語法
        worksheet.update([['username', 'title', 'url']] + df_final[['username', 'title', 'url']].values.tolist())
        return {"status": "success"}
    except Exception as e:
        return {"error": f"同步失敗: {str(e)}"}

# --- API 3: 搜尋與串流 ---
@app.get("/api/search")
def search_songs(q: str = Query(...)):
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
            res = ydl.extract_info(f"scsearch20:{q}", download=False)
            return res.get('entries', [])
    except Exception as e:
        return {"error": f"搜尋失敗: {str(e)}"}

@app.get("/api/stream")
def get_stream_url(url: str = Query(...)):
    try:
        with yt_dlp.YoutubeDL({'format': 'bestaudio', 'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return {"stream_url": info['url']}
    except Exception as e:
        return {"error": f"音訊解析失敗: {str(e)}"}

@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()
