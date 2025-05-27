from huggingface_hub import HfApi
import pandas as pd
from datetime import datetime
import numpy as np

# 初始化 Hugging Face API
api = HfApi()

# 獲取模型列表，按下載次數降序排序
models = api.list_models(
    sort="downloads",  # 按下載次數排序
    direction=-1,      # 降序
    limit=113          # 限制為前 100 個
)

# 準備儲存結果的列表
data = []
total_size_mb = 0  # 用於計算所有 public 模型檔案的總大小（MB）
model_sizes = []   # 儲存每個 public 模型的總大小（MB）

# 遍歷模型，僅處理 public 模型
for model in models:
    model_info = {
        "Name": model.modelId,
        "Type": model.tags[-1] if model.tags else "Unknown",  # 使用最後一個 tag 作為類型
        "Status": "public",  # 默認為 public
        "WeightFiles": [],
        "FileSizes": [],
        "TotalSizeMB": 0.0  # 新增欄位：模型總大小（MB）
    }
    
    # 檢查模型是否為 private 或 gated
    try:
        model_details = api.model_info(model.modelId)
        if model_details.private:
            model_info["Status"] = "private"
        elif model_details.gated:
            model_info["Status"] = "gated"
        
        # 僅對 public 模型查詢檔案資訊
        if model_info["Status"] == "public":
            files = api.list_repo_files(model.modelId)
            weight_files = [f for f in files if f.endswith(('.bin', '.safetensors', '.pt', '.pth', '.gguf'))]
            
            # 儲存權重檔案名稱和大小
            model_total_size_mb = 0.0
            for file in weight_files:
                try:
                    file_info = api.get_paths_info(model.modelId, file)
                    if isinstance(file_info, list):
                        file_info = file_info[0]  # 取第一個匹配的檔案資訊
                    size_mb = file_info.size / (1024 * 1024)  # 轉換為 MB
                    total_size_mb += size_mb  # 累加到全局總大小
                    model_total_size_mb += size_mb  # 累加到該模型總大小
                    model_info["WeightFiles"].append(file)
                    model_info["FileSizes"].append(f"{size_mb:.2f} MB")

                except Exception as e:
                    print(f"Error fetching file info for {model.modelId}/{file}: {e}")
                    model_info["WeightFiles"].append(file)
                    model_info["FileSizes"].append("Unknown")
                


            
            # 記錄模型總大小
            model_info["TotalSizeMB"] = f"{model_total_size_mb:.2f}"
            if model_total_size_mb > 0:
                model_sizes.append(model_total_size_mb)
            
            # 將 WeightFiles 和 FileSizes 轉為字串
            model_info["WeightFiles"] = "; ".join(model_info["WeightFiles"])
            model_info["FileSizes"] = "; ".join(model_info["FileSizes"])
        else:
            # 非 public 模型，設置為空
            model_info["WeightFiles"] = "N/A"
            model_info["FileSizes"] = "N/A"
            model_info["TotalSizeMB"] = "N/A"
        
    except Exception as e:
        print(f"Error fetching details for {model.modelId}: {e}")
        model_info["Status"] = "unknown"
        model_info["WeightFiles"] = "N/A"
        model_info["FileSizes"] = "N/A"
        model_info["TotalSizeMB"] = "N/A"

    # 僅將 public 模型添加到結果
    if model_info["Status"] == "public" and model_info["TotalSizeMB"] != "0.00":
        data.append(model_info)

# 轉換為 DataFrame
df = pd.DataFrame(data)

# # 按名稱排序（可選）
# df = df.sort_values(by="Name")

# 統計 public 模型數量
public_count = len(df)
print(f"Number of public models: {public_count}")

# 計算總檔案大小（轉換為 GB）
total_size_gb = total_size_mb / 1024
print(f"Total size of all public model weight files: {total_size_gb:.2f} GB")

# 模型總大小分布統計
# 僅對有效模型總大小進行分析
model_sizes = [size for size in model_sizes if size > 0]
bins = [0, 100, 500, 1000, 5000, float("inf")]
labels = ["0-100 MB", "100-500 MB", "500-1000 MB", "1000-5000 MB", ">5000 MB"]
size_distribution = pd.cut(model_sizes, bins=bins, labels=labels, include_lowest=True)
size_dist_counts = pd.Series(size_distribution).value_counts().sort_index()
print("\nModel size distribution for public models:")
for label, count in size_dist_counts.items():
    print(f"{label}: {count} models")

# 顯示 DataFrame
print("\nPublic model details:")
print(df)

# 保存到 CSV 文件，文件名包含當前日期
current_date = datetime.now().strftime("%Y%m%d")
df.to_csv(f"huggingface_top100_public_models.csv", index=False)
print(f"\nResults saved to huggingface_top100_public_models.csv")
