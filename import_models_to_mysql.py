import mysql.connector
import json
import os
import numpy as np
from transformers import AutoConfig
from huggingface_hub import HfApi, hf_hub_download
import torch
from safetensors.torch import load_file as load_safetensors
import shutil

# MySQL 連線設定
db_config = {
    "host": "localhost",
    "user": "root",  # 請替換為你的 MySQL 使用者名稱
    "password": "REMOVED_PASSWORD",  # 請替換為你的 MySQL 密碼
    "database": "testdb"
}

# SQL 語句
insert_model_sql = """
INSERT INTO HF_model (model_account, model_name, model_type, model_permissions, status)
VALUES (%s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE modify_time = CURRENT_TIMESTAMP, status = 1
"""

insert_hyperparameter_sql = """
INSERT INTO HF_model_hyperparameters (model_id, `key`, `value`)
VALUES (%s, %s, %s)
"""

insert_weight_sql = """
INSERT INTO HF_model_weights_details (model_id, layer_name, shape, num_parameters, weight_mean, weight_std, min_value, max_value)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""

def get_model_id(cursor, model_account, model_name):
    """從 HF_model 資料表取得模型 ID"""
    cursor.execute("SELECT id FROM HF_model WHERE model_account = %s AND model_name = %s", 
                   (model_account, model_name))
    result = cursor.fetchone()
    return result[0] if result else None

def get_hyperparameters(config):
    """提取模型配置中的超參數"""
    return [
        {"key": key, "value": getattr(config, key)}
        for key in dir(config)
        if not key.startswith("__") and not callable(getattr(config, key))
    ]

def get_weight_info(weight_file_path, file_type):
    """從權重檔案提取資訊"""
    try:
        # 根據檔案類型載入權重
        if file_type.endswith(('.bin', '.pt', '.pth')):
            state_dict = torch.load(weight_file_path, map_location='cpu', weights_only=True)
        elif file_type.endswith('.safetensors'):
            state_dict = load_safetensors(weight_file_path)
        else:
            raise ValueError(f"不支援的檔案格式: {file_type}")

        weight_details = []
        for name, param in state_dict.items():
            param_numpy = param.cpu().detach().numpy()
            weight_details.append({
                "layer_name": name,
                "shape": list(param.shape),
                "num_parameters": param.numel(),
                "weight_mean": float(np.mean(param_numpy)),
                "weight_std": float(np.std(param_numpy)),
                "min_value": float(np.min(param_numpy)),
                "max_value": float(np.max(param_numpy))
            })
        return weight_details
    except Exception as e:
        print(f"❌ 處理權重檔案 {weight_file_path} 時發生錯誤: {e}")
        return []

def delete_model_cache(model_name, cache_dir):
    """刪除模型的快取資料夾"""
    model_dir = os.path.join(cache_dir, "models--" + model_name.replace("/", "--"))
    if os.path.exists(model_dir):
        shutil.rmtree(model_dir)
        print(f"✅ 已刪除快取資料夾: {model_dir}")
    else:
        print(f"ℹ️ 快取資料夾不存在: {model_dir}")

def determine_model_type(weight_files):
    """根據特定權重檔案副檔名推斷模型框架類型"""
    for weight_file in weight_files:
        if weight_file.endswith('.gguf'):
            return "ggml"
        elif weight_file.endswith(('.safetensors', '.pt', '.pth', '.bin')):
            return "pytorch"
    return "unknown"

def import_model_to_mysql(model_name):
    """將單一模型的資料匯入資料庫"""
    # 連線到 MySQL
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ 資料庫連線失敗: {e}")
        return

    # 拆解 model_account 和 model_name
    if "/" in model_name:
        model_account, model_name_split = model_name.split("/", 1)
    else:
        model_account, model_name_split = "unknown", model_name

    try:
        # 步驟 1: 取得模型類型和權限
        api = HfApi()
        model_info = api.model_info(model_name)
        model_type = model_info.config.get("model_type", "N/A") if model_info.config else "N/A"
        model_permissions = "public"  # 預設為 public
        if model_info.gated:
            model_permissions = "gated"
        elif model_info.private:
            model_permissions = "private"

        # 取得權重檔案清單並推斷 model_type
        files = [f.rfilename for f in model_info.siblings]
        weight_files = [f for f in files if f.endswith(('.bin', '.safetensors', '.pt', '.pth', '.gguf', '.h5'))]
        model_type = determine_model_type(weight_files)

        # 步驟 2: 插入 HF_model
        cursor.execute(insert_model_sql, (
            model_account,
            model_name_split,
            model_type,
            model_permissions,
            0  # 初始 status 為 0
        ))
        conn.commit()
        print(f"✅ 已插入/更新 {model_name} 到 HF_model")

        # 步驟 3: 取得 model_id
        model_id = get_model_id(cursor, model_account, model_name_split)
        if not model_id:
            print(f"❌ 無法取得 {model_name} 的 model_id")
            return

        # 步驟 4: 提取超參數
        try:
            config = AutoConfig.from_pretrained(model_name)
            hyperparameters = get_hyperparameters(config)
            for param in hyperparameters:
                value = json.dumps(param["value"], ensure_ascii=False)
                cursor.execute(insert_hyperparameter_sql, (model_id, param["key"], value))
            conn.commit()
            print(f"✅ 已插入 {len(hyperparameters)} 個超參數到 {model_name}")
        except Exception as e:
            print(f"❌ 提取 {model_name} 超參數時發生錯誤: {e}")

        # 步驟 5: 下載並處理權重檔案
        try:
            files = [f.rfilename for f in model_info.siblings]
            weight_files = [f for f in files if f.endswith(('.bin', '.safetensors', '.pt', '.pth', '.gguf'))]
            
            for weight_file in weight_files:
                print(f"ℹ️ 正在下載權重檔案: {weight_file}")
                cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
                local_path = hf_hub_download(repo_id=model_name, filename=weight_file, cache_dir=cache_dir)
                
                # 提取權重資訊
                weight_details = get_weight_info(local_path, weight_file)
                for layer in weight_details:
                    shape = json.dumps(layer["shape"], ensure_ascii=False)
                    cursor.execute(insert_weight_sql, (
                        model_id,
                        layer["layer_name"],
                        shape,
                        layer["num_parameters"],
                        layer["weight_mean"],
                        layer["weight_std"],
                        layer["min_value"],
                        layer["max_value"]
                    ))
                conn.commit()
                print(f"✅ 已插入 {len(weight_details)} 個權重資訊到 {model_name} (檔案: {weight_file})")

                # 刪除下載的權重檔案
                if os.path.exists(local_path):
                    os.remove(local_path)
                    print(f"✅ 已刪除權重檔案: {local_path}")

            # 清除快取資料夾
            delete_model_cache(model_name, cache_dir)

        except Exception as e:
            print(f"❌ 處理 {model_name} 權重檔案時發生錯誤: {e}")

    except Exception as e:
        print(f"❌ 處理 {model_name} 時發生錯誤: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
            print("✅ 資料庫連線已關閉")

if __name__ == "__main__":
    test_model = "Bingsu/adetailer"
    import_model_to_mysql(test_model)
    print("🎉 匯入完成！")