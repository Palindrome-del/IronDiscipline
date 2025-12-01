# agents/screener.py (V7 - Transparent Scanning Edition)
import pandas as pd
import numpy as np
from datetime import date, timedelta
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
        
        # 觀察清單
        self.target_stocks = [
            "2330", "2454", "2303", "3711", "3034", "2379", "3443", "3035", "3661",
            "2317", "2382", "2357", "3231", "2356", "2301", "2376", "2377", "2324", "6669", "3529", "3017",
            "2881", "2882", "2891", "2886", "2884", "2892", "5880", "2885", "2880", "2883", "2887", "5876", "2890",
            "2603", "2609", "2615", "2618", "2610",
            "1101", "1102", "1216", "1301", "1303", "1326", "1402", "2002", "2105", "2207", "2912", "9910", 
            "2308", "3008", "3045", "4904", "4938", "2412", "3037", "2345",
            "1513", "1519", "1504", "1605", "0050" # 補回 0050
        ]

    def _scan_single_stock(self, stock_id):
        """
        單一股票掃描邏輯
        """
        try:
            # 強制更新數據
            df = self.loader.fetch_data(stock_id, force_update=True) 
            
            # --- [關鍵修正] 明確回報失敗原因 ---
            if df is None:
                print(f" -> {Fore.RED}{stock_id}: ❌ 數據抓取失敗 (Data Fetch Failed)")
                return None
            
            if len(df) < Config.WINDOW_SIZE:
                print(f" -> {Fore.YELLOW}{stock_id}: ⚠️ 數據不足 (Rows: {len(df)} < {Config.WINDOW_SIZE})")
                return None
            
            current_price = df['Close'].iloc[-1]
            
            # AI 預測
            score, msg, (curr, target, support) = self.tech_agent.analyze(df)
            
            roi = (target - current_price) / current_price
            
            # --- 異常漲幅過濾 ---
            if roi > 0.5:
                print(f" -> {Fore.RED}{stock_id}: ⚠️ 異常漲幅 ({roi*100:.0f}%)，疑似分拆/數據錯誤，略過。")
                return None
            
            # 過濾條件
            if roi > 0.01: 
                print(f" -> {Fore.GREEN}{stock_id}: 發現潛力股! 預期漲幅 {roi*100:.2f}%")
                return {
                    "stock_id": stock_id,
                    "price": current_price,
                    "ai_target": target,
                    "ai_roi_pct": roi * 100,
                    "ai_support": support,
                    "score": score,
                    "msg": msg
                }
            else:
                # [V7] 恢復顯示平淡股，讓你知道系統有在跑
                print(f" -> {stock_id}: 預期平淡 ({roi*100:.2f}%)")
                pass

        except Exception as e:
            print(f"{Fore.RED}Error scanning {stock_id}: {e}")
        
        return None

    def scan(self, strategy="AI_Alpha"):
        print(f"{Fore.CYAN}[Scanner] 啟動 {strategy} 透明掃描 (目標: {len(self.target_stocks)} 檔)...")
        results = []
        
        # 單線程迴圈 + 延遲
        for i, stock_id in enumerate(self.target_stocks):
            res = self._scan_single_stock(stock_id)
            if res:
                results.append(res)
            
            # 禮貌性延遲 (避免被封鎖)
            if i % 5 == 0:
                time.sleep(0.5)
        
        if results:
            res_df = pd.DataFrame(results).sort_values("ai_roi_pct", ascending=False)
            return res_df
        
        return pd.DataFrame()