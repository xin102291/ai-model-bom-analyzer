import os
import mysql.connector
from transformers import AutoConfig
from dotenv import load_dotenv
from huggingface_hub import hf_hub_download
import json

load_dotenv()

# MySQL 連線設定：從 .env 讀取（範本見 .env.example）
db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "testdb"),
}
# 安全 join model_architecture
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

# 主函數：取得欄位值（AutoConfig or raw config.json）
def get_model_fields(model_id):
    # 嘗試使用 transformers 的 AutoConfig
    try:
        config = AutoConfig.from_pretrained(model_id)
        config_dict = config.to_dict()
        # 特別處理：CLIPConfig 類型
        if config.__class__.__name__ in ["CLIPConfig", "CLIPSegConfig", "SiglipConfig", "BlipConfig"]:
            return {
                "model_architecture": safe_join_architecture(config),
                "layer_count": getattr(config.text_config, "num_hidden_layers", None),  # 用文字編碼器代表主結構
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

        # 正常處理其他架構
        return {
            "model_architecture": safe_join_architecture(config),
            "layer_count": getattr(config, "num_hidden_layers", None),
            "hidden_size": getattr(config, "hidden_size", getattr(config, "n_embd", getattr(config, "d_model", None))),
            "embedding_size": getattr(config, "n_embd", getattr(config, "hidden_size", getattr(config, "d_model", None))),
            "attention_heads": getattr(config, "num_attention_heads", None)
        }
    except Exception as e:
        print(f"⚠️ AutoConfig 失敗：{model_id}，錯誤：{e}")

# 查找需要補欄位的模型
def get_models_to_update(cursor):
    query = """
    SELECT model_account, model_name 
    FROM HF_model 
    WHERE model_architecture IS NULL OR model_architecture = ''
       OR layer_count IS NULL OR layer_count = 0
       OR hidden_size IS NULL OR hidden_size = 0
       OR embedding_size IS NULL OR embedding_size = 0
       OR attention_heads IS NULL OR attention_heads = 0
    """
    cursor.execute(query)
    return cursor.fetchall()

# 執行更新
def update_model_info(cursor, model_account, model_name, values):
    query = """
    UPDATE HF_model
    SET model_architecture = %s,
        layer_count = %s,
        hidden_size = %s,
        embedding_size = %s,
        attention_heads = %s,
        modify_time = CURRENT_TIMESTAMP
    WHERE model_account = %s AND model_name = %s
    """
    cursor.execute(query, (
        values["model_architecture"],
        values["layer_count"],
        values["hidden_size"],
        values["embedding_size"],
        values["attention_heads"],
        model_account,
        model_name
    ))

# 主程式
def main():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        models = get_models_to_update(cursor)
        print(f"🔍 共 {len(models)} 筆模型需要補欄位")

        for model_account, model_name in models:
            full_model_id = f"{model_account}/{model_name}" if model_account != "unknown" else model_name
            print(f"➡️ 更新 {full_model_id}")

            values = get_model_fields(full_model_id)
            if values is None:
                print(f"⚠️ 跳過：無法取得欄位資料")
                continue

            try:
                update_model_info(cursor, model_account, model_name, values)
                conn.commit()
                print(f"✅ 補完：{full_model_id}")
            except Exception as e:
                print(f"❌ 資料庫更新失敗：{full_model_id}，錯誤：{e}")

    except Exception as e:
        print(f"❌ 無法連接資料庫：{e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
            print("🔚 資料庫連線已關閉")

if __name__ == "__main__":
    main()
