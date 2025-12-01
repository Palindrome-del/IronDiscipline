# utils/watchlist_mgr.py
import json
import os
from config.settings import Config

class WatchlistManager:
    def __init__(self):
        self.file_path = os.path.join(Config.DATA_DIR, "watchlist.json")
        if not os.path.exists(self.file_path):
            self.save([])

    def load(self):
        with open(self.file_path, 'r') as f:
            return json.load(f)

    def save(self, data):
        with open(self.file_path, 'w') as f:
            json.dump(data, f)

    def add_stock(self, stock_id, reason=""):
        data = self.load()
        # 避免重複
        if not any(d['id'] == stock_id for d in data):
            data.append({"id": stock_id, "reason": reason})
            self.save(data)
            return True
        return False

    def remove_stock(self, stock_id):
        data = self.load()
        new_data = [d for d in data if d['id'] != stock_id]
        self.save(new_data)