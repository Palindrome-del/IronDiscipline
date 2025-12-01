import numpy as np
from config.settings import Config
import colorama
from colorama import Fore

colorama.init(autoreset=True)

class Executor:
    def __init__(self, capital=120000): # 預設本金 12 萬
        self.capital = capital

    def plan_trade(self, df, tft_data, total_score, risk_safe):
        """
        根據分析結果，生成具體的交易計畫
        """
        current_price = df['Close'].iloc[-1]
        
        # TFT 數據
        p10 = tft_data['p10'][0] # 近期支撐
        p50 = tft_data['p50'][0] # 預測目標
        p90 = tft_data['p90'][0] # 近期壓力
        
        # 1. 決定方向
        direction = "NEUTRAL"
        if total_score >= 2 and risk_safe:
            direction = "LONG"
        elif total_score <= -2 and risk_safe:
            direction = "SHORT"
        
        if direction == "NEUTRAL":
            return {
                "action": "觀望",
                "reason": "訊號不明確或風控未過",
                "entry": None,
                "stop_loss": None,
                "take_profit": None,
                "size": 0
            }

        # 2. 計算進出場點位 (精密戰術)
        if direction == "LONG":
            # 進場：不要追高，掛在 TFT 預測的中軸與下緣之間
            entry_price = (current_price + p10) / 2
            # 停損：跌破 TFT 預測的下緣 (P10) 再多讓 1%
            stop_loss = p10 * 0.99
            # 停利：TFT 預測的上緣 (P90)
            take_profit = p90
            
        elif direction == "SHORT":
            # 進場：掛在現價與壓力 (P90) 之間
            entry_price = (current_price + p90) / 2
            # 停損：突破壓力位 (P90) 再多讓 1%
            stop_loss = p90 * 1.01
            # 停利：TFT 預測的下緣 (P10)
            take_profit = p10

        # 3. 資金控管 (Position Sizing) - 凱利公式簡化版
        # 預期獲利 %
        reward_pct = abs(take_profit - entry_price) / entry_price
        # 預期虧損 %
        risk_pct = abs(entry_price - stop_loss) / entry_price
        
        # 盈虧比 (Reward/Risk Ratio)
        rr_ratio = reward_pct / risk_pct if risk_pct > 0 else 0
        
        # 建議倉位 (Base Position): 
        # 如果盈虧比 > 2 (賺10%賠5%) -> 下 20% 資金
        # 如果盈虧比 < 1.5 -> 不建議進場
        
        position_pct = 0
        if rr_ratio > 2.5:
            position_pct = 0.30 # 強力訊號，下 30%
        elif rr_ratio > 1.5:
            position_pct = 0.15 # 普通訊號，下 15%
        else:
            return {
                "action": "放棄",
                "reason": f"盈虧比過低 ({rr_ratio:.2f})，不值得冒險",
                "entry": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "size": 0
            }
            
        suggested_amount = self.capital * position_pct

        return {
            "action": "做多 (Buy Call)" if direction == "LONG" else "做空 (Buy Put)",
            "reason": f"趨勢明確且盈虧比優秀 (R/R: {rr_ratio:.1f})",
            "entry": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "size_pct": position_pct,
            "amount": suggested_amount
        }
