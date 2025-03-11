import json
import time
from transformers import AutoConfig, AutoModel

def get_model_info(model_name):
    """
    根據 Hugging Face 的模型名稱自動提取 AI BOM 所需的模型資訊。
    """
    try:
        # 載入模型配置
        config = AutoConfig.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name)

        # 提取超參數
        hyperparameters = get_hyperparameters(config)

        # 動態提取下載位置
        download_url = f"https://huggingface.co/{model_name}/resolve/main/{config._name_or_path}.bin"

        # 自動提取所有關鍵資訊
        info = {
            "type": "ai_AIPackage",
            "spdxId": f"https://huggingface.co/{model_name}",
            "creationInfo": "_:creationinfo",
            "name": model_name,
            "releaseTime": time.strftime("%Y-%m-%dT%H:%M:%SZ"),  # 使用當前時間作為發佈時間
            "suppliedBy": f"https://huggingface.co/{model_name}",
            "software_downloadLocation": download_url,
            "software_packageVersion": "2.0",  # 依需求調整版本
            "software_primaryPurpose": "Define yourself",  # 依模型用途調整
            "comment": "Define yourself",
            "ai_autonomyType": "no",
            "ai_domain": [
                "Define yourself"
            ],
            "model_version": config.model_type,  # 模型的版本類型
            "model_architecture": config.architectures if hasattr(config, "architectures") else ["Unknown"],  # 直接從 config 讀取架構
            "layer_count": str(config.num_hidden_layers) if hasattr(config, "num_hidden_layers") else "Unknown",  # 層數
            "embedding_size": str(config.hidden_size) if hasattr(config, "hidden_size") else "Unknown",  # 嵌入層大小
            "attention_heads": str(config.num_attention_heads) if hasattr(config, "num_attention_heads") else "Unknown",  # 注意力頭數
            "activation_function": config.activation_function if hasattr(config, "activation_function") else "Unknown",  # 激活函數
            "hyperparameters": hyperparameters,  # 自動提取的超參數
        }

        return info

    except Exception as e:
        return {"錯誤": f"無法載入模型 {model_name}: {str(e)}"}

def get_hyperparameters(config):
    """
    提取並返回配置文件中的超參數。
    """
    return [
        {"key": key, "value": getattr(config, key)}
        for key in dir(config)
        if not key.startswith("__") and not callable(getattr(config, key))  # 排除特殊方法和可呼叫的屬性
    ]

# 測試不同的模型
model_names = ["gpt2", "bert-base-uncased"]

for model_name in model_names:
    model_info = get_model_info(model_name)
    
    # 產生 JSON 檔案
    json_filename = f"{model_name.replace('/', '_')}_info.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(model_info, f, ensure_ascii=False, indent=4)
    
    print(f"已產生 {json_filename}")
