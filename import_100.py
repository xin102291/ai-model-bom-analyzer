import mysql.connector
import csv
import json
import os
import numpy as np
from transformers import AutoConfig
from huggingface_hub import HfApi, hf_hub_download
import torch
from safetensors.torch import load_file as load_safetensors
import shutil
from openvino.runtime import Core
from dotenv import load_dotenv


load_dotenv()

# MySQL 連線設定：從 .env 讀取（範本見 .env.example）
db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "testdb"),
}

# SQL 語句
insert_model_sql = """
INSERT INTO HF_model (model_account, model_name, model_type, model_architecture, layer_count, hidden_size, embedding_size, attention_heads, model_permissions, status)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE modify_time = CURRENT_TIMESTAMP, status = 1;

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

def get_weight_info_from_model(model):
    """使用 transformers 載入的模型計算權重資訊（model_information.py 版）"""
    state_dict = model.state_dict()
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

def load_openvino_weight_info(xml_path, bin_path):
    """使用 OpenVINO 讀取 IR 格式的模型權重資訊"""
    weight_details = []
    try:
        core = Core()
        model = core.read_model(model=xml_path, weights=bin_path)

        for op in model.get_ops():
            if not op.get_output_size():
                continue
            for idx, output in enumerate(op.outputs()):
                shape = list(output.get_shape())
                num_parameters = np.prod(shape) if shape else 0
                weight_details.append({
                    "layer_name": op.friendly_name,
                    "shape": shape,
                    "num_parameters": int(num_parameters),
                    "weight_mean": 0.0,
                    "weight_std": 0.0,
                    "min_value": 0.0,
                    "max_value": 0.0
                })

        return weight_details
    except Exception as e:
        print(f"❌ OpenVINO 模型處理失敗: {e}")
        return []


def get_weight_info(model_name, weight_file_path=None, token=None):
    """
    判斷是 transformers 模型還是 OpenVINO 權重，自動切換處理方式。
    """
    try:
        # 如果是 .bin 檔且有同名 .xml，使用 OpenVINO 方式
        if weight_file_path and weight_file_path.endswith(".bin"):
            xml_path = weight_file_path.replace(".bin", ".xml")
            if os.path.exists(xml_path):
                print("🧠 偵測到 OpenVINO 模型，使用 XML+BIN 處理")
                return load_openvino_weight_info(xml_path, weight_file_path)

        # 預設使用 transformers 模型載入方式
        print("🤗 使用 transformers 模型載入")
        from transformers import AutoModel
        model = AutoModel.from_pretrained(model_name, use_auth_token=token)
        return get_weight_info_from_model(model)

    except Exception as e:
        print(f"❌ 擷取權重資訊失敗：{e}")
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

def safe_json(value):
    if isinstance(value, (np.dtype, torch.dtype)):
        return str(value)
    if isinstance(value, (np.ndarray, torch.Tensor)):
        return value.tolist()
    return value

# 從 update_model_architecture_fields 複製過來
def safe_join_architecture(config):
    try:
        arch = getattr(config, "architectures", None)
        if isinstance(arch, (list, tuple)):
            return ", ".join(arch)
        elif isinstance(arch, str):
            return arch
        else:
            return "Unknown"
    except Exception:
        return "Unknown"

def get_model_fields(model_id, token=None):
    try:
        config = AutoConfig.from_pretrained(model_id, use_auth_token=token)
        config_dict = config.to_dict()
        if config.__class__.__name__ in ["CLIPConfig", "CLIPSegConfig", "SiglipConfig", "BlipConfig"]:
            return {
                "model_architecture": safe_join_architecture(config),
                "layer_count": getattr(config.text_config, "num_hidden_layers", None),
                "hidden_size": getattr(config.text_config, "hidden_size", None),
                "embedding_size": getattr(config.text_config, "hidden_size", None),
                "attention_heads": getattr(config.text_config, "num_attention_heads", None)
            }
        if config.__class__.__name__ == "VitMatteConfig":
            subcfg = getattr(config, "backbone_config", config_dict.get("backbone_config"))
            if subcfg:
                if not isinstance(subcfg, dict):
                    subcfg = subcfg.to_dict()
                return {
                    "model_architecture": safe_join_architecture(config),
                    "layer_count": subcfg.get("num_hidden_layers"),
                    "hidden_size": subcfg.get("hidden_size"),
                    "embedding_size": subcfg.get("hidden_size"),
                    "attention_heads": subcfg.get("num_attention_heads")
                }
        return {
            "model_architecture": safe_join_architecture(config),
            "layer_count": getattr(config, "num_hidden_layers", None),
            "hidden_size": getattr(config, "hidden_size", getattr(config, "n_embd", getattr(config, "d_model", None))),
            "embedding_size": getattr(config, "n_embd", getattr(config, "hidden_size", getattr(config, "d_model", None))),
            "attention_heads": getattr(config, "num_attention_heads", None)
        }
    except Exception as e:
        print(f"⚠️ get_model_fields 失敗：{model_id}，錯誤：{e}")
        return {
            "model_architecture": "Unknown",
            "layer_count": "Unknown",
            "hidden_size": "Unknown",
            "embedding_size": "Unknown",
            "attention_heads": "Unknown"
        }


def import_model_to_mysql(model_name, token=None):
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
        config = AutoConfig.from_pretrained(model_name, use_auth_token=token)
        model_type = getattr(config, "model_type", "Unknown")
        value = get_model_fields(model_name,token= token)
        model_architecture = value["model_architecture"]
        layer_count = value["layer_count"]
        hidden_size = value["hidden_size"]
        embedding_size = value["embedding_size"]
        attention_heads = value["attention_heads"]
        # model_architecture = ", ".join(getattr(config, "architectures", ["Unknown"]))
        # layer_count = str(getattr(config, "num_hidden_layers", "Unknown"))
        # hidden_size = str( getattr(config, "hidden_size", getattr(config, "n_embd", getattr(config, "d_model", "Unknown"))))
        # embedding_size = str( getattr(config, "n_embd", getattr(config, "hidden_size", getattr(config, "d_model", "Unknown"))))
        # attention_heads = str(getattr(config, "num_attention_heads", "Unknown"))

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
            model_architecture,
            layer_count,
            hidden_size,
            embedding_size,
            attention_heads,
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
            config = AutoConfig.from_pretrained(model_name, use_auth_token=token)
            hyperparameters = get_hyperparameters(config)
            for param in hyperparameters:
                # value = json.dumps(param["value"], ensure_ascii=False)
                value = json.dumps(safe_json(param["value"]), ensure_ascii=False)

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
                local_path = hf_hub_download(repo_id=model_name, filename=weight_file, cache_dir=cache_dir, token=token)

                # 提取權重資訊
                weight_details = get_weight_info(model_name, local_path ,token)

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
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
            print("✅ 資料庫連線已關閉")

if __name__ == "__main__":
    model_list = ["meta-llama/Llama-3.2-1B-Instruct"]
    HF_TOKEN = os.getenv("HF_TOKEN")  # 從 .env 讀取；只處理公開模型時可留空
    for i in model_list:
        import_model_to_mysql(i,token=HF_TOKEN)
    # csv_file = "huggingface_top100_public_models.csv"  # CSV 檔案名稱
    # start = 6  # 要處理的起始第幾筆（從 1 開始算）
    # end = 10    # 要處理的結束第幾筆（包含）

    # with open(csv_file, 'r', encoding='utf-8') as file:
    #     csv_reader = csv.reader(file)
    #     next(csv_reader)  # 跳過標題列

    #     for index, row in enumerate(csv_reader, start=1):
    #         if index < start:
    #             continue
    #         if index > end:
    #             break

    #         model_name = row[0]
    #         print(f"ℹ️ 正在處理第 {index} 筆模型: {model_name}")
    #         import_model_to_mysql(model_name)

    print("🎉 匯入完成！")