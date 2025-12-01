# utils/db_manager.py (V2 - Thread Safe)
import sqlite3
import pandas as pd
import os
from config.settings import Config
import colorama
from colorama import Fore

colorama.init(autoreset=True)

class DBManager:
    def __init__(self, db_name="market_data.db"):
        # 不再儲存 self.conn，只儲存路徑
        self.db_path = os.path.join(Config.DATA_DIR, db_name)
        self._init_db()

    def _get_conn(self):
        """
        每次都返回一個新的資料庫連線。
        check_same_thread=False 避免在多線程環境下，即便我們開啟新連線，底層仍被卡住。
        """
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self):
        """初始化資料庫表結構，使用 context manager 確保連線關閉"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS daily_metrics (
                        date TEXT,
                        stock_id TEXT,
                        Close REAL,
                        Volume INTEGER,
                        Foreign_BuySell REAL,
                        Trust_BuySell REAL,
                        PRIMARY KEY (date, stock_id)
                    )
                ''')
                conn.commit()
        except Exception as e:
            print(f"{Fore.RED} [DB ERROR] 初始化失敗: {e}")

    def save_data(self, df, stock_id):
        """將 Dataframe 存入 SQL，每次都開啟新連線"""
        if df.empty: return
        
        save_df = df[['date', 'Close', 'Volume', 'Foreign_BuySell', 'Trust_BuySell']].copy()
        save_df['stock_id'] = stock_id
        save_df['date'] = save_df['date'].dt.strftime('%Y-%m-%d')
        
        try:
            with self._get_conn() as conn: # 關鍵：新連線
                # 使用 replace 模式，如果有重複日期就覆蓋
                save_df.to_sql('daily_metrics', conn, if_exists='append', index=False, method='multi')
                # print(f"{Fore.GREEN}[DB] 成功儲存 {len(save_df)} 筆數據至資料庫") # 避免 log 過長
        except sqlite3.IntegrityError:
            # 數據已存在，跳過
            pass
        except Exception as e:
             print(f"{Fore.RED}[DB ERROR] 寫入數據失敗: {e}")

    def load_data(self, stock_id, start_date):
        """從 SQL 讀取數據，每次都開啟新連線"""
        try:
            with self._get_conn() as conn: # 關鍵：新連線
                query = f"""
                    SELECT * FROM daily_metrics 
                    WHERE stock_id = '{stock_id}' AND date >= '{start_date}'
                    ORDER BY date ASC
                """
                df = pd.read_sql(query, conn)
                if not df.empty:
                    df['date'] = pd.to_datetime(df['date'])
                return df
        except Exception as e:
            print(f"{Fore.RED}[DB ERROR] 讀取數據失敗: {e}")
            return pd.DataFrame()