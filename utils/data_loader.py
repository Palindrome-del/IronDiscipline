# utils/data_loader.py (V9 - Silent & Robust Edition)
import pandas as pd
import requests
import yfinance as yf
from datetime import date, datetime, timedelta
from FinMind.data import DataLoader as FinMindDataLoader
from config.settings import Config
from utils.db_manager import DBManager
import colorama
from colorama import Fore
import re
from bs4 import BeautifulSoup

# --- 靜音 yfinance 的內部錯誤 ---
import logging
logging.getLogger('yfinance').setLevel(logging.CRITICAL)
# -----------------------------

colorama.init(autoreset=True)

class DataLoader:
    def __init__(self):
        self.api = FinMindDataLoader()
        
        user = Config.FINMIND_USER
        pwd = Config.FINMIND_PASS
        
        if user: user = str(user).strip()
        if pwd: pwd = str(pwd).strip()
        
        if user and pwd:
            try:
                self.api.login(user_id=user, password=pwd)
            except Exception as e:
                print(f"{Fore.RED}[DataLoader] FinMind 登入失敗: {e}")
        
        self.db = DBManager()
    
    def _get_realtime_price(self, stock_id):
        # ... (保持 V8 的 BeautifulSoup 爬蟲邏輯不變) ...
        try:
            exchanges = ['TWO', 'TW']
            for exchange in exchanges:
                url = f"https://tw.stock.yahoo.com/quote/{stock_id}.{exchange}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                res = requests.get(url, headers=headers, timeout=3)
                if res.status_code != 200: continue
                
                soup = BeautifulSoup(res.text, 'html.parser')
                meta = soup.find("meta", property="og:description")
                
                if meta:
                    content = meta.get("content", "")
                    if "查無" in content: continue
                    match = re.search(r'成交價\s*([\d,]+\.?\d*)', content)
                    if match:
                        price = float(match.group(1).replace(',', ''))
                        if price > 0: return price
        except: pass

        # yfinance 備援 (靜音版)
        try:
            for suffix in ['.TW', '.TWO']:
                ticker = yf.Ticker(f"{stock_id}{suffix}")
                try:
                    if hasattr(ticker, 'fast_info'):
                        price = ticker.fast_info.last_price
                        if price and price > 0: return price
                except: pass
                
                try:
                    df_rt = ticker.history(period="1d", interval="1m")
                    if not df_rt.empty:
                        price = df_rt['Close'].iloc[-1]
                        if price > 0: return price
                except: pass
        except: pass

        return None

    def _fetch_from_yfinance(self, stock_id):
        # ... (保持 V8 邏輯，但確保不會報錯) ...
        print(f"{Fore.YELLOW}[Data] 啟動備援 (yfinance) {stock_id}...")
        try:
            for suffix in ['.TW', '.TWO']:
                # 這裡的 progress=False 會隱藏進度條，我們再加 logger 設定隱藏錯誤
                df = yf.download(f"{stock_id}{suffix}", start=Config.START_DATE, progress=False)
                if not df.empty:
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    df = df.reset_index()
                    df = df.rename(columns={"Date": "date", "Close": "Close", "Volume": "Volume"})
                    if 'Close' not in df.columns: continue
                    df = df[df['Close'] > 0]
                    df['stock_id'] = stock_id
                    df['Foreign_BuySell'] = 0
                    df['Trust_BuySell'] = 0
                    df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
                    return df[['date', 'stock_id', 'Close', 'Volume', 'Foreign_BuySell', 'Trust_BuySell']]
            return None
        except: return None

    def fetch_data(self, stock_id, force_update=False):
        today_str = date.today().strftime('%Y-%m-%d')
        df = None
        if not force_update: df = self.db.load_data(stock_id, Config.START_DATE)
        
        if df is None or df.empty or force_update:
            try:
                # 這裡可能會因為 FinMind 限流而失敗，失敗就安靜地去用 yfinance
                df_p = self.api.taiwan_stock_daily(stock_id=stock_id, start_date=Config.START_DATE, end_date=today_str)
                if not df_p.empty:
                    df_p['date'] = pd.to_datetime(df_p['date'])
                    df_p = df_p.rename(columns={"close": "Close", "Trading_Volume": "Volume"})
                    df_p = df_p[df_p['Close'] > 0]
                    if not df_p.empty:
                        df_p['Foreign_BuySell'] = 0
                        df_p['Trust_BuySell'] = 0
                        df = df_p
                        self.db.save_data(df, stock_id)
            except: pass 

        if df is None or len(df) < 60:
            df_res = self._fetch_from_yfinance(stock_id)
            if df_res is not None: 
                df = df_res
                self.db.save_data(df, stock_id)

        if df is None or df.empty: return None

        # 4. 注入即時股價 (擴大時段)
        now = datetime.now()
        if 0 <= now.weekday() <= 4 and 8 <= now.hour <= 16:
            real = self._get_realtime_price(stock_id)
            if real and real > 0:
                df.iloc[-1, df.columns.get_loc('Close')] = real
        
        return df