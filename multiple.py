import torch
import numpy as np
import hashlib
import scipy.stats
import tensorflow_hub as hub
import onnxruntime as ort
from scipy.spatial.distance import cosine
from transformers import AutoModel
import torch.hub

# 🔹 1. 從 Hugging Face 載入 Transformer 模型
def load_model_from_huggingface(model_name):
    return AutoModel.from_pretrained(model_name)

# 🔹 2. 從 TensorFlow Hub 載入模型
def load_model_from_tensorflow_hub(model_url):
    return hub.load(model_url)

# 🔹 3. 從 PyTorch Hub 載入模型
def load_model_from_pytorch_hub(model_name, repo="pytorch/vision"):
    return torch.hub.load(repo, model_name, pretrained=True)

# 🔹 4. 從 ONNX Model Zoo 載入 ONNX 模型
def load_model_from_onnx(model_path):
    return ort.InferenceSession(model_path)

# 🔹 5. 統一處理不同來源的模型
def load_model(model_id, source):
    if source == "huggingface":
        return load_model_from_huggingface(model_id)
    elif source == "tensorflow_hub":
        return load_model_from_tensorflow_hub(model_id)
    elif source == "pytorch_hub":
        return load_model_from_pytorch_hub(model_id)
    elif source == "onnx":
        return load_model_from_onnx(model_id)
    else:
        raise ValueError("❌ 不支援的模型來源！")

# 🔹 6. 比對模型架構
def compare_model_architecture(model_a, model_b):
    layers_a = [layer.__class__.__name__ for layer in model_a.children()]
    layers_b = [layer.__class__.__name__ for layer in model_b.children()]
    
    common_layers = sum(1 for la, lb in zip(layers_a, layers_b) if la == lb)
    total_layers = max(len(layers_a), len(layers_b))
    
    return common_layers / total_layers if total_layers > 0 else 0

# 🔹 7. 比對模型權重
def compare_model_weights(model_a, model_b):
    weights_a = torch.cat([param.flatten() for param in model_a.state_dict().values()]).cpu().numpy()
    weights_b = torch.cat([param.flatten() for param in model_b.state_dict().values()]).cpu().numpy()

    l2_distance = np.linalg.norm(weights_a - weights_b)
    cosine_similarity = 1 - cosine(weights_a, weights_b)

    return l2_distance, cosine_similarity

# 🔹 8. 比對權重分布
def compare_weight_distribution(model_a, model_b):
    weights_a = torch.cat([param.flatten() for param in model_a.state_dict().values()]).cpu().numpy()
    weights_b = torch.cat([param.flatten() for param in model_b.state_dict().values()]).cpu().numpy()

    mean_diff = abs(np.mean(weights_a) - np.mean(weights_b))
    std_diff = abs(np.std(weights_a) - np.std(weights_b))

    hist_a, _ = np.histogram(weights_a, bins=50, density=True)
    hist_b, _ = np.histogram(weights_b, bins=50, density=True)

    emd_distance = scipy.stats.wasserstein_distance(hist_a, hist_b)

    return mean_diff, std_diff, emd_distance

# 🔹 9. 計算模型哈希
def hash_model_weights(model):
    weights = torch.cat([param.flatten() for param in model.state_dict().values()]).cpu().numpy()
    return hashlib.sha256(weights.tobytes()).hexdigest()

# 🔹 10. 綜合比對，返回所有可能的來源
def determine_multiple_sources(model, candidate_sources, threshold=0.5):
    similarity_scores = {}

    for source, candidate_model in candidate_sources.items():
        arch_score = compare_model_architecture(model, candidate_model)
        l2_dist, cos_sim = compare_model_weights(model, candidate_model)
        mean_diff, std_diff, emd_dist = compare_weight_distribution(model, candidate_model)

        # 綜合評分（0~1，越高越相似）
        score = (arch_score * 0.4) + ((1 - l2_dist) * 0.2) + (cos_sim * 0.2) + ((1 - emd_dist) * 0.2)
        similarity_scores[source] = score

    # 篩選所有相似度 > threshold（可能來自多個來源）
    possible_sources = {src: score for src, score in similarity_scores.items() if score > threshold}

    return dict(sorted(possible_sources.items(), key=lambda x: x[1], reverse=True)) if possible_sources else {"未知來源": 0.0}

# 🔹 11. 測試：載入多個來源的模型
if __name__ == "__main__":
    # 測試目標模型（來自 Hugging Face）
    target_model = load_model("bert-base-uncased", "huggingface")

    # 候選來源模型（來自多個不同的來源）
    candidate_models = {
        "Hugging Face: bert-base-uncased": load_model("bert-base-uncased", "huggingface"),
        "Hugging Face: gpt2": load_model("gpt2", "huggingface"),
        "TensorFlow Hub: universal-sentence-encoder": load_model("https://tfhub.dev/google/universal-sentence-encoder/4", "tensorflow_hub"),
        "PyTorch Hub: resnet18": load_model("resnet18", "pytorch_hub"),
        "ONNX Model Zoo: resnet50": load_model("resnet50.onnx", "onnx"),
    }

    # 執行來源比對
    results = determine_multiple_sources(target_model, candidate_models)

    # 輸出比對結果
    print("\n🔍 來源比對結果：")
    for source, score in results.items():
        print(f"{source}: {score:.2f}")
