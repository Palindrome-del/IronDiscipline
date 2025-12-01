# main.py (V2 - AI Screening Edition)
import sys
import pandas as pd
from config.settings import Config
from utils.data_loader import DataLoader
from agents.tech_agent import TechAgent
from agents.screener import MarketScanner
import colorama
from colorama import Fore, Style

colorama.init(autoreset=True)

def main():
    print(f"\n{Fore.WHITE}{'='*60}")
    print(f"{Fore.WHITE}🛡️  IRON DISCIPLINE AI (V2.0) - AI 戰略雷達啟動  🛡️")
    print(f"{Fore.WHITE}{'='*60}\n")

    # 1. 初始化 AI 大腦 (只載入一次，省時間)
    print(f"{Fore.YELLOW}[System] 正在喚醒 TFT 通用模型...")
    tech_agent = TechAgent()
    
    # 2. 初始化掃描器 (注入大腦)
    scanner = MarketScanner(tech_agent=tech_agent)

    # 3. 執行掃描
    print(f"\n{Fore.WHITE}>>> 開始執行 AI Alpha 策略掃描...")
    df_results = scanner.scan(strategy="AI_Alpha")

    # 4. 顯示結果
    print(f"\n{Fore.WHITE}{'='*60}")
    print(f"{Fore.GREEN}🏆 AI 嚴選潛力股清單 (按預期漲幅排序)")
    print(f"{Fore.WHITE}{'='*60}")

    if not df_results.empty:
        # 顯示前 10 名
        top_picks = df_results.head(10)
        
        # 美化輸出表格
        print(f"{'代號':<8} {'現價':<10} {'AI目標價':<10} {'預期漲幅':<10} {'強力支撐':<10} {'AI訊號'}")
        print("-" * 60)
        
        for _, row in top_picks.iterrows():
            stock = row['stock_id']
            price = row['price']
            target = row['ai_target']
            roi = row['ai_roi_pct']
            support = row['ai_support']
            score = row['score']
            
            # 顏色邏輯
            roi_color = Fore.GREEN if roi > 3 else Fore.WHITE
            score_str = "強力買進" if score >= 1.5 else ("偏多" if score > 0 else "中立")
            
            print(f"{stock:<8} {price:<10.1f} {target:<10.1f} {roi_color}{roi:>6.2f}%{Fore.RESET}   {support:<10.1f} {score_str}")
            
        print(f"\n{Fore.WHITE}共發現 {len(df_results)} 檔標的，請結合籌碼面與消息面進行最終確認。")
    else:
        print(f"{Fore.YELLOW}今日市場風險較高，AI 未發現高信心度的做多標的。建議空手觀望。")

    print(f"{Fore.WHITE}{'='*60}\n")

if __name__ == "__main__":
    main()