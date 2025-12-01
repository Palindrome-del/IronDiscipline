# agents/tech_agent.py (V12 - Professional Features Match)
import os
import numpy as np
import pandas as pd
import torch
import lightning.pytorch as pl
from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
from pytorch_forecasting.data import GroupNormalizer
from config.settings import Config
from datetime import timedelta
import colorama
from colorama import Fore

colorama.init(autoreset=True)

class TechAgent:
    def __init__(self):
        self.model_dir = Config.DATA_DIR
        self.model_path = self._find_best_model()
        self.dataset_path = os.path.join(Config.DATA_DIR, "fitted_dataset.pkl")
        self.model = None
        self.trained_dataset = None 
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        if self.model_path:
            try:
                self.model = TemporalFusionTransformer.load_from_checkpoint(self.model_path)
                self.model.eval()
                self.model.to(self.device)
            except: pass

        if os.path.exists(self.dataset_path):
            try: self.trained_dataset = torch.load(self.dataset_path, weights_only=False)
            except: 
                try: self.trained_dataset = torch.load(self.dataset_path)
                except: pass

        # 簡化 Proxy 清單
        self.known_universe = ["2330"] # 只要有一個存在的即可，重點在 Re-Scaling

    def _find_best_model(self):
        if not os.path.exists(self.model_dir): return None
        files = [f for f in os.listdir(self.model_dir) if f.endswith(".ckpt") and "universal" in f]
        if not files: return None
        files.sort(key=lambda x: os.path.getmtime(os.path.join(self.model_dir, x)), reverse=True)
        return os.path.join(self.model_dir, files[0])

    def _preprocess(self, df, stock_id):
        data = df.copy()
        data['date'] = pd.to_datetime(data['date'])
        min_date = pd.Timestamp(Config.START_DATE)
        data['time_idx'] = (data['date'] - min_date).dt.days
        
        if 'stock_id' not in data.columns: data['stock_id'] = str(stock_id)
        
        # Proxy 策略: 統一使用 2330，依賴 Normalizer 修正價格
        data['group_id'] = "2330"

        data['log_volume'] = np.log1p(data['Volume'])
        data['pct_change'] = data['Close'].pct_change()
        
        for w in [5, 20, 60]:
            data[f'MA{w}'] = data['Close'].rolling(w).mean()
            data[f'Bias{w}'] = (data['Close'] - data[f'MA{w}']) / (data[f'MA{w}'] + 1e-9)
            
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(6).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(6).mean()
        rs = gain / (loss + 1e-9)
        data['RSI6'] = 100 - (100 / (1 + rs))
        
        exp12 = data['Close'].ewm(span=12, adjust=False).mean()
        exp26 = data['Close'].ewm(span=26, adjust=False).mean()
        data['MACD'] = exp12 - exp26
        data['MACD_signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
        data['MACD_hist'] = data['MACD'] - data['MACD_signal']
        
        low_min = data['Close'].rolling(9).min()
        high_max = data['Close'].rolling(9).max()
        rsv = (data['Close'] - low_min) / (high_max - low_min + 1e-9) * 100
        data['K'] = rsv.ewm(com=2, adjust=False).mean()
        data['D'] = data['K'].ewm(com=2, adjust=False).mean()

        # --- [NEW] 新增特徵計算 (必須與 Trainer 一致) ---
        data['BB_std'] = data['Close'].rolling(20).std()
        data['BB_upper'] = data[f'MA20'] + (data['BB_std'] * 2)
        data['BB_lower'] = data[f'MA20'] - (data['BB_std'] * 2)
        data['BB_width'] = (data['BB_upper'] - data['BB_lower']) / (data[f'MA20'] + 1e-9)
        
        data['Vol_20'] = data['pct_change'].rolling(20).std()
        
        data = data.replace([np.inf, -np.inf], np.nan)
        data = data.ffill().bfill().fillna(0)
        return data

    def _prepare_inference_data(self, df):
        if self.model is None or self.trained_dataset is None: return None, "模型未就緒"

        stock_id = str(df['stock_id'].iloc[0] if 'stock_id' in df.columns else Config.TARGET_STOCK)
        data = self._preprocess(df, stock_id)

        if len(data) < Config.WINDOW_SIZE: return None, f"數據不足 ({len(data)})"

        # 更新特徵白名單
        cols = [
            "date", "stock_id", "time_idx", "group_id", 
            "Close", "Volume", "Foreign_BuySell", "Trust_BuySell", 
            "pct_change", "log_volume", 
            "MA5", "MA20", "MA60", "Bias5", "Bias20", "RSI6",
            "MACD", "MACD_hist", "K", "D",
            "BB_width", "Vol_20" # <--- 新增
        ]
        
        data = data[cols].copy()

        last_idx = data['time_idx'].max()
        last_row = data.iloc[-1]
        gid = data['group_id'].iloc[-1]
        
        future_rows = []
        for i in range(1, Config.PREDICTION_DAYS + 1):
            row = last_row.copy()
            row['time_idx'] = last_idx + i
            row['date'] = last_row['date'] + timedelta(days=i)
            row['group_id'] = gid
            # 假設波動率回歸均值
            row['BB_width'] = row['BB_width'] * 0.95 
            row['Vol_20'] = row['Vol_20'] * 0.95
            future_rows.append(row)
        
        return pd.concat([data, pd.DataFrame(future_rows)], ignore_index=True), "OK"

    def analyze(self, df):
        data, msg = self._prepare_inference_data(df)
        if data is None: return 0, msg, (0, 0, 0)
        try:
            ds = TimeSeriesDataSet.from_dataset(self.trained_dataset, data, predict=True, stop_randomization=True, target_normalizer=GroupNormalizer(groups=["group_id"], transformation="softplus"))
            dl = ds.to_dataloader(train=False, batch_size=1, num_workers=0)
            raw = self.model.predict(dl, mode="raw", return_x=False, trainer_kwargs=dict(accelerator="gpu", devices=1))
            pred = raw['prediction'][0]
            p50 = pred[:, 3].detach().cpu().numpy()
            p10 = pred[:, 1].detach().cpu().numpy()
            curr = df['Close'].iloc[-1]
            target = p50[-1]
            support = p10[-1]
            roi = (target - curr) / curr
            score = 1.5 if roi > 0.04 else (1 if roi > 0.015 else (-1 if roi < -0.015 else -1.5))
            return score, f"目標 {target:.1f} ({roi*100:.2f}%)", (curr, target, support)
        except Exception as e:
            return 0, f"推論錯誤: {e}", (0, 0, 0)

    def get_plot_data(self, df):
        data, _ = self._prepare_inference_data(df)
        if data is None: return {}
        try:
            ds = TimeSeriesDataSet.from_dataset(self.trained_dataset, data, predict=True, stop_randomization=True, target_normalizer=GroupNormalizer(groups=["group_id"], transformation="softplus"))
            dl = ds.to_dataloader(train=False, batch_size=1, num_workers=0)
            raw = self.model.predict(dl, mode="raw", return_x=False, trainer_kwargs=dict(accelerator="gpu", devices=1))
            pred = raw['prediction'][0]
            future_dates = []
            curr_date = df['date'].iloc[-1]
            for _ in range(Config.PREDICTION_DAYS):
                curr_date += timedelta(days=1)
                while curr_date.weekday() >= 5: curr_date += timedelta(days=1)
                future_dates.append(curr_date)
            return {
                "hist_dates": df['date'], "hist_close": df['Close'], "pred_dates": future_dates,
                "p10": pred[:, 1].detach().cpu().numpy(), "p50": pred[:, 3].detach().cpu().numpy(), "p90": pred[:, 5].detach().cpu().numpy()
            }
        except: return {}