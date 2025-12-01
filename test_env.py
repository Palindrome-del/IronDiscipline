# test_env.py
import os
from dotenv import load_dotenv

# 強制載入當前目錄的 .env
load_dotenv(override=True)

user = os.getenv("FINMIND_USER")
password = os.getenv("FINMIND_PASS")

print(f"偵測到的帳號: {user}")
print(f"偵測到的密碼: {password}")

if user:
    print("✅ 環境變數讀取成功！")
else:
    print("❌ 讀取失敗，user 為 None")