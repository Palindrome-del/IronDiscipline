# agents/strategy_agent.py (V13.1 - Corrected: Force 2.5-Pro Priority)
import os
import time
import google.generativeai as genai
from google.api_core import exceptions
from config.settings import Config
import colorama
from colorama import Fore

colorama.init(autoreset=True)

class StrategyAgent:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.model = None
        
        if not self.api_key:
            print(f"{Fore.RED}[Strategy] ⚠️ 未偵測到 GOOGLE_API_KEY。")
            return

        try:
            genai.configure(api_key=self.api_key)
            
            # --- [關鍵修正] 強制優先使用 2.5-pro ---
            # 系統會依序嘗試，直到成功為止。這樣既能追求最強，又有備案。
            target_models = [
                "models/gemini-2.5-pro",      # 👑 第一順位：我們指定的頂規模型
                "models/gemini-2.0-flash-exp",# ⚡ 第二順位：速度極快的實驗版
                "models/gemini-1.5-pro",      # 🛡️ 第三順位：穩定的量產版
                "models/gemini-pro"
            ]
            
            for m in target_models:
                try:
                    # 測試連線
                    test_model = genai.GenerativeModel(m)
                    # 嘗試生成一個極短的 token 以確認權限 (避免假性成功)
                    # 注意：有些模型初始化不報錯，但在生成時才報錯，所以這裡只做初始化
                    # 真正的 Fallback 會在 _retry_generate 裡處理
                    self.model = test_model
                    print(f"{Fore.GREEN}[Strategy] AI 投資長已上線，核心: {m}")
                    break
                except Exception as e:
                    print(f"{Fore.YELLOW}[Strategy] 嘗試 {m} 失敗，切換下一備援...")
                    continue
            
            if self.model is None:
                print(f"{Fore.RED}[Strategy] ❌ 所有 Gemini 模型初始化失敗！請檢查 API Key 或網路。")

        except Exception as e:
            print(f"{Fore.RED}[Strategy] 初始化失敗: {e}")

    def _retry_generate(self, prompt, retries=3):
        """
        帶有重試機制的生成函數，確保決策不中斷
        """
        if not self.model: return "AI_ERROR: 模型未就緒"

        for i in range(retries):
            try:
                response = self.model.generate_content(prompt)
                if response.text: return response.text
            except exceptions.ResourceExhausted:
                wait = (i + 1) * 5
                print(f"{Fore.YELLOW}[Strategy] API 額度滿載，休息 {wait} 秒...")
                time.sleep(wait)
            except Exception as e:
                print(f"{Fore.RED}[Strategy] 思考錯誤 (第 {i+1} 次): {e}")
                # 如果是模型不存在的錯誤 (404)，這時候也可以考慮在這裡做 runtime fallback，但初始化已經做過篩選，機率較低
                time.sleep(2)
        return "AI_ERROR: 決策迴路過載 (無法生成)"

    def consult(self, stock_id, tech_data, warrant_plan, macro_data, portfolio_data):
        """
        核心決策：進場審核 (狼性版)
        """
        cash = portfolio_data['cash']
        
        # 狼性 Prompt：強調攻擊性與逆勢操作
        prompt = f"""
        Role: Elite Hedge Fund Manager (Wolf Style).
        Objective: Aggressive Capital Recovery (Target: +70% Total Return).
        User Profile: Wants "Home Run" trades using Warrants. High Risk Tolerance.
        
        [Target Info]
        Stock: {stock_id}
        Proposed Strategy: {warrant_plan['strategy']} ({warrant_plan.get('direction', 'Unknown')})
        
        [Technical Intelligence (AI Prediction)]
        Current Price: {tech_data[0]}
        AI Target: {tech_data[1]}
        Predicted ROI: {(tech_data[1]-tech_data[0])/tech_data[0]*100:.2f}% (10 Days)
        Support Level: {tech_data[2]}
        
        [Macro Environment]
        Global/Local Score: {macro_data[0]:.2f} (Range -3 to +3)
        Market Status: {macro_data[1]}
        
        [CRITICAL DECISION MATRIX - THE WOLF CODE]
        1. **The "Reversal Sniper" Setup (Contrarian Long):**
           - IF Macro is Negative (Panic/Crash) BUT Tech ROI is > +3% (Strong Rebound Prediction).
           - ACTION: This is a PRIME BUY signal. The market is wrong, the stock is oversold.
           - INSTRUCTION: Authorize Aggressive Call Warrant. Buy when others bleed.
           
        2. **The "Wolf Pack" Setup (Momentum Short):**
           - IF Macro is Negative AND Tech ROI is < -2% (Crash Prediction).
           - ACTION: This is a PRIME SHORT signal.
           - INSTRUCTION: Authorize Aggressive Put Warrant. Do not hesitate.
           
        3. **The "Trend Follower" Setup:**
           - IF Macro is Positive AND Tech ROI is > +2%.
           - ACTION: Standard Buy.
        
        [Output Requirements]
        **決策：** [全力出擊 / 分批進場 / 放棄]
        **狼性分析：** [解釋為什麼這是肥肉？是超跌反彈？還是順勢崩盤？]
        **資金配置：** [建議金額或 %，若是權證請大膽一點]
        **停損鐵律：** [給出明確價位，跌破即砍]
        
        Reply in Traditional Chinese. Be sharp, concise, and predatory. No disclaimer needed.
        """
        return self._retry_generate(prompt)

    def compare(self, challenger, incumbent, macro_data):
        """
        換股評估：新歡 vs 舊愛 (殘酷淘汰制)
        """
        prompt = f"""
        Role: Ruthless Portfolio Manager.
        Task: Optimization Duel (Challenger vs Incumbent).
        
        [Challenger (New Opportunity)]
        Stock: {challenger['id']}
        Predicted ROI: {challenger['roi']:.2f}%
        Price: {challenger['price']}
        
        [Incumbent (Current Holding)]
        Stock: {incumbent['id']}
        Remaining Potential ROI: {incumbent['roi']:.2f}%
        Current Profit/Loss: {incumbent['profit_pct']:.2f}%
        
        [Macro Context]
        Score: {macro_data[0]:.2f} ({macro_data[1]})
        
        [Decision Logic]
        1. **Opportunity Cost:** Is the Challenger's ROI significantly higher (> 5% diff) than the Incumbent's *remaining* potential?
        2. **Dead Money:** If Incumbent is stagnant and Challenger is moving, SWAP immediately.
        3. **Switching Cost:** Assume 0.6% cost. The swap must justify this.
        
        [Output]
        **決策：** [立即換股 / 續抱舊股]
        **對決分析：** [比較兩者爆發力與風險]
        **執行指令：** [賣出 X 買入 Y 的具體操作]
        
        Reply in Traditional Chinese.
        """
        return self._retry_generate(prompt)

    def review_holding(self, stock_id, holding_data, tech_data, macro_data):
        """
        持倉診斷：去弱留強
        """
        curr, target, support = tech_data
        cost = holding_data['avg_cost']
        p_type = holding_data['type']
        
        # 計算未實現損益
        roi_pct = (curr - cost) / cost * 100 if cost > 0 else 0
        
        # 剩餘上漲空間
        remaining_upside = (target - curr) / curr * 100
        
        prompt = f"""
        Role: Cold-Blooded Risk Manager.
        Task: Position Audit.
        
        [Position Status]
        Target: {stock_id} ({p_type})
        Unrealized P/L: {roi_pct:.2f}%
        
        [Forward Outlook]
        AI Prediction: Target {target:.1f} (Upside: {remaining_upside:.2f}%)
        Support Level: {support:.1f}
        Macro Score: {macro_data[0]:.2f}
        
        [Evaluation Rules]
        1. **Kill the Losers:** If P/L < -5% AND AI predicts further downside -> SELL IMMEDIATELY.
        2. **Take Profit:** If P/L > 20% AND Upside is limited (<3%) -> SELL to lock in gains.
        3. **Ride the Winner:** If P/L > 0 AND AI predicts strong upside -> HOLD or ADD.
        
        [Output]
        **診斷結果：** [續抱 / 減碼獲利 / 清倉止損 / 加碼]
        **戰況分析：** [目前的處境與未來預期]
        **戰術指令：** [明確的行動，包含新的移動停損點位]
        
        Reply in Traditional Chinese.
        """
        return self._retry_generate(prompt)