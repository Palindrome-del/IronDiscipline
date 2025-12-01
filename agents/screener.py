# agents/screener.py
import pandas as pd
import numpy as np
from config.settings import Config
from utils.data_loader import DataLoader
from agents.tech_agent import TechAgent
import colorama
from colorama import Fore
import time

colorama.init(autoreset=True)

class MarketScanner:
    def __init__(self, tech_agent=None):
        self.loader = DataLoader()
        self.tech_agent = tech_agent if tech_agent else TechAgent()
        
        # 狼性擴充：包含權值與熱門股
        self.target_stocks = [
            "2330", "2454", "2303", "3711", "3034", "2379", "3443", "3035", "3661",
            "2317", "2382", "2357", "3231", "2356", "2301", "2376", "2377", "2324", "6669", "3529", "3017",
            "2881", "2882", "2891", "2886", "2884", "2892", "5880", "2885", "2880", "2883", "2887", "5876", "2890",
            "2603", "2609", "2615", "2618", "2610",
            "1101", "1102", "1216", "1301", "1303", "1326", "1402", "2002", "2105", "2207", "2912", "9910", 
            "2308", "3008", "3045", "4904", "4938", "2412", "3037", "2345",
            "1513", "1519", "1504", "1605", "0050"
        ]

    def _scan_single_stock(self, stock_id):
        try:
            df = self.loader.fetch_data(stock_id, force_update=True) 
            if df is None: return None
            if len(df) < Config.WINDOW_SIZE: return None
            
            current_price = df['Close'].iloc[-1]
            score, msg, (curr, target, support) = self.tech_agent.analyze(df)
            roi = (target - current_price) / current_price
            
            if abs(roi) > 0.5: return None # 異常數據過濾
            
            # --- 狼性邏輯：多空雙殺 ---
            direction = "NEUTRAL"
            
            # 做多門檻：+1.5%
            if roi > 0.015: 
                direction = "LONG"
                print(f" -> {Fore.GREEN}{stock_id}: 🚀 發現獵物 (做多) 預期漲幅 {roi*100:.2f}%")
            
            # 做空門檻：-1.5% (這是關鍵！)
            elif roi < -0.015:
                direction = "SHORT"
                print(f" -> {Fore.RED}{stock_id}: 📉 發現獵物 (做空/避險) 預期跌幅 {roi*100:.2f}%")
            else:
                # 波動過小，忽略
                return None

            return {
                "stock_id": stock_id,
                "price": current_price,
                "ai_target": target,
                "ai_roi_pct": roi * 100,
                "ai_support": support,
                "score": score,
                "msg": msg,
                "direction": direction
            }

        except Exception as e:
            print(f"{Fore.RED}Error scanning {stock_id}: {e}")
        return None

    def scan(self, strategy="Wolf_Pack"):
        print(f"{Fore.CYAN}[Scanner] 狼群出動 (Wolf Pack Mode) - 掃描 {len(self.target_stocks)} 檔標的...")
        results = []
        for i, stock_id in enumerate(self.target_stocks):
            res = self._scan_single_stock(stock_id)
            if res: results.append(res)
            # 稍微加速，只休 0.1s
            if i % 10 == 0: time.sleep(0.1) 
        
        if results:
            res_df = pd.DataFrame(results)
            # 依照「絕對波動幅度」排序，波動越大越好
            res_df['abs_roi'] = res_df['ai_roi_pct'].abs()
            return res_df.sort_values("abs_roi", ascending=False)
        
        return pd.DataFrame()