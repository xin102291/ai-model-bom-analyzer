import json
import uuid
from datetime import datetime

def get_input(prompt, default=None):
    value = input(f"{prompt} (預設: {default}): ")
    return value if value else default

def generate_spdx_json():
    ai_bom = {
        "spdxId": str(uuid.uuid4()),  # 自動生成唯一 SPDX ID
        "name": get_input("請輸入 AI 模型名稱", "GPT-2"),
        "packageVersion": get_input("請輸入模型版本", "1.5"),
        "downloadLocation": get_input("請輸入下載位置", "https://github.com/openai/gpt-2"),
        "primaryPurpose": get_input("請輸入主要用途", "自然語言處理 (NLP)"),
        "releaseTime": get_input("請輸入發布時間 (YYYY-MM-DD)", "2019-02-14"),
        "buildTime": get_input("請輸入建置時間 (YYYY-MM-DD)", datetime.now().strftime('%Y-%m-%d')),
        "suppliedBy": get_input("請輸入供應者資訊", "OpenAI"),
        "hasConcludedLicense": get_input("請輸入確定的授權類型", "MIT License"),
        "hasDeclaredLicense": get_input("請輸入聲明的授權類型", "MIT License")
    }
    
    file_name = f"ai_bom_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(ai_bom, f, indent=4, ensure_ascii=False)
    
    print(f"✅ AI BOM JSON 已生成：{file_name}")

if __name__ == "__main__":
    generate_spdx_json()
