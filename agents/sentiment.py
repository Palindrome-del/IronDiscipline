# agents/sentiment.py
import feedparser
import ollama
import colorama
from colorama import Fore
from datetime import datetime, timedelta
from dateutil import parser
import pytz # 處理時區

colorama.init(autoreset=True)

class SentimentAgent:
    def __init__(self):
        self.model_name = "llama3"
        # Google News RSS 連結 (針對台灣繁體中文)
        self.rss_url = "https://news.google.com/rss/search?q={stock_id}+when:1d&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        
    def fetch_news(self, stock_id="2330"):
        """
        使用 RSS 獲取新聞，並進行嚴格的時間過濾
        """
        print(f"{Fore.CYAN}[News Agent] 正在透過 RSS 掃描 {stock_id} 近 24 小時新聞...")
        
        target_url = self.rss_url.format(stock_id=f"{stock_id}+台積電") 
        feed = feedparser.parse(target_url)
        
        headlines = []
        now = datetime.now(pytz.utc)
        
        count = 0
        for entry in feed.entries:
            try:
                # 1. 時間過濾
                pub_date = parser.parse(entry.published)
                # 確保 pub_date 有時區資訊，如果沒有預設為 UTC
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=pytz.utc)
                
                # 計算差距
                time_diff = now - pub_date
                
                # 嚴格過濾：只看過去 18 小時內的新聞 (涵蓋夜盤與今晨)
                if time_diff > timedelta(hours=18):
                    continue 
                
                title = entry.title
                # 2. 關鍵字過濾
                if any(k in title for k in ["台積", "晶圓", "外資", "大盤", "台股", "ADR", "費半"]):
                    hours_ago = int(time_diff.total_seconds() / 3600)
                    headlines.append(f"[{hours_ago}小時前] {title}")
                    count += 1
                    
            except Exception as e:
                continue

        # 如果新聞太少，可能是系統問題，回傳空以避免誤判
        if count == 0:
            print(f"{Fore.YELLOW}[News Agent] 無符合時間篩選的新聞。")
            return []

        # 按照時間排序 (越新越前面)
        return headlines[:10]

    def analyze(self, stock_id="2330"):
        headlines = self.fetch_news(stock_id)
        
        if not headlines:
            return 0, "無最新新聞數據", 0
            
        news_text = "\n".join(headlines)
        print(f"{Fore.CYAN}[News Agent] 過濾後的高信度新聞:\n{news_text}")
        print(f"{Fore.YELLOW}[News Agent] 傳送至 Llama 3 進行專家解讀 (Risk Manager Persona)...")

        # --- 專家級 Prompt ---
        prompt = f"""
        Role: You are a senior risk manager at a hedge fund.
        Task: Analyze the sentiment of the following news headlines for TSMC (2330).
        
        News Headlines (sorted by time, [0 hours ago] is the latest):
        {news_text}
        
        Instructions:
        1. FOCUS on the MOST RECENT headlines (0-6 hours ago).
        2. IGNORE old bullish news if recent news contains words like "Crash", "Plummet", "Drop", "重挫", "大跌".
        3. Output a Sentiment Score from -1.0 (Extreme Bearish) to 1.0 (Extreme Bullish). 
           - Night market crash (夜盤大跌) or ADR drop = Negative Score.
        4. Provide a concise reason in Traditional Chinese.

        Output Format:
        Score: [Score]
        Reason: [Reason]
        """
        
        try:
            response = ollama.chat(model=self.model_name, messages=[
                {'role': 'user', 'content': prompt},
            ])
            
            content = response['message']['content']
            
            # 解析回應
            score = 0
            reason = "AI 無法解析"
            
            lines = content.split('\n')
            for line in lines:
                if "Score:" in line:
                    try:
                        import re
                        score_str = re.findall(r"[-+]?\d*\.\d+|\d+", line)[0]
                        score = float(score_str)
                    except:
                        pass
                if "Reason:" in line:
                    reason = line.split(":", 1)[1].strip()
            
            # 歸一化信號
            final_signal = 0
            if score >= 0.3: final_signal = 1
            elif score <= -0.3: final_signal = -1
            
            return final_signal, f"AI 情緒分: {score} ({reason})", score

        except Exception as e:
            print(f"{Fore.RED}[News Agent] 分析失敗: {e}")
            return 0, "LLM 連線錯誤", 0