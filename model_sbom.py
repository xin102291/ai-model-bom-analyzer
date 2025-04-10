import json
import subprocess
from transformers import AutoModel, AutoConfig
from cyclonedx.model.bom import Bom
from cyclonedx.model.component import Component
from cyclonedx.output import get_instance, BaseOutput, OutputFormat

def generate_sbom(model_name, output_file="sbom.json"):
    try:
        # 下載並載入 Hugging Face 模型
        print(f"下載並載入模型：{model_name}")
        model = AutoModel.from_pretrained(model_name)
        config = AutoConfig.from_pretrained(model_name)

        # 取得 Python 環境的依賴
        print("掃描 Python 套件依賴...")
        dependencies = get_python_dependencies()

        # 建立 SBOM 物件
        bom = Bom()
        model_component = Component(
            name=model_name,
            version=config.model_type,
            description="Hugging Face AI Model"
        )

        # 加入模型到 SBOM
        bom.components.add(model_component)

        # 加入 Python 依賴
        for dep in dependencies:
            dependency_component = Component(
                name=dep["name"],
                version=dep["version"],
                description="Python Package Dependency"
            )
            bom.components.add(dependency_component)

        # 使用 cyclonedx 生成 SBOM JSON
        outputter: BaseOutput = get_instance(bom=bom, output_format=OutputFormat.JSON)
        bom_json: str = outputter.output_as_string()

        # 儲存 SBOM JSON 到檔案
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(bom_json)

        print(f"SBOM 產生完成：{output_file}")

        # 1. 解析轉義的字符串為 JSON 格式
        parsed_bom_json = json.loads(bom_json)
        # 2. 格式化並美化 JSON 輸出
        formatted_bom_json = json.dumps(parsed_bom_json, indent=4)

        # 將格式化後的 JSON 寫入檔案
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(formatted_bom_json)

    except Exception as e:
        print(f"發生錯誤：{e}")

def get_python_dependencies():
    """
    取得當前 Python 環境中的所有依賴與版本
    """
    dependencies = []
    try:
        result = subprocess.run(["pip", "list", "--format=json"], capture_output=True, text=True, check=True)
        packages = json.loads(result.stdout)
        for pkg in packages:
            dependencies.append({"name": pkg["name"], "version": pkg["version"]})
    except Exception as e:
        print(f"取得 Python 依賴失敗：{e}")
    return dependencies

# 指定要掃描的 Hugging Face 模型
model_names = ["tiiuae/falcon-7b", "gpt2", "bert-base-uncased", "google/mobilebert-uncased", "albert-base-v2", "google/electra-small-discriminator", "microsoft/Phi-3-mini-4k-instruct"]
for model_name in model_names:
    generate_sbom(model_name, f"bom/{model_name.replace('/', '_')}_sbom.json")
