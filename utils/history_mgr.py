# utils/history_mgr.py
import json
import os
import numpy as np
import pandas as pd
from datetime import datetime
from config.settings import Config

class HistoryManager:
    def __init__(self):
        # 歷史檔案存在 data/history 資料夾
        self.history_dir = os.path.join(Config.DATA_DIR, "history")
        os.makedirs(self.history_dir, exist_ok=True)

    def _make_serializable(self, obj):
        """
        將 NumPy/Pandas 等複雜物件轉換為 JSON 可儲存格式
        """
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(v) for v in obj]
        elif isinstance(obj, (np.ndarray, np.generic)):
            return obj.tolist()
        elif isinstance(obj, pd.Series):
            return obj.tolist()
        elif isinstance(obj, (datetime, pd.Timestamp)):
            return obj.strftime('%Y-%m-%d')
        return obj

    def save_report(self, report_type, stock_id, data):
        """
        儲存戰報
        report_type: 'Tactic'(戰術), 'Analysis'(單股), 'Hunter'(獵人)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{report_type}_{stock_id}.json"
        filepath = os.path.join(self.history_dir, filename)
        
        # 準備儲存資料
        save_data = {
            "meta": {
                "timestamp": timestamp,
                "type": report_type,
                "stock_id": stock_id
            },
            "content": self._make_serializable(data)
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=4, ensure_ascii=False)
            
        return filename

    def load_history_list(self):
        """列出所有歷史檔案 (最新在最前)"""
        if not os.path.exists(self.history_dir):
            return []
        files = [f for f in os.listdir(self.history_dir) if f.endswith(".json")]
        files.sort(reverse=True)
        return files

    def load_report(self, filename):
        """讀取特定戰報"""
        filepath = os.path.join(self.history_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def delete_report(self, filename):
        filepath = os.path.join(self.history_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False