import yfinance as yf
import pandas as pd
import colorama
from colorama import Fore

colorama.init(autoreset=True)

class MacroAgent:
    def __init__(self):
        # 監控清單
        self.tickers = {
            "^SOX": "費城半導體",
            "^GSPC": "S&P 500",
            "^VIX": "恐慌指數",
            "DX-Y.NYB": "美元指數",
            "TSM": "台積電ADR"
        }

    def analyze(self):
        print(f"{Fore.MAGENTA}[Macro Agent] 正在掃描全球金融市場...")
        
        try:
            # 一次抓取所有數據
            tickers_list = list(self.tickers.keys())
            data = yf.download(tickers_list, period="5d", progress=False)['Close']
            
            # 整理數據
            status = []
            score = 0
            
            # 1. 費半 (SOX) - 台股電子命脈
            sox_chg = (data['^SOX'].iloc[-1] - data['^SOX'].iloc[-2]) / data['^SOX'].iloc[-2]
            if sox_chg < -0.015: 
                status.append(f"費半重挫 {sox_chg*100:.2f}%")
                score -= 1.5
            elif sox_chg > 0.015:
                status.append(f"費半大漲 {sox_chg*100:.2f}%")
                score += 1.5
                
            # 2. 恐慌指數 (VIX) - 市場風險溫度計
            vix = data['^VIX'].iloc[-1]
            if vix > 20:
                status.append(f"VIX 高檔 ({vix:.1f})")
                score -= 1 # 避險情緒高
            
            # 3. 美元指數 (DXY) - 資金流向
            dxy_chg = (data['DX-Y.NYB'].iloc[-1] - data['DX-Y.NYB'].iloc[-2])
            if dxy_chg > 0.3:
                status.append("美元強升(資金外流)")
                score -= 0.5
                
            # 4. 台積電 ADR
            tsm_chg = (data['TSM'].iloc[-1] - data['TSM'].iloc[-2]) / data['TSM'].iloc[-2]
            status.append(f"ADR {tsm_chg*100:.2f}%")
            if tsm_chg < -0.02: score -= 1
            elif tsm_chg > 0.02: score += 1

            # 綜合判斷
            final_msg = " | ".join(status)
            
            return score, final_msg

        except Exception as e:
            print(f"{Fore.RED}[Macro Agent] 數據獲取失敗: {e}")
            return 0, "無法連線國際市場"