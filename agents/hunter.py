# agents/hunter.py
import requests
import pandas as pd
import colorama
from colorama import Fore
from bs4 import BeautifulSoup
import re

colorama.init(autoreset=True)

class HunterAgent:
    def __init__(self):
        # Yahoo 股市排行的基礎 URL
        self.base_url = "https://tw.stock.yahoo.com/rank/{type}?exchange={exchange}"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def _fetch_rank(self, rank_type, exchange="TAI"):
        """
        抓取排行榜
        rank_type: 'volume' (成交量), 'change-up' (漲幅), 'turnover-ratio' (周轉率)
        exchange: 'TAI' (上市), 'TWO' (上櫃)
        """
        url = self.base_url.format(type=rank_type, exchange=exchange)
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
        except Exception as e:
            print(f"{Fore.RED}[Hunter] 連線失敗: {e}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 解析股票代號 (Yahoo 的結構可能會變，這裡用通用的 class 抓取)
        # 通常股票代號會在一個帶有 ticker 連結的結構中
        stocks = []
        
        # 針對 Yahoo 股市新版介面的解析邏輯
        # 尋找所有類似 /quote/2330.TW 的連結
        links = soup.find_all('a', href=re.compile(r'/quote/\d+\.(TW|TWO)'))
        
        for link in links:
            href = link.get('href')
            # 提取代號，例如 /quote/2330.TW -> 2330
            match = re.search(r'(\d+)\.(TW|TWO)', href)
            if match:
                stock_id = match.group(1)
                # 簡單過濾：排除權證 (6位數) 或特殊商品，只留個股 (4位數)
                if len(stock_id) == 4: 
                    stocks.append(stock_id)
        
        # 去除重複並保持順序
        seen = set()
        unique_stocks = [x for x in stocks if not (x in seen or seen.add(x))]
        
        return unique_stocks[:30] # 每個榜單只抓前 30 名，求精不求多

    def hunt(self, mode="aggressive"):
        """
        開始狩獵：整合上市上櫃的強勢股
        mode:
         - aggressive: 抓漲幅排行 + 成交量排行 (適合找飆股)
         - conservative: 抓成交量排行 (適合找權值股)
        """
        print(f"{Fore.RED}🦅 [Hunter Agent] 鷹眼啟動，正在掃描全台股異動...")
        
        targets = set()
        
        # 1. 上市 + 上櫃 成交量排行 (資金熱點)
        print(f"{Fore.YELLOW} -> 掃描資金熱點 (上市/上櫃 成交量)...")
        targets.update(self._fetch_rank("volume", "TAI"))
        targets.update(self._fetch_rank("volume", "TWO"))
        
        if mode == "aggressive":
            # 2. 上市 + 上櫃 漲幅排行 (強勢飆股)
            print(f"{Fore.YELLOW} -> 鎖定強勢飆股 (上市/上櫃 漲幅榜)...")
            targets.update(self._fetch_rank("change-up", "TAI"))
            targets.update(self._fetch_rank("change-up", "TWO"))
            
            # 3. 選擇性：周轉率 (代表有人在炒)
            # targets.update(self._fetch_rank("turnover-ratio", "TAI"))

        target_list = list(targets)
        print(f"{Fore.GREEN}🦅 [Hunter] 狩獵完成！共鎖定 {len(target_list)} 檔異動標的。")
        
        return target_list

# 簡單測試用
if __name__ == "__main__":
    hunter = HunterAgent()
    print(hunter.hunt())