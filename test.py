import json
import requests
from transformers import AutoModel, AutoTokenizer
import torch.hub

def detect_model_source(model_id):
    """自動判斷模型來自 Hugging Face、TensorFlow Hub、PyTorch Hub、ONNX Model Zoo 或 Google Research Models"""
    
    # 檢查 Hugging Face
    hf_url = f"https://huggingface.co/api/models/{model_id}"
    response = requests.get(hf_url)
    if response.status_code == 200:
        return "huggingface", hf_url
    
    # 檢查 TensorFlow Hub
    tfhub_url = f"https://tfhub.dev/s?search={model_id}"
    response = requests.get(tfhub_url)
    if response.status_code == 200 and model_id in response.text:
        return "tensorflow_hub", tfhub_url
    
    # 檢查 PyTorch Hub
    try:
        available_models = torch.hub.list("pytorch/vision")
        if model_id in available_models:
            return "pytorch_hub", "https://pytorch.org/hub/"
    except Exception:
        pass
    
    # 檢查 ONNX Model Zoo
    onnx_url = "https://github.com/onnx/models"
    response = requests.get(onnx_url)
    if response.status_code == 200 and model_id in response.text:
        return "onnx_model_zoo", onnx_url
    
    # 檢查 Google Research Models
    google_models_url = "https://github.com/google-research/google-research"
    response = requests.get(google_models_url)
    if response.status_code == 200 and model_id in response.text:
        return "google_research", google_models_url
    
    return None, None

def generate_ml_bom(model_id, source, source_url):
    """根據模型來源生成 AI BOM (ML-BOM)"""
    ml_bom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "metadata": {
            "component": {
                "name": model_id,
                "source": source_url,
                "properties": [
                    {"name": "model.source", "value": source},
                    {"name": "model.url", "value": source_url}
                ]
            }
        }
    }
    return ml_bom

if __name__ == "__main__":
    model_id = input("請輸入模型 ID: ")
    source, source_url = detect_model_source(model_id)
    
    if source:
        print(f"模型來自: {source} ({source_url})")
        ml_bom = generate_ml_bom(model_id, source, source_url)
        with open(f"{model_id}.json", "w") as f:
            json.dump(ml_bom, f, indent=4)
        print(f"✅ ML-BOM 已儲存至 {model_id}.json")
    else:
        print("❌ 無法識別模型來源，請確認模型 ID 是否正確")
