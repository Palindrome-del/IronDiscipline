# agents/warrant_agent.py (V2 - Filter Output)
import colorama
from colorama import Fore

colorama.init(autoreset=True)

class WarrantAgent:
    def __init__(self):
        pass

    def generate_plan(self, current_price, target_price, support_price, score):
        """
        根據 AI 預測，生成權證操作參數及篩選條件 (對應券商 App 介面)
        """
        roi_pct = (target_price - current_price) / current_price
        
        # 1. 決定多空方向
        is_bull = score > 0.5
        category = "認購權證" if is_bull else "認售權證"

        # 2. 決定履約價策略 (價內外 Moneyness)
        if is_bull:
            if roi_pct > 0.05: # 攻擊型：微價外
                moneyness = "價外2%~價外8%"
                strike_min = current_price * 1.02
                strike_max = current_price * 1.08
                strategy_name = "🚀 攻擊型認購 (OTM Call)"
                desc = "AI 預期漲幅大，建議微價外權證以最大化槓桿爆發力。"
            else: # 穩健型：價平附近
                moneyness = "價外0%~價內3%"
                strike_min = current_price * 0.97
                strike_max = current_price * 1.00
                strategy_name = "🛡️ 防守型認購 (ATM Call)"
                desc = "AI 預期緩漲，建議價平權證避免時間價值耗損。"
        else: # 認售
            # ... 這裡可以添加做空邏輯，但為了專注於你的攻擊目標(回本)，我們暫時聚焦認購
            moneyness = "不適用"
            strategy_name = "空手/避險"
            desc = "目前系統建議做多，不做認售規劃。"
            
        # 3. 輸出篩選條件
        filters = {
            "權證標的": category,
            "類別": category,
            "發行券商": "不指定券商",
            "價內外": moneyness,
            "剩餘日": "> 90 天", # 鐵律：不做短天期
            "執行比例": "不限 (需自行篩選高執行比例)", 
            "隱含波動率": "不限 (需自行篩選IV穩定者)",
            "成交量": "> 500 張", # 增加流動性要求
        }

        return {
            "strategy": strategy_name,
            "description": desc,
            "current_price": current_price,
            "stop_loss_trigger": support_price,
            "filters": filters
        }