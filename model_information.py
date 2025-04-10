import torch
import requests
from transformers import AutoConfig, AutoModel
import json
import time
import numpy as np
from huggingface_hub import HfApi
# 取得模型資訊
def get_model_info(model_name):
    """
    取得 Hugging Face 模型的 AI BOM 資訊，包括模型架構、權重資訊等。
    """
    try:
        # 載入模型配置與權重
        config = AutoConfig.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name)

        # 提取超參數
        hyperparameters = get_hyperparameters(config)

        # 讀取權重資訊
        weight_info = get_weight_info(model)
        # 資料集資訊
        dataset_info = get_dataset_info(model_name)
        # 動態提取下載位置
        download_url = f"https://huggingface.co/{model_name}/resolve/main/{config._name_or_path}.bin"

        # 整理 AI BOM 資訊
        info = {
            "type": "ai_AIPackage",
            "spdxId": f"https://huggingface.co/{model_name}",
            "creationInfo": "_:creationinfo",
            "name": model_name,
            "releaseTime": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "suppliedBy": f"https://huggingface.co/{model_name}",
            "software_downloadLocation": download_url,
            "software_packageVersion": "2.0",
            "training_datasets": dataset_info,
            "software_primaryPurpose": "Define yourself",
            "comment": "Define yourself",
            "ai_autonomyType": "no",
            "ai_domain": ["Define yourself"],
            "model_version": config.model_type,
            "model_architecture": config.architectures if hasattr(config, "architectures") else ["Unknown"],
            "layer_count": str(config.num_hidden_layers) if hasattr(config, "num_hidden_layers") else "Unknown",
            "embedding_size": str(config.hidden_size) if hasattr(config, "hidden_size") else "Unknown",
            "attention_heads": str(config.num_attention_heads) if hasattr(config, "num_attention_heads") else "Unknown",
            "activation_function": config.activation_function if hasattr(config, "activation_function") else "Unknown",
            "hyperparameters": hyperparameters,
            "weights_info": weight_info,  # 新增的權重資訊
        }

        return info

    except Exception as e:
        return {"錯誤": f"無法載入模型 {model_name}: {str(e)}"}

# 新增：提取資料集
def get_dataset_info(model_name):
    try:
        api = HfApi()
        model_info = api.model_info(model_name)
        dataset_tag = model_info.cardData.get("datasets") if model_info.cardData else None
        if isinstance(dataset_tag, list):
            return dataset_tag
        elif isinstance(dataset_tag, str):
            return [dataset_tag]
        else:
            return ["Unknown"]
    except Exception as e:  # ← 通用錯誤處理
        return [f"Failed to retrieve dataset info: {str(e)}"]

def get_hyperparameters(config):
    """
    提取並返回配置文件中的超參數。
    """
    return [
        {"key": key, "value": getattr(config, key)}
        for key in dir(config)
        if not key.startswith("__") and not callable(getattr(config, key))
    ]

def get_weight_info(model):
    """
    讀取 PyTorch 模型的權重資訊，包括參數數量、權重維度、數值範圍。
    """
    # 讀取模型權重
    state_dict = model.state_dict()
    # 計算總參數數量
    total_params = sum(p.numel() for p in state_dict.values())
    # 整理權重詳細資訊
    weight_details = []
    # 遍歷所有權重
    for name, param in state_dict.items():
        # 將權重轉換為 NumPy 陣列
        param_numpy = param.cpu().detach().numpy()
        # 計算權重平均值、標準差、最小值和最大值
        weight_details.append({
            "layer_name": name,
            "shape": param.shape,
            "num_parameters": param.numel(),
            "weight_mean": np.mean(param_numpy),
            "weight_std": np.std(param_numpy),
            "min_value": np.min(param_numpy),
            "max_value": np.max(param_numpy),
        })
    # 返回總參數數量和權重詳細資訊
    return {
        "total_parameters": total_params,
        "layers": weight_details
    }



# 測試不同的模型
model_names = ["tiiuae/falcon-7b", "gpt2", "bert-base-uncased", "google/mobilebert-uncased", "albert-base-v2", "google/electra-small-discriminator", "microsoft/Phi-3-mini-4k-instruct"]

for model_name in model_names:
    model_info = get_model_info(model_name)

    # 產生 JSON 檔案
    json_filename = f"bom/{model_name.replace('/', '_')}_info.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(model_info, f, ensure_ascii=False, indent=4, default=str)


    print(f"已產生 {json_filename}")
