import os
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# --- 基本功能 ---
def load_model_json(json_path):
    with open(json_path, 'r') as f:
        return json.load(f)

# --- 結構特徵抽取 ---
def extract_structure_features(data):
    keys = ['model_type', 'model_architecture', 'layer_count', 'hidden_size', 'embedding_size', 'attention_heads']
    features = []
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            value = value[0] if value else ''
        features.append(str(value))
    return features

# --- 超參數抽取 ---
def extract_hyperparam_features(data):
    target_keys = ['activation_function', 'initializer_range', 'hidden_dropout_prob', 'intermediate_size']
    hp_dict = {hp['key']: hp['value'] for hp in data.get('hyperparameters', [])}
    features = []
    for key in target_keys:
        value = hp_dict.get(key, '')
        features.append(str(value))
    return features

# --- 權重特徵抽取 ---
def extract_weight_fingerprint(data):
    layers = data.get('weights_info', {}).get('layers', [])
    fp = []
    for layer in layers:
        mean = float(layer['weight_mean'])
        std = float(layer['weight_std'])
        min_val = float(layer['min_value'])
        max_val = float(layer['max_value'])
        fp.extend([mean, std, min_val, max_val])
    return np.array(fp)

# --- 結構與超參數比對（相同加分） ---
def structure_score(a, b):
    return sum([1 for x, y in zip(a, b) if x == y]) / len(a)

def hyperparam_score(a, b):
    return sum([1 for x, y in zip(a, b) if x == y]) / len(a)

# --- 權重比對（Cosine Similarity） ---
def weight_similarity(fp1, fp2):
    min_len = min(len(fp1), len(fp2))
    if min_len == 0:
        return 0.0
    fp1_crop = fp1[:min_len]
    fp2_crop = fp2[:min_len]
    return cosine_similarity([fp1_crop], [fp2_crop])[0][0]

# --- 綜合比對分數 ---
def compute_final_score(structure_sim, hyper_sim, weight_sim):
    return round(structure_sim * 0.3 + hyper_sim * 0.2 + weight_sim * 0.5, 6)

# --- 比對主流程 ---
def match_top_n(unknown_path, known_dir, top_n=3):
    unknown = load_model_json(unknown_path)
    u_struct = extract_structure_features(unknown)
    u_hparam = extract_hyperparam_features(unknown)
    u_fp = extract_weight_fingerprint(unknown)

    results = []

    for fname in os.listdir(known_dir):
        if not fname.endswith('_info.json'):
            continue
        k_path = os.path.join(known_dir, fname)
        known = load_model_json(k_path)

        k_struct = extract_structure_features(known)
        k_hparam = extract_hyperparam_features(known)
        k_fp = extract_weight_fingerprint(known)

        s_score = structure_score(u_struct, k_struct)
        h_score = hyperparam_score(u_hparam, k_hparam)
        w_score = weight_similarity(u_fp, k_fp)

        final = compute_final_score(s_score, h_score, w_score)

        results.append({
            'name': known.get('name', fname),
            'file': fname,
            'structure': s_score,
            'hyperparam': h_score,
            'weight_sim': round(w_score, 6),
            'final_score': final
        })

    top_matches = sorted(results, key=lambda x: x['final_score'], reverse=True)[:top_n]
    return top_matches

# --- 執行範例 ---
if __name__ == '__main__':
    unknown_model_path = 'prajjwal1_bert-tiny_info.json'         # 你的未知模型檔
    known_models_dir = './bom/'                       # 存放已知模型 JSON 的資料夾

    matches = match_top_n(unknown_model_path, known_models_dir)
    
    print("\n🔍 Top 3 Similar Models:")
    for i, m in enumerate(matches):
        print(f"#{i+1}: {m['name']} ({m['file']})")
        print(f"   ➤ Structure Match:   {m['structure']}")
        print(f"   ➤ Hyperparam Match:  {m['hyperparam']}")
        print(f"   ➤ Weight Similarity: {m['weight_sim']}")
        print(f"   ✅ Final Score:       {m['final_score']}")
        print("---")