# config/settings.py (V3 - Force Override Edition)
import os
import sys
from dotenv import load_dotenv
import colorama
from colorama import Fore

colorama.init(autoreset=True)

# --- 🔍 強力路徑定位與載入 ---
# 1. 抓出 settings.py 所在的 config 資料夾
current_dir = os.path.dirname(os.path.abspath(__file__))
# 2. 抓出專案根目錄 (D:\IronDiscipline)
project_root = os.path.dirname(current_dir)
# 3. 鎖定 .env 檔案
env_path = os.path.join(project_root, '.env')

print(f"{Fore.YELLOW}[Config] 正在讀取設定檔: {env_path}")

# 4. 強制載入 (override=True 是關鍵！這跟 test_env.py 一樣強)
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)
    print(f"{Fore.GREEN}[Config] .env 載入成功！")
else:
    # 備案：如果路徑算錯，試著從當前目錄找
    print(f"{Fore.RED}[Config] ❌ 找不到 {env_path}，嘗試備用路徑...")
    load_dotenv(override=True)

class Config:
    # 帳號設定 (從 .env 讀取)
    FINMIND_USER = os.getenv("FINMIND_USER")
    FINMIND_PASS = os.getenv("FINMIND_PASS")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    # 系統參數 (保留你原本的設定)
    TARGET_STOCK = "2330"
    START_DATE = "2020-01-01"
    
    # TFT 模型參數
    WINDOW_SIZE = 120
    PREDICTION_DAYS = 10
    
    # 風控參數
    MAX_LOSS_PERCENT = 0.02 
    ATR_MULTIPLIER = 2.0     
    
    # 路徑設定 (使用絕對路徑比較安全)
    DATA_DIR = os.path.join(project_root, "data")
    MODEL_PATH = os.path.join(DATA_DIR, "universal_tft_v1.ckpt")

    @staticmethod
    def ensure_dirs():
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        os.makedirs(os.path.join(project_root, "logs"), exist_ok=True)

    # --- 自我檢查 (開機自檢) ---
    if not FINMIND_USER:
        print(f"{Fore.RED}[Config Error] ❌ 嚴重錯誤: 仍然讀不到 FINMIND_USER！")
        print(f"請確認 .env 檔案內容是否為: FINMIND_USER=你的帳號")
    else:
        # 只顯示前三碼，確保有讀到東西
        masked_user = str(FINMIND_USER)[:3] + "***"
        print(f"{Fore.GREEN}[Config] 帳號讀取確認: {masked_user}")

Config.ensure_dirs()