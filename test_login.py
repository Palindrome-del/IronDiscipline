# test_login.py
from utils.data_loader import DataLoader

try:
    loader = DataLoader()
    print("測試結束：DataLoader 初始化成功")
except Exception as e:
    print(f"測試結束：發生錯誤 - {e}")