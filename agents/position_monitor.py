# agents/position_monitor.py
import pandas as pd
from colorama import Fore
import colorama

colorama.init(autoreset=True)

class PositionMonitor:
    def __init__(self, loader, portfolio_agent):
        self.loader = loader
        self.portfolio_agent = portfolio_agent

    def review_portfolio(self):
        """
        巡視所有持倉，計算即時損益與戰術狀態
        """
        p_data = self.portfolio_agent.get_summary()
        positions = p_data['positions']
        
        if not positions:
            return []

        report = []
        print(f"{Fore.CYAN}[Monitor] 正在巡視 {len(positions)} 檔持倉狀態...")

        for pos in positions:
            stock_id = pos['stock_id']
            
            # 1. 獲取即時行情 (強制更新)
            df = self.loader.fetch_data(stock_id, force_update=True)
            if df is None or df.empty:
                continue
                
            current_price = df['Close'].iloc[-1]
            
            # 2. 計算損益
            cost = pos['avg_cost']
            qty = pos['qty']
            market_value = current_price * qty
            # 簡單估算賣出費用 (0.4425% = 手續費+稅)
            # 權證稅低，這裡做個概算，精確還是要看 portfolio
            fee_rate = 0.004425 if pos['type'] == 'Stock' else 0.002425
            net_market_value = market_value * (1 - fee_rate)
            
            unrealized_pl = net_market_value - (cost * qty)
            roi_pct = (unrealized_pl / (cost * qty)) * 100
            
            # 3. 戰術檢查 (The Discipline Check)
            status = "HOLD"
            action_msg = "續抱"
            status_color = "normal"
            
            stop_loss = pos.get('stop_loss', 0)
            target_price = pos.get('target_price', 99999)
            
            # 檢查停損
            if stop_loss > 0 and current_price <= stop_loss:
                status = "STOP_LOSS"
                action_msg = f"🚨 觸發停損 (現價 {current_price} <= {stop_loss})"
                status_color = "inverse" # 紅色警戒
            
            # 檢查停利
            elif target_price > 0 and current_price >= target_price:
                status = "TAKE_PROFIT"
                action_msg = f"🎉 達標停利 (現價 {current_price} >= {target_price})"
                status_color = "green"
                
            # 檢查嚴重虧損 (無停損設定時的保險)
            elif roi_pct < -10:
                status = "DANGER"
                action_msg = "⚠️ 虧損擴大 (>10%)，請檢查"
                status_color = "inverse"

            report.append({
                "stock_id": stock_id,
                "type": pos['type'],
                "qty": qty,
                "cost": cost,
                "current_price": current_price,
                "market_value": net_market_value,
                "unrealized_pl": unrealized_pl,
                "roi_pct": roi_pct,
                "stop_loss": stop_loss,
                "target_price": target_price,
                "status": status,
                "action_msg": action_msg,
                "status_color": status_color
            })
            
        return report