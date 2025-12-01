# agents/risk_mgr.py
import numpy as np
import colorama
from colorama import Fore
from config.settings import Config

colorama.init(autoreset=True)

class RiskManager:
    def check_risk(self, df, strategy_score):
        print(f"{Fore.MAGENTA}[Risk Manager] 正在進行壓力測試與風控...")
        
        close = df['Close']
        
        # 1. 波動率檢查 (ATR 概念简化版: 近5日高低震幅平均)
        # 如果你有 high/low 數據更好，這裡用收盤價變化率模擬
        volatility = close.pct_change().tail(5).std()
        
        # 台積電平常波動約 1.5%，如果 > 2.5% 代表市場恐慌
        limit = 0.025
        
        if volatility > limit:
            msg = f"{Fore.RED}❌ 警告：市場波動劇烈 (Vol: {volatility*100:.2f}%) > {limit*100}%，強制鎖單！"
            return False, msg
            
        # 2. 乖離率 (Bias) 檢查
        # 股價跌太深追空會死，漲太高追多會套
        ma20 = close.rolling(20).mean().iloc[-1]
        current = close.iloc[-1]
        bias = (current - ma20) / ma20
        
        # 負乖離過大 (例如 -10%)
        if bias < -0.10:
            if strategy_score < 0: # 策略叫你放空
                msg = f"{Fore.RED}❌ 警告：負乖離過大 ({bias*100:.2f}%)，隨時可能死貓跳，禁止追空！"
                return False, msg
        
        # 3. 停損檢查 (模擬)
        # 這裡未來可以接你的券商 API 讀取真實庫存損益
        # 現在先回傳 Pass
        
        return True, f"{Fore.GREEN}✅ 風控檢測通過 (Vol: {volatility*100:.2f}%, Bias: {bias*100:.2f}%)"