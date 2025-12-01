# agents/macro_agent.py
import yfinance as yf
import pandas as pd
import colorama
from colorama import Fore

colorama.init(autoreset=True)

class MacroAgent:
    def __init__(self):
        self.tickers = {
            "^TWII": "台股加權",
            "^SOX": "費城半導體",
            "^VIX": "恐慌指數",
            "TSM": "台積電ADR"
        }

    def analyze(self):
        print(f"{Fore.MAGENTA}[Macro Agent] 啟動全球與在地市場動態掃描 (Smart Weighting)...")
        
        try:
            # 抓取數據 (包含成交量以判斷是否休市)
            data = yf.download(list(self.tickers.keys()), period="5d", progress=False)
            close = data['Close']
            
            # 定義各指標的基礎權重 (滿分 3 分)
            # 台股最重要，VIX 次之
            components = {
                "TWII": {"val": 0, "weight": 1.5, "desc": ""},
                "SOX":  {"val": 0, "weight": 1.0, "desc": ""},
                "ADR":  {"val": 0, "weight": 1.0, "desc": ""},
                "VIX":  {"val": 0, "weight": 1.0, "desc": ""}
            }
            
            # 1. 台股加權 (^TWII)
            tw = close['^TWII'].ffill()
            tw_curr, tw_prev = tw.iloc[-1], tw.iloc[-2]
            tw_chg = (tw_curr - tw_prev) / tw_prev
            components["TWII"]["desc"] = f"台股 {tw_chg*100:.2f}%"
            
            # 狼性評分：大跌時加重扣分，製造做空訊號
            if tw_chg < -0.015: components["TWII"]["val"] = -1.5 # 大跌 > 1.5% (重扣)
            elif tw_chg < -0.005: components["TWII"]["val"] = -0.5
            elif tw_chg > 0.015: components["TWII"]["val"] = 1 # 大漲
            elif tw_chg > 0.005: components["TWII"]["val"] = 0.5

            # 2. 費半 (^SOX) - 偵測休市
            sox = close['^SOX'].ffill()
            if sox.iloc[-1] == sox.iloc[-2]:
                components["SOX"]["desc"] = "費半休市"
                components["SOX"]["weight"] = 0 # 休市不計分
                # 權重轉移給 VIX (市場不確定性增加)
                components["VIX"]["weight"] += 0.5
            else:
                sox_chg = (sox.iloc[-1] - sox.iloc[-2]) / sox.iloc[-2]
                components["SOX"]["desc"] = f"費半 {sox_chg*100:.2f}%"
                if sox_chg < -0.02: components["SOX"]["val"] = -1
                elif sox_chg > 0.02: components["SOX"]["val"] = 1

            # 3. 台積電 ADR (TSM) - 偵測休市
            tsm = close['TSM'].ffill()
            if tsm.iloc[-1] == tsm.iloc[-2]:
                components["ADR"]["desc"] = "ADR休市"
                components["ADR"]["weight"] = 0 # 休市不計分
                # 權重轉移給台股 (回歸在地基本面)
                components["TWII"]["weight"] += 0.5
            else:
                tsm_chg = (tsm.iloc[-1] - tsm.iloc[-2]) / tsm.iloc[-2]
                components["ADR"]["desc"] = f"ADR {tsm_chg*100:.2f}%"
                if tsm_chg < -0.02: components["ADR"]["val"] = -1
                elif tsm_chg > 0.02: components["ADR"]["val"] = 1

            # 4. VIX - 永遠有參考性
            vix = close['^VIX'].ffill().iloc[-1]
            components["VIX"]["desc"] = f"VIX {vix:.1f}"
            if vix > 22: components["VIX"]["val"] = -1 # 恐慌
            elif vix < 15: components["VIX"]["val"] = 0.5 # 安穩

            # --- 關鍵演算法：動態歸一化 (Dynamic Normalization) ---
            # 計算有效總權重 (排除休市的市場)
            total_active_weight = sum(c["weight"] for c in components.values())
            
            # 計算原始得分
            raw_score = sum(c["val"] * c["weight"] for c in components.values())
            
            # 歸一化：將分數放大回 -3 ~ +3 的區間
            if total_active_weight > 0:
                final_score = (raw_score / total_active_weight) * 3.0
            else:
                final_score = 0
            
            # 整理訊息
            status_list = [c["desc"] for c in components.values() if c["desc"]]
            final_msg = " | ".join(status_list)
            
            print(f"{Fore.MAGENTA} -> 有效權重: {total_active_weight:.1f} | 最終評分: {final_score:.2f}")
            
            return final_score, final_msg

        except Exception as e:
            print(f"{Fore.RED}[Macro] Error: {e}")
            return 0, "數據連線異常"