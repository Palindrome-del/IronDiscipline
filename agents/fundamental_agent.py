import pandas as pd
from datetime import date, timedelta
from FinMind.data import DataLoader as FinMindDataLoader
from config.settings import Config
import colorama
from colorama import Fore

colorama.init(autoreset=True)

class FundamentalAgent:
    def __init__(self):
        self.api = FinMindDataLoader()
        self.api.login(user_id=Config.FINMIND_USER, password=Config.FINMIND_PASS)

    def analyze(self, stock_id):
        print(f"{Fore.BLUE}[Fundamental Agent] 正在審計 {stock_id} 財務報表...")
        
        today_str = date.today().strftime('%Y-%m-%d')
        # 抓取過去一年的數據以確保有資料
        start_date = (date.today() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        score = 0
        status = []
        
        try:
            # 1. 月營收 (Revenue) - 最即時的基本面
            df_rev = self.api.taiwan_stock_month_revenue(
                stock_id=stock_id, start_date=start_date, end_date=today_str
            )
            
            if not df_rev.empty:
                last_rev = df_rev.iloc[-1]
                # 年增率 (YoY)
                if last_rev['revenue_year_growth'] > 20:
                    score += 1.5
                    status.append(f"營收爆發(YoY+{last_rev['revenue_year_growth']}%)")
                elif last_rev['revenue_year_growth'] < -10:
                    score -= 1.5
                    status.append(f"營收衰退(YoY{last_rev['revenue_year_growth']}%)")
                
                # 月增率 (MoM) - 動能
                if last_rev['revenue_month_growth'] > 5:
                    score += 0.5
                    status.append("月增")
                elif last_rev['revenue_month_growth'] < -5:
                    score -= 0.5
                    status.append("月減")
            
            # 2. 本益比 (PE Ratio) - 估值
            df_per = self.api.taiwan_stock_per_pbr(
                stock_id=stock_id, start_date=start_date, end_date=today_str
            )
            
            if not df_per.empty:
                last_pe = df_per['PER'].iloc[-1]
                # 簡單過濾：本益比過高 (>60) 危險，過低 (<10) 可能是景氣循環高點或超跌
                # 這裡做個簡單判斷，實戰需搭配產業平均
                if 0 < last_pe < 15:
                    score += 1
                    status.append(f"低估值(PE {last_pe:.1f})")
                elif last_pe > 50:
                    # 成長股 PE 高是正常的，所以這裡只給警示，不扣太多分，除非搭配營收衰退
                    if score < 0: # 營收爛 + PE 高 = 必死
                        score -= 1
                        status.append(f"估值過高(PE {last_pe:.1f})")
                    else:
                        status.append(f"高成長溢價(PE {last_pe:.1f})")

            if not status:
                return 0, "數據不足或平淡"
                
            final_msg = " | ".join(status)
            return score, final_msg

        except Exception as e:
            print(f"{Fore.RED}[Fundamental Agent] 財報獲取失敗: {e}")
            return 0, "財報數據異常"