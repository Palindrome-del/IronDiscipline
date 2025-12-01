# agents/review_agent.py (V2 - Deep Post-Mortem & Strategic Review)
import pandas as pd
import colorama
from colorama import Fore
from config.settings import Config
import time

colorama.init(autoreset=True)

class ReviewAgent:
    def __init__(self, loader, scanner, strategy_agent, history_mgr):
        self.loader = loader
        self.scanner = scanner
        # 透過 scanner 取得 tech_agent，以便進行技術面重估
        self.tech_agent = scanner.tech_agent 
        self.strategy = strategy_agent
        self.history = history_mgr

    def perform_daily_review(self):
        print(f"{Fore.CYAN}[Review] 啟動深度盤後覆盤 (Deep Post-Mortem)...")

        # 1. 獲取觀察名單的今日表現
        targets = self.scanner.target_stocks
        daily_stats = []
        
        print(f"{Fore.YELLOW}[Review] 重新掃描 {len(targets)} 檔標的之收盤數據...")
        for stock_id in targets:
            df = self.loader.fetch_data(stock_id, force_update=True)
            if df is None or len(df) < 2: continue
            
            close = df['Close'].iloc[-1]
            prev_close = df['Close'].iloc[-2]
            pct_change = (close - prev_close) / prev_close * 100
            
            daily_stats.append({
                "stock_id": stock_id,
                "close": close,
                "pct_change": pct_change,
                "df": df # 保留 dataframe 以便重算技術指標
            })
            
        if not daily_stats: return "❌ 無法獲取行情數據。"

        # 2. 找出「超乎預期」的標的 (漲跌幅絕對值 > 3%)
        df_stats = pd.DataFrame(daily_stats)
        # 關注大漲 (錯過機會) 或 大跌 (避開風險)
        significant_moves = df_stats[df_stats['pct_change'].abs() > 3.0].sort_values("pct_change", ascending=False)
        
        report = ["## 📝 每日盤後深度覆盤 (Deep Review)"]
        report.append(f"**時間:** {time.strftime('%Y-%m-%d %H:%M')}\n")
        
        # 讀取早上決策
        history_files = self.history.load_history_list()
        last_tactic = None
        for f in history_files:
            if "Tactic" in f:
                last_tactic = self.history.load_report(f)
                break
        
        rec_stock = last_tactic['content']['stock_id'] if last_tactic else "無"
        report.append(f"### 🎯 今日系統戰術: {rec_stock}")
        
        if last_tactic:
            perf = df_stats[df_stats['stock_id'] == rec_stock]
            if not perf.empty:
                p_chg = perf.iloc[0]['pct_change']
                # 評估今日戰果
                result_type = "獲利" if p_chg > 0 else "虧損"
                report.append(f"- **收盤表現:** {p_chg:.2f}% ({result_type})")

        report.append("\n### 🔍 市場異動與 AI 深度反思")
        
        if significant_moves.empty:
            report.append("今日市場波動平緩，無顯著異動標的需檢討。")
        else:
            # 取前 3 名波動最大的進行檢討
            for _, row in significant_moves.head(3).iterrows():
                sid = row['stock_id']
                change = row['pct_change']
                df = row['df']
                
                # --- 關鍵差異：重新進行技術面評估 (Re-Evaluate) ---
                score, msg, (curr, target, support) = self.tech_agent.analyze(df)
                new_roi = (target - curr) / curr * 100
                
                status = "🔴 錯失" if sid != rec_stock and change > 0 else ("🟢 命中" if sid == rec_stock else "🛡️ 避開")
                
                report.append(f"#### {status}: {sid} ({change:.2f}%)")
                report.append(f"- **收盤後 AI 視角:** 現價 {curr} | 目標 {target:.1f} (預期仍有 +{new_roi:.2f}%) | 支撐 {support:.1f}")
                
                # 呼叫投資長進行「定性分析」
                reflection = self._ask_strategy_deep_review(sid, change, new_roi, support, curr)
                report.append(reflection)
                report.append("---")

        return "\n".join(report)

    def _ask_strategy_deep_review(self, stock_id, actual_change, new_roi, support, current_price):
        """
        投資長深度覆盤：區分「運氣」與「實力」，並給出後市展望
        """
        risk_reward_ratio = new_roi / (abs((current_price - support)/current_price)*100 + 0.1)
        
        prompt = f"""
        Role: Senior Portfolio Manager conducting a Post-Mortem Analysis (Deep Dive).
        
        [Scenario]
        Stock: {stock_id}
        Today's Move: {actual_change:.2f}% (This is what happened)
        
        [Post-Market Re-Evaluation]
        AI updated Projection (After close): +{new_roi:.2f}% Upside remaining.
        New Support Level: {support:.1f}
        Implied Risk/Reward Ratio: {risk_reward_ratio:.2f}
        
        [Analysis Task]
        1. **Classify this move:**
           - Was this a "Good Miss" (High risk gambling, we were right to avoid)?
           - Or a "Bad Miss" (Solid fundamentals/techs, our system failed to catch it)?
        2. **Future Outlook:** - Is it too late to enter tomorrow? (Chasing highs?)
           - Or is this just the beginning of a trend?
        
        [Output Format]
        **覆盤定性：** [系統盲點 / 風控正確 / 隨機波動]
        **原因解析：** [為什麼會漲/跌？是籌碼？還是消息？]
        **後市評估：** [明日操作建議：追價/拉回買/觀望]
        Reply in Traditional Chinese. Keep it sharp and professional.
        """
        return self.strategy._retry_generate(prompt)