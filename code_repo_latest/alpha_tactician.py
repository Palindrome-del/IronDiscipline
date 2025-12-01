# agents/alpha_tactician.py (V9 Final - Complete Code)
import colorama
from colorama import Fore
import pandas as pd
import time

colorama.init(autoreset=True)

class AlphaTactician:
    def __init__(self, hunter, scanner, tech_agent, strategy_agent, macro_agent, portfolio_agent):
        self.hunter = hunter
        self.scanner = scanner
        self.tech_agent = tech_agent
        self.strategy_agent = strategy_agent
        self.macro_agent = macro_agent
        self.portfolio_agent = portfolio_agent

    def generate_daily_tactics(self):
        """
        核心函數：生成今日最佳戰術指令 (含 Top 15 迴圈審核 & 權證風險感知)
        """
        print(f"{Fore.CYAN}[Tactician] 正在召集所有 Agent 進行戰略會議...")
        
        # 1. 情報收集
        m_score, m_msg = self.macro_agent.analyze()
        p_data = self.portfolio_agent.get_summary()
        cash = p_data['cash']
        
        # 2. 獵殺階段
        # 如果 VIX 太高，獵人模式改為保守，否則激進
        hunt_mode = "conservative" if m_score < -1 else "aggressive"
        dynamic_list = self.hunter.hunt(mode=hunt_mode)
        
        # 臨時替換掃描清單
        original_targets = self.scanner.target_stocks
        self.scanner.target_stocks = dynamic_list
        
        # 執行 AI 掃描 (這裡會自動用 fetch_data(force_update=True) 抓即時價)
        df_res = self.scanner.scan(strategy="AI_Alpha")
        
        # 還原清單
        self.scanner.target_stocks = original_targets
        
        if df_res.empty:
            return self._create_empty_report(m_score, m_msg, cash, "全市場掃描完成，無符合 AI 標準之標的。")

        # --- 3. 迴圈審核機制 (Deep Search) ---
        # 擴大搜索範圍至前 15 名，確保不錯過好標的
        search_limit = 15
        candidates = df_res.head(search_limit)
        
        print(f"{Fore.YELLOW}[Tactician] 啟動投資長深度審核 (檢查 Top {search_limit})...")
        
        for i, (index, row) in enumerate(candidates.iterrows()):
            stock_id = row['stock_id']
            roi = row['ai_roi_pct']
            price = row['price']
            support = row['ai_support']
            rank = i + 1
            
            # 基礎門檻：ROI < 1.5% 連問都不用問
            if roi < 1.5:
                print(f" -> [#{rank}] {stock_id} (ROI {roi:.2f}%) 被戰術官直接刷掉 (利潤太少)")
                continue

            print(f"{Fore.CYAN} -> [#{rank}/{search_limit}] 正在讓投資長審核: {stock_id} (ROI {roi:.2f}%) ...")

            # 準備深度資料
            loader = self.scanner.loader
            df_detail = loader.fetch_data(stock_id, force_update=False)
            tech_data = (price, row['ai_target'], support)
            
            # 明確定義這是權證策略，觸發 StrategyAgent 的鎖倉風險檢查
            warrant_context = {
                "strategy": "認購權證 (Call Warrant)", 
                "filters": {"價內外": "依 Gemini 判斷"},
                "stop_loss_trigger": f"跌破 {support:.1f}"
            }

            # 請 Gemini 投資長決策
            final_decision = self.strategy_agent.consult(
                stock_id,
                tech_data,
                warrant_context,
                (m_score, m_msg),
                p_data
            )
            
            # --- API 保護機制 ---
            time.sleep(1) 
            
            # --- 4. 故障安全與判讀 ---
            if "AI_ERROR" in final_decision:
                print(f"{Fore.RED}[Tactician] 投資長連線異常，跳過 {stock_id}")
                continue

            # 清理文字並比對否決關鍵字
            clean_decision = final_decision.replace(" ", "").replace("\n", "").replace("*", "")
            veto_keywords = [
                "決策：觀望", "決策:觀望", "決策：賣出", "決策:賣出", 
                "保持100%現金", "建議空手", "暫不進場", "風險過高"
            ]
            is_vetoed = any(k in clean_decision for k in veto_keywords)
            
            if not is_vetoed:
                # 找到真命天子了！
                print(f"{Fore.GREEN}[Tactician] 投資長核准！鎖定標的: {stock_id}")
                return {
                    "status": "ACTION",
                    "stock_id": stock_id,
                    "price": price,
                    "roi": roi,
                    "support": support,
                    "macro_score": m_score,
                    "macro_msg": m_msg,
                    "cash": cash,
                    "gemini_analysis": final_decision,
                    "ai_target": row['ai_target']
                }
            else:
                print(f"{Fore.RED}[Tactician] 投資長否決 {stock_id}，繼續尋找...")

        # --- 5. 全軍覆沒 ---
        return self._create_empty_report(
            m_score, m_msg, cash, 
            f"已深度審核今日最佳的 {search_limit} 檔標的，但全數因風險過高或總經因素被投資長否決。今日強烈建議空手。"
        )

    def _create_empty_report(self, m_score, m_msg, cash, reason):
        return {
            "status": "WAIT",
            "stock_id": "N/A",
            "macro_score": m_score,
            "macro_msg": m_msg,
            "cash": cash,
            "reason": reason,
            "gemini_analysis": f"**決策：** 觀望\n**分析：** {reason}\n**指令：** 保持 100% 現金部位，靜待機會。"
        }

    # --- [NEW] 換股評估功能 ---
    def evaluate_rebalance(self, new_report, old_stock_id):
        """
        比較新發現的標的 (new_report) 與 手中的持股 (old_stock_id)
        """
        print(f"{Fore.MAGENTA}[Tactician] 啟動換股評估: {new_report['stock_id']} vs {old_stock_id}...")
        
        # 1. 獲取舊股的即時狀態 (必須重新 AI 分析)
        loader = self.scanner.loader
        df = loader.fetch_data(old_stock_id, force_update=True) # 強制更新
        
        if df is None: return "無法獲取持股數據"
        
        score, msg, (curr, target, support) = self.tech_agent.analyze(df)
        # 計算舊股的「剩餘」漲幅潛力
        new_roi = (target - curr) / curr * 100
        
        # 獲取持倉成本
        p_data = self.portfolio_agent.get_summary()
        holding = next((p for p in p_data['positions'] if p['stock_id'] == old_stock_id), None)
        if not holding: return "持倉中找不到此股票"
        
        # 兼容舊資料 (若無 avg_cost 則用 cost)
        cost = holding.get('avg_cost', holding.get('cost', curr))
        profit_pct = (curr - cost) / cost * 100
        
        # 2. 打包數據
        challenger = {
            "id": new_report['stock_id'],
            "price": new_report['price'],
            "roi": new_report['roi'],
            "support": new_report['support']
        }
        
        incumbent = {
            "id": old_stock_id,
            "cost": cost,
            "price": curr,
            "roi": new_roi, 
            "support": support,
            "profit_pct": profit_pct
        }
        
        m_score, m_msg = self.macro_agent.analyze()
        
        # 3. 呼叫投資長對決
        decision = self.strategy_agent.compare(challenger, incumbent, (m_score, m_msg))
        return decision