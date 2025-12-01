# agents/warrant_agent.py
import colorama
from colorama import Fore

colorama.init(autoreset=True)

class WarrantAgent:
    def __init__(self):
        pass

    def generate_plan(self, current_price, target_price, support_price, score):
        roi_pct = (target_price - current_price) / current_price
        
        # 1. 決定多空方向
        if roi_pct > 0:
            direction = "CALL"
            category = "認購權證"
        else:
            direction = "PUT"
            category = "認售權證"

        # 2. 戰術參數生成
        if direction == "CALL":
            # 做多邏輯
            if roi_pct > 0.05: 
                moneyness = "價外5%~10%"
                strike_target = current_price * 1.05
                strategy_name = "🚀 攻擊型認購 (OTM Call)"
                desc = "AI 預期大漲，買微價外拼高槓桿。"
            else:
                moneyness = "價平~價內5%"
                strike_target = current_price
                strategy_name = "🛡️ 穩健型認購 (ATM Call)"
                desc = "預期緩漲，買價平減少耗損。"
            stop_loss = support_price
            stop_loss_desc = f"現貨跌破 {support_price:.1f}"
            
        else: # PUT (關鍵升級)
            # 做空邏輯
            if roi_pct < -0.03: # 跌幅超過 3% 視為崩跌
                moneyness = "價外10%~20%" # 深價外認售
                strike_target = current_price * 0.85
                strategy_name = "🐺 嗜血型認售 (Deep OTM Put)"
                desc = "AI 預期崩盤，建議買深價外認售，以小博大拼倍數獲利。"
                stop_loss = target_price * 1.02 # 反彈 2% 停損
            else:
                moneyness = "價平~價外5%"
                strike_target = current_price * 0.95
                strategy_name = "🐻 避險型認售 (ATM Put)"
                desc = "預期修正，買價平認售操作。"
                stop_loss = target_price
            stop_loss_desc = f"現貨反向漲破 {stop_loss:.1f}"

        # 3. 輸出
        filters = {
            "權證標的": category,
            "價內外": moneyness,
            "參考履約價": f"約 {strike_target:.1f}",
            "剩餘日": "> 60 天",
            "行使比例": "越高越好", 
            "成交量": "> 300 張"
        }

        return {
            "strategy": strategy_name,
            "description": desc,
            "current_price": current_price,
            "stop_loss_trigger": stop_loss_desc,
            "filters": filters,
            "direction": direction # 回傳給 UI 用
        }