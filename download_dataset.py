from datasets import load_dataset

# 下載 OpenWebText，允許執行遠端代碼
dataset = load_dataset("openwebtext", trust_remote_code=True)

# 儲存到本地
dataset.save_to_disk("./openwebtext_dataset")

print("OpenWebText 資料集已下載並儲存到 ./openwebtext_dataset")
