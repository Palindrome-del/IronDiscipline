from utils.data_loader import DataLoader

loader = DataLoader()
df = loader.fetch_data("2330")
print(df.tail())
print("環境建置成功！")