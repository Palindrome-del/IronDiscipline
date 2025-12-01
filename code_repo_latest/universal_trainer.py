# agents/universal_trainer.py (V12 - Stable Core: Features of V11, Arch of V10)
import sys
import os

# --- 🚑 路徑急救包 ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)
# -------------------

import pandas as pd
import numpy as np
import torch
import lightning.pytorch as pl
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint, LearningRateMonitor
from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
from pytorch_forecasting.data import GroupNormalizer
from pytorch_forecasting.metrics import QuantileLoss
from config.settings import Config
from utils.data_loader import DataLoader
import colorama
from colorama import Fore

colorama.init(autoreset=True)
torch.set_float32_matmul_precision('medium')

class UniversalModelTrainer:
    def __init__(self):
        self.loader = DataLoader()
        self.universe = [
            "2330", "2454", "2303", "3711", "3034", "2379", "3443", "3035", "3661",
            "2317", "2382", "2357", "3231", "2356", "2301", "2376", "2377", "2324", "6669", "3529", "3017",
            "2881", "2882", "2891", "2886", "2884", "2892", "5880", "2885", "2880", "2883", "2887", "5876", "2890",
            "2603", "2609", "2615", "2618", "2610",
            "1101", "1102", "1216", "1301", "1303", "1326", "1402", "2002", "2105", "2207", "2912", "9910", 
            "2308", "3008", "3045", "4904", "4938", "2412", "3037", "2345",
            "1513", "1519", "1504", "1605"
        ]
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        self.model_path = os.path.join(Config.DATA_DIR, "universal_tft.ckpt")

    def prepare_universal_data(self):
        print(f"{Fore.YELLOW}[Trainer] 正在構建穩健型數據池 (含 BB/Vol)...")
        all_df = []
        for stock_id in self.universe:
            try:
                df = self.loader.fetch_data(stock_id, force_update=False)
                if len(df) < Config.WINDOW_SIZE + Config.PREDICTION_DAYS:
                    continue
                df = self._add_features(df, stock_id)
                all_df.append(df)
                print(f" -> 已載入 {stock_id} ({len(df)} rows)")
            except Exception as e:
                print(f" -> {stock_id} 載入失敗: {e}")

        if not all_df:
            raise ValueError("沒有任何數據可供訓練！")

        full_data = pd.concat(all_df, ignore_index=True)
        full_data['group_id'] = full_data['group_id'].astype(str)
        return full_data

    def _add_features(self, df, stock_id):
        data = df.copy()
        data['date'] = pd.to_datetime(data['date'])
        min_date = pd.Timestamp(Config.START_DATE)
        data['time_idx'] = (data['date'] - min_date).dt.days
        
        data['group_id'] = str(stock_id)
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
        
        # MACD
        exp12 = data['Close'].ewm(span=12, adjust=False).mean()
        exp26 = data['Close'].ewm(span=26, adjust=False).mean()
        data['MACD'] = exp12 - exp26
        data['MACD_signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
        data['MACD_hist'] = data['MACD'] - data['MACD_signal']
        
        # KD
        low_min = data['Close'].rolling(9).min()
        high_max = data['Close'].rolling(9).max()
        rsv = (data['Close'] - low_min) / (high_max - low_min + 1e-9) * 100
        data['K'] = rsv.ewm(com=2, adjust=False).mean()
        data['D'] = data['K'].ewm(com=2, adjust=False).mean()

        # BB & Vol (保留這些好用的新特徵)
        data['BB_std'] = data['Close'].rolling(20).std()
        data['BB_upper'] = data['MA20'] + (data['BB_std'] * 2)
        data['BB_lower'] = data['MA20'] - (data['BB_std'] * 2)
        data['BB_width'] = (data['BB_upper'] - data['BB_lower']) / (data['MA20'] + 1e-9)
        data['Vol_20'] = data['pct_change'].rolling(20).std()

        data = data.replace([np.inf, -np.inf], np.nan)
        data = data.ffill().bfill().fillna(0)
        return data

    def train(self):
        data = self.prepare_universal_data()
        print(f"{Fore.GREEN}[Trainer] 數據準備完成，總筆數: {len(data)}。啟動 V12 穩健訓練...")

        training_cutoff = data["time_idx"].max() - Config.PREDICTION_DAYS

        training = TimeSeriesDataSet(
            data[lambda x: x.time_idx <= training_cutoff],
            time_idx="time_idx",
            target="Close",
            group_ids=["group_id"],
            min_encoder_length=Config.WINDOW_SIZE // 2,
            max_encoder_length=Config.WINDOW_SIZE,
            min_prediction_length=1,
            max_prediction_length=Config.PREDICTION_DAYS,
            static_categoricals=["group_id"],
            time_varying_known_reals=["time_idx"],
            time_varying_unknown_reals=[
                "Close", "Volume", "Foreign_BuySell", "Trust_BuySell", 
                "pct_change", "log_volume", 
                "MA5", "MA20", "MA60", "Bias5", "Bias20", "RSI6",
                "MACD", "MACD_hist", "K", "D",
                "BB_width", "Vol_20"
            ],
            target_normalizer=GroupNormalizer(groups=["group_id"], transformation="softplus"),
            add_relative_time_idx=True,
            add_target_scales=True,
            add_encoder_length=True,
            allow_missing_timesteps=True
        )

        dataset_path = os.path.join(Config.DATA_DIR, "fitted_dataset.pkl")
        print(f"{Fore.YELLOW}[Trainer] 儲存特徵字典...")
        torch.save(training, dataset_path)

        validation = TimeSeriesDataSet.from_dataset(training, data, predict=True, stop_randomization=True)
        
        # --- 關鍵回歸：Batch Size 128 ---
        # 這是讓 Loss 穩定的關鍵。128 筆資料才修正一次方向，避免被單一雜訊帶偏。
        train_dataloader = training.to_dataloader(train=True, batch_size=128, num_workers=4, persistent_workers=True)
        val_dataloader = validation.to_dataloader(train=False, batch_size=128, num_workers=4, persistent_workers=True)

        checkpoint_callback = ModelCheckpoint(
            dirpath=Config.DATA_DIR, 
            filename="universal_tft_v1", 
            monitor="val_loss", 
            mode="min", 
            save_top_k=1
        )
        
        early_stop_callback = EarlyStopping(monitor="val_loss", min_delta=1e-4, patience=15, verbose=True, mode="min")
        lr_logger = LearningRateMonitor(logging_interval="epoch")

        trainer = pl.Trainer(
            max_epochs=50, 
            accelerator="gpu", 
            devices=1,
            gradient_clip_val=0.1, # 嚴格風控：0.1
            callbacks=[checkpoint_callback, early_stop_callback, lr_logger],
            enable_model_summary=True,
            precision="bf16-mixed"
        )
        
        tft = TemporalFusionTransformer.from_dataset(
            training,
            learning_rate=0.001, # 標準學習率
            hidden_size=128,     # 回歸 128 (輕量)
            lstm_layers=1,       # 回歸 1 層 (穩定)
            attention_head_size=4,
            dropout=0.15,
            hidden_continuous_size=16,
            output_size=7,
            loss=QuantileLoss(),
            reduce_on_plateau_patience=4,
        )
        
        trainer.fit(tft, train_dataloaders=train_dataloader, val_dataloaders=val_dataloader)
        print(f"{Fore.GREEN}[Trainer] V12 穩健模型訓練完成！")

if __name__ == "__main__":
    trainer = UniversalModelTrainer()
    trainer.train()