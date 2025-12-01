# agents/strategy_agent.py (V11 - Position Doctor Edition)
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
            
            # 優先使用 Pro 模型
            target_model = "models/gemini-2.5-pro"
            
            # Fallback check
            try:
                available = [m.name for m in genai.list_models()]
                if target_model not in available:
                    print(f"{Fore.YELLOW}[Strategy] 找不到 {target_model}，切換至 1.5-pro...")
                    target_model = "models/gemini-1.5-pro"
            except: pass

            print(f"{Fore.GREEN}[Strategy] AI 投資長已上線，核心: {target_model}")
            self.model = genai.GenerativeModel(target_model)
            
        except Exception as e:
            print(f"{Fore.RED}[Strategy] 初始化失敗: {e}")

    def _retry_generate(self, prompt, retries=3):
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
                time.sleep(2)
        return "AI_ERROR: 無法生成決策"

    def consult(self, stock_id, tech_data, warrant_plan, macro_data, portfolio_data):
        if not self.model: return "AI_ERROR"
        
        cash = portfolio_data['cash']
        pos_val = sum(p.get('avg_cost', 0) * p['qty'] for p in portfolio_data['positions'])
        total = cash + pos_val
        cash_ratio = (cash / total * 100) if total > 0 else 100
        
        # 鎖倉風險檢查
        is_warrant = "權證" in warrant_plan['strategy'] or "Call" in warrant_plan['strategy']
        liquidity_warning = ""
        if is_warrant:
            liquidity_warning = """
            [CRITICAL WARNING: LIQUIDITY LOCK-IN]
            * The user intends to trade WARRANTS.
            * CONSTRAINT: Warrants CANNOT be day-traded (Sold on T+0). 
            * RISK: If you buy now, you MUST hold until tomorrow. You CANNOT execute a stop-loss today even if the price crashes.
            * IMPACT: This drastically increases risk. Do NOT recommend 'Aggressive' sizing if VIX is high.
            """
        
        prompt = f"""
        Role: Aggressive Hedge Fund Manager (Capital Recovery).
        Style: Opportunistic but Survival-First.
        
        [Target] {stock_id}
        Price: {tech_data[0]} -> Target: {tech_data[1]:.1f} (ROI: {(tech_data[1]-tech_data[0])/tech_data[0]*100:.2f}%)
        Support: {tech_data[2]:.1f}
        Macro: {macro_data[0]} ({macro_data[1]})
        
        [Portfolio] Cash: ${cash:,.0f} ({cash_ratio:.1f}%)
        
        {liquidity_warning}
        
        [Task]
        Evaluate trade. 
        1. If 'LIQUIDITY LOCK-IN' warning exists AND Macro is unstable (VIX high), be EXTREMELY CAUTIOUS.
        2. If conviction is absolute (Home Run setup), allow entry but REDUCE SIZE.
        
        [Output]
        **決策：** [強力買進/小額試單/觀望]
        **風險分析：** ...
        **指令：** [資金%與停損]
        Reply in Traditional Chinese.
        """
        return self._retry_generate(prompt)

    def compare(self, challenger, incumbent, macro_data):
        prompt = f"""
        Role: Portfolio Manager. Duel: New vs Old.
        
        [Challenger (New)] {challenger['id']} | ROI: +{challenger['roi']:.2f}%
        [Incumbent (Old)] {incumbent['id']} | Remaining ROI: +{incumbent['roi']:.2f}% | Profit: {incumbent['profit_pct']:.2f}%
        
        Constraint: Switching cost ~0.6%.
        
        Task: Decide SWAP or HOLD.
        Only swap if Challenger ROI >> Incumbent ROI + Cost.
        
        [Output]
        **決策：** [換股/續抱]
        **分析：** ...
        """
        return self._retry_generate(prompt)

    # --- [NEW] 持倉診斷功能 ---
    def review_holding(self, stock_id, holding_data, tech_data, macro_data):
        """
        針對現有持倉進行深度診斷
        """
        curr, target, support = tech_data
        cost = holding_data['avg_cost']
        qty = holding_data['qty']
        p_type = holding_data['type']
        roi_pct = (curr - cost) / cost * 100 if cost > 0 else 0
        
        # 偵測特殊情境：高獲利但技術面轉弱 / 訊號矛盾
        conflict_context = ""
        if roi_pct > 5 and (curr < support or macro_data[0] < -1):
            conflict_context = """
            [CONFLICT DETECTED]
            * The position is PROFITABLE (>5%), BUT Technical/Macro signals are turning bearish.
            * STRATEGY: Consider 'Partial Profit Taking' (Selling Half) to lock in gains.
            """
            
        prompt = f"""
        Role: Senior Risk Manager (Focus: Profit Protection & Dynamic Adjustment).
        Task: Review an existing position and provide tactical advice.
        
        [Position Status]
        Target: {stock_id} ({p_type})
        Avg Cost: {cost:.2f}
        Current Price: {curr:.2f}
        Unrealized P/L: {roi_pct:.2f}%
        
        [Latest Intelligence]
        AI Tech Prediction: Target {target:.1f} | Support {support:.1f}
        Macro Environment: Score {macro_data[0]} ({macro_data[1]})
        
        {conflict_context}
        
        [Instructions]
        1. **Evaluate Hold vs Sell:** Is the trend still intact?
        2. **Conflict Resolution:** If P/L is positive but risks are rising, suggest trimming.
        3. **Trailing Stop:** Suggest a new stop-loss price based on current price.
        
        [Output Format]
        **診斷結果：** [續抱 / 減碼獲利 (Sell Half) / 清倉離場 / 加碼]
        **戰況分析：** [解釋多空矛盾與應對策略]
        **戰術指令：** [明確的行動，包含移動停損點位]
        Reply in Traditional Chinese.
        """
        return self._retry_generate(prompt)