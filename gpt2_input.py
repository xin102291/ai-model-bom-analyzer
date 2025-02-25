import json
import uuid
from datetime import datetime

def get_input(prompt, default=None):
    value = input(f"{prompt} (預設: {default}): ")
    return value if value else default

def generate_spdx_json():
    spdx_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
    
    spdx_data = {
        "spdxVersion": "SPDX-3.0",
        "SPDXID": f"SPDXRef-{spdx_id}",
        "creationInfo": {
            "created": timestamp,
            "creators": [
                "Tool: AI-BOM-Generator-1.0"
            ]
        },
        "packages": [
            {
                "SPDXID": "SPDXRef-AIModel",
                "name": get_input("請輸入 AI 模型名稱", "GPT-2"),
                "versionInfo": get_input("請輸入模型版本", "1.5"),
                "downloadLocation": get_input("請輸入下載位置", "https://github.com/openai/gpt-2"),
                "primaryPurpose": get_input("請輸入主要用途", "自然語言處理 (NLP)"),
                "releaseTime": get_input("請輸入發布時間 (YYYY-MM-DD)", "2019-02-14"),
                "buildTime": get_input("請輸入建置時間 (YYYY-MM-DD)", datetime.now().strftime('%Y-%m-%d')),
                "supplier": get_input("請輸入供應者資訊", "OpenAI"),
                "licenseConcluded": get_input("請輸入確定的授權類型", "MIT License"),
                "licenseDeclared": get_input("請輸入聲明的授權類型", "MIT License")
            }
        ],
        "files": [
            {
                "SPDXID": "SPDXRef-Dataset",
                "fileName": get_input("請輸入資料集名稱", "OpenWebText2"),
                "downloadLocation": get_input("請輸入資料集下載位置", "https://github.com/EleutherAI/openwebtext2"),
                "fileLicenseConcluded": get_input("請輸入資料集授權類型", "Unknown (需確認 OpenWebText2 授權)"),
                "fileLicenseDeclared": get_input("請輸入資料集授權類型", "Unknown (需確認 OpenWebText2 授權)")
            }
        ],
        "relationships": [
            {
                "spdxElementId": "SPDXRef-AIModel",
                "relatedSpdxElement": "SPDXRef-Dataset",
                "relationshipType": "GENERATES"
            }
        ]
    }
    
    file_name = f"spdx_ai_bom_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(spdx_data, f, indent=4, ensure_ascii=False)
    
    print(f"✅ SPDX 3.0 AI BOM JSON 已生成：{file_name}")

if __name__ == "__main__":
    generate_spdx_json()
