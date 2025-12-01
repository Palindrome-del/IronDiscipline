# agents/portfolio_agent.py (V5 - Smart Type Detection & Auto-Fix)
import json
import os
from config.settings import Config
from datetime import datetime

class PortfolioAgent:
    def __init__(self):
        self.file_path = os.path.join(Config.DATA_DIR, "portfolio.json")
        self._ensure_file_exists()
        
        self.FEE_RATE = 0.001425
        self.TAX_STOCK = 0.003
        self.TAX_WARRANT = 0.001
        self.DISCOUNT_STOCK = 0.6
        self.DISCOUNT_WARRANT = 1.0

    def _ensure_file_exists(self):
        if not os.path.exists(self.file_path):
            initial_data = {
                "cash": 117000.0,
                "positions": [],
                "history": []
            }
            self.save(initial_data)

    def load(self):
        with open(self.file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 強制轉型：確保所有 ID 都是字串，避免 int/str 混用
            for p in data['positions']:
                p['stock_id'] = str(p['stock_id']).strip()
            return data

    def save(self, data):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def get_summary(self):
        return self.load()

    def update_cash(self, new_amount):
        data = self.load()
        data['cash'] = float(new_amount)
        self.save(data)

    def record_transaction(self, action, stock_id, p_type, price, qty, note="", stop_loss=0.0, target_price=0.0):
        data = self.load()
        
        stock_id = str(stock_id).strip() # 強制轉字串
        price = float(price)
        qty = int(qty)
        
        # --- [V5 新增] 智慧型別修正邏輯 (僅針對賣出) ---
        # 如果使用者想賣出，但類型選錯了，系統自動嘗試修正
        if action == 'SELL':
            # 先找完全匹配的
            exact_match = next((p for p in data['positions'] if str(p['stock_id']) == stock_id and p['type'] == p_type), None)
            
            if not exact_match:
                # 如果找不到，試著找「ID 一樣但類型不同」的
                fuzzy_match = next((p for p in data['positions'] if str(p['stock_id']) == stock_id), None)
                
                if fuzzy_match:
                    # 找到了！自動修正類型
                    detected_type = fuzzy_match['type']
                    print(f"⚠️ [Portfolio] 偵測到類型錯誤，自動修正: {p_type} -> {detected_type}")
                    p_type = detected_type # 自動切換為庫存中的正確類型
        # ------------------------------------------------
        
        amount = price * qty
        
        # 根據最終確認的 p_type 計算費率
        discount = self.DISCOUNT_STOCK if p_type == 'Stock' else self.DISCOUNT_WARRANT
        raw_fee = amount * self.FEE_RATE * discount
        fee = max(20, int(raw_fee))
        
        tax_rate = self.TAX_WARRANT if p_type == 'Warrant' else self.TAX_STOCK
        tax = int(amount * tax_rate) if action == 'SELL' else 0
        
        total_impact = 0
        
        if action == 'BUY':
            total_cost = amount + fee
            if data['cash'] < total_cost:
                return False, f"❌ 現金不足！需 ${total_cost:,.0f}"
            
            data['cash'] -= total_cost
            total_impact = -total_cost
            
            existing = next((p for p in data['positions'] if str(p['stock_id']) == stock_id and p['type'] == p_type), None)
            
            if existing:
                old_total = existing['avg_cost'] * existing['qty']
                new_qty = existing['qty'] + qty
                existing['avg_cost'] = (old_total + total_cost) / new_qty
                existing['qty'] = new_qty
                if stop_loss > 0: existing['stop_loss'] = stop_loss
                if target_price > 0: existing['target_price'] = target_price
            else:
                data['positions'].append({
                    "stock_id": stock_id,
                    "type": p_type,
                    "avg_cost": total_cost / qty,
                    "qty": qty,
                    "stop_loss": float(stop_loss),
                    "target_price": float(target_price),
                    "note": note
                })

        elif action == 'SELL':
            net_income = amount - fee - tax
            data['cash'] += net_income
            total_impact = net_income
            
            existing = next((p for p in data['positions'] if str(p['stock_id']) == stock_id and p['type'] == p_type), None)
            
            if existing:
                if existing['qty'] < qty:
                    return False, f"❌ 庫存不足！(持有: {existing['qty']}, 欲賣: {qty})"
                
                existing['qty'] -= qty
                if existing['qty'] == 0:
                    data['positions'].remove(existing)
            else:
                # 如果到了這一步還找不到，那就是真的沒有
                current_holdings = [f"{p['stock_id']}({p['type']})" for p in data['positions']]
                return False, f"❌ 無此持倉！(目標: {stock_id}-{p_type}, 現有: {current_holdings})"

        record = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "action": action,
            "stock_id": stock_id,
            "type": p_type,
            "price": price,
            "qty": qty,
            "fee": fee,
            "tax": tax,
            "net_cash": total_impact,
            "note": note
        }
        data['history'].insert(0, record)
        self.save(data)
        
        return True, f"交易成功！現金變動: ${total_impact:,.0f}"