import pandas as pd
from datetime import date, timedelta
from FinMind.data import DataLoader as FinMindDataLoader
from config.settings import Config
import colorama
from colorama import Fore

colorama.init(autoreset=True)

class ChipAgent:
    def __init__(self):
        self.api = FinMindDataLoader()
        self.api.login(user_id=Config.FINMIND_USER, password=Config.FINMIND_PASS)

    def analyze(self, df):
        # df 已經包含了基本的 Foreign_BuySell (來自 data_loader)
        # 但我們需要額外去抓「融資融券」數據，因為 data_loader 預設沒抓這個
        
        print(f"{Fore.CYAN}[Chip Agent] 正在進行深度籌碼透視 (法人 vs 散戶)...")
        
        stock_id = str(df['stock_id'].iloc[-1])
        today_str = date.today().strftime('%Y-%m-%d')
        start_date = (date.today() - timedelta(days=10)).strftime('%Y-%m-%d')
        
        # 1. 抓取融資融券 (Margin)
        df_margin = self.api.taiwan_stock_margin_purchase_short_sale(
            stock_id=stock_id, start_date=start_date, end_date=today_str
        )
        
        # 2. 基礎法人數據 (來自輸入的 df)
        recent = df.tail(5)
        foreign_sum = recent['Foreign_BuySell'].sum()
        trust_sum = recent['Trust_BuySell'].sum()
        
        score = 0
        status = []
        
        # --- 法人邏輯 ---
        if foreign_sum > 5000: 
            score += 1; status.append("外資買")
        elif foreign_sum < -5000: 
            score -= 1; status.append("外資賣")
            
        if trust_sum > 1000: 
            score += 1; status.append("投信買")
        elif trust_sum < -1000: 
            score -= 1; status.append("投信賣")
            
        # --- 散戶邏輯 (關鍵升級) ---
        if not df_margin.empty:
            # 融資餘額變化 (最近 1 天)
            last_margin = df_margin.iloc[-1]
            prev_margin = df_margin.iloc[-2] if len(df_margin) > 1 else last_margin
            
            margin_diff = last_margin['MarginPurchaseTodayBalance'] - prev_margin['MarginPurchaseTodayBalance']
            
            # 散戶指標：融資大增 (散戶進場)
            if margin_diff > 1000: 
                # 如果股價跌還融資增 -> 散戶接刀 -> 扣分
                if df['Close'].iloc[-1] < df['Close'].iloc[-2]:
                    score -= 1.5 
                    status.append(f"散戶接刀(資增{int(margin_diff)}張)")
                else:
                    # 股價漲融資增 -> 人氣旺 -> 不扣分或微加
                    status.append("融資增")
            
            # 融資大減 (散戶停損/獲利了結)
            elif margin_diff < -1000:
                if df['Close'].iloc[-1] > df['Close'].iloc[-2]:
                    score += 1 
                    status.append("籌碼安定(資減)")
                else:
                    status.append("多殺多")

        # 綜合判斷
        msg = f"籌碼結構: {' '.join(status)}"
        return score, msg