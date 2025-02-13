import json
import requests
from transformers import AutoModelForCausalLM, AutoTokenizer

# ---- 1. 選擇 Hugging Face 模型 ----
MODEL_NAME = "gpt2"

# ---- 2. 自動檢測 Hugging Face 模型資訊 ----
def get_huggingface_model_info(model_name):
    url = f"https://huggingface.co/api/models/{model_name}"
    response = requests.get(url)
    
    if response.status_code == 200:
        model_info = response.json()
        return {
            "model_name": model_info.get("modelId", "Unknown"),
            "source": f"https://huggingface.co/{model_name}",
            "license": model_info.get("license", "Unknown"),
            "library": model_info.get("library_name", "transformers"),
            "size": model_info.get("modelSize", "Unknown"),
            "tags": model_info.get("tags", [])
        }
    else:
        print(f"❌ 無法獲取 {model_name} 的資訊，請檢查模型名稱是否正確。")
        return None

model_metadata = get_huggingface_model_info(MODEL_NAME)

# ---- 3. 下載並載入模型 ----
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)

# ---- 4. 使用模型生成文字 ----
from transformers import pipeline
generator = pipeline("text-generation", model=model, tokenizer=tokenizer)

prompt = "Once upon a time"
output = generator(prompt, max_length=50, num_return_sequences=1)
generated_text = output[0]['generated_text']

print("\n🔹 AI 生成的文字：")
print(generated_text)

# ---- 5. 自動產生 AI BOM (ML-BOM) JSON ----
ml_bom = {
    "bomFormat": "CycloneDX",
    "specVersion": "1.5",
    "serialNumber": "urn:uuid:123e4567-e89b-12d3-a456-426614174000",
    "version": 1,
    "metadata": {
        "timestamp": "2025-02-13T00:00:00Z",
        "tools": [
            {
                "vendor": "CycloneDX",
                "name": "cyclonedx-cli",
                "version": "1.5"
            }
        ],
        "component": {
            "type": "application",
            "name": model_metadata["model_name"],
            "version": "1.0",
            "description": f"A pre-trained {model_metadata['model_name']} language generation model",
            "licenses": [
                {
                    "license": {
                        "id": model_metadata["license"]
                    }
                }
            ],
            "properties": [
                {"name": "model.framework", "value": model_metadata["library"]},
                {"name": "model.source", "value": model_metadata["source"]},
                {"name": "model.size", "value": str(model_metadata["size"])},
                {"name": "model.tags", "value": ", ".join(model_metadata["tags"])},
                {"name": "hardware.gpu", "value": "Not Required (Runs on CPU)"}
            ]
        }
    },
    "components": [
        {"type": "library", "name": "transformers", "version": "4.36.1", "purl": "pkg:pypi/transformers@4.36.1"},
        {"type": "library", "name": "torch", "version": "2.0.1", "purl": "pkg:pypi/torch@2.0.1"}
    ]
}

# ---- 6. 儲存 BOM 到 JSON 檔案 ----
with open("ml-bom.json", "w") as f:
    json.dump(ml_bom, f, indent=4)

print("\n✅ ML-BOM 已自動生成並儲存至 'ml-bom.json'")
