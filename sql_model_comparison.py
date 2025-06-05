import json
import mysql.connector
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# --- 資料庫設定 ---
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "REMOVED_PASSWORD",
    "database": "testdb",
}

# --- 載入未知模型 JSON ---
def load_unknown_model(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# --- 撈所有模型資訊（包含架構） ---
def load_known_models_from_db():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            id, model_account, model_name, model_type,
            model_architecture, layer_count, hidden_size,
            embedding_size, attention_heads
        FROM HF_model;
    """)
    models = cursor.fetchall()

    all_models = []
    for m in models:
        model_id = m["id"]
        model_data = {
            "name": f'{m["model_account"]}/{m["model_name"]}',
            "model_type": m.get("model_type"),
            "model_architecture": m.get("model_architecture"),
            "layer_count": m.get("layer_count"),
            "hidden_size": m.get("hidden_size"),
            "embedding_size": m.get("embedding_size"),
            "attention_heads": m.get("attention_heads"),
        }

        # 超參數
        cursor.execute("SELECT `key`, `value` FROM HF_model_hyperparameters WHERE model_id = %s", (model_id,))
        hparams = [{"key": row["key"], "value": json.loads(row["value"])} for row in cursor.fetchall()]
        model_data["hyperparameters"] = hparams

        # 權重摘要
        cursor.execute("""
            SELECT weight_mean, weight_std, min_value, max_value
            FROM HF_model_weights_details
            WHERE model_id = %s
        """, (model_id,))
        weights = [{
            "weight_mean": float(r["weight_mean"]),
            "weight_std": float(r["weight_std"]),
            "min_value": float(r["min_value"]),
            "max_value": float(r["max_value"])
        } for r in cursor.fetchall()]
        model_data["weights_info"] = {"layers": weights}

        all_models.append(model_data)

    cursor.close()
    conn.close()
    return all_models

# --- 特徵抽取（與原始邏輯相同）---
def extract_structure_features(data):
    keys = ['model_type', 'model_architecture', 'layer_count', 'hidden_size', 'embedding_size', 'attention_heads']
    features = []
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            value = value[0] if value else ''
        features.append(str(value))
    return features

def extract_hyperparam_features(data):
    keys = ['activation_function', 'initializer_range', 'hidden_dropout_prob', 'intermediate_size']
    hp_dict = {hp['key']: hp['value'] for hp in data.get('hyperparameters', [])}
    return [str(hp_dict.get(k, '')) for k in keys]

def extract_weight_fingerprint(data):
    layers = data.get('weights_info', {}).get('layers', [])
    fp = []
    for l in layers:
        fp.extend([l['weight_mean'], l['weight_std'], l['min_value'], l['max_value']])
    return np.array(fp)

# --- 相似度與分數計算（原始邏輯）---
def structure_score(a, b):
    return sum([1 for x, y in zip(a, b) if x == y]) / len(a)

def hyperparam_score(a, b):
    return sum([1 for x, y in zip(a, b) if x == y]) / len(a)

def weight_similarity(fp1, fp2):
    min_len = min(len(fp1), len(fp2))
    if min_len == 0:
        return 0.0
    fp1_crop = fp1[:min_len]
    fp2_crop = fp2[:min_len]
    return cosine_similarity([fp1_crop], [fp2_crop])[0][0]

def compute_final_score(structure_sim, hyper_sim, weight_sim):
    return round(structure_sim * 0.3 + hyper_sim * 0.2 + weight_sim * 0.5, 6)

# --- 主比對流程 ---
def match_top_n_from_db(unknown_data, known_models, top_n=3):
    u_struct = extract_structure_features(unknown_data)
    u_hparam = extract_hyperparam_features(unknown_data)
    u_fp = extract_weight_fingerprint(unknown_data)

    results = []
    for known in known_models:
        k_struct = extract_structure_features(known)
        k_hparam = extract_hyperparam_features(known)
        k_fp = extract_weight_fingerprint(known)

        s_score = structure_score(u_struct, k_struct)
        h_score = hyperparam_score(u_hparam, k_hparam)
        w_score = weight_similarity(u_fp, k_fp)

        final = compute_final_score(s_score, h_score, w_score)

        results.append({
            'name': known["name"],
            'structure': s_score,
            'hyperparam': h_score,
            'weight_sim': round(w_score, 6),
            'final_score': final
        })

    top_matches = sorted(results, key=lambda x: x['final_score'], reverse=True)[:top_n]
    return top_matches

# --- 主程式 ---
if __name__ == "__main__":
    unknown_path = "test\EleutherAI_gpt-neo-1.3B_info.json"  # ← 改成你的檔案路徑

    print("🔍 載入未知模型...")
    unknown = load_unknown_model(unknown_path)

    print("📦 從資料庫讀取模型資料...")
    known_models = load_known_models_from_db()

    print("🧠 執行比對...")
    matches = match_top_n_from_db(unknown, known_models)

    print("\n🎯 Top 3 最相似模型：")
    for i, m in enumerate(matches):
        print(f"\n#{i+1}: {m['name']}")
        print(f"   ➤ Structure Match:   {m['structure']}")
        print(f"   ➤ Hyperparam Match:  {m['hyperparam']}")
        print(f"   ➤ Weight Similarity: {m['weight_sim']}")
        print(f"   ✅ Final Score:       {m['final_score']}")
