import json
from datetime import datetime
import uuid

def load_json(file_path):
    """ 讀取 JSON 檔案 """
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)

def generate_spdx_3(data):
    """ 根據 JSON 資料產生 SPDX 3.0 AI BOM """

    creation_time = data["creationInfo"]["created"]
    creation_info_id = f"_:creationinfo-{uuid.uuid4()}"

    spdx_document = {
        "@context": "https://spdx.org/rdf/3.0.0/spdx-context.jsonld",
        "@graph": []
    }

    # 創建人資訊
    person_id = "https://my-aibom.com/ai-bom-generator"
    spdx_document["@graph"].append({
        "type": "Person",
        "spdxId": person_id,
        "creationInfo": creation_info_id,
        "name": "AI-BOM-Generator-1.0"
    })

    # 創建資訊
    spdx_document["@graph"].append({
        "type": "CreationInfo",
        "@id": creation_info_id,
        "specVersion": data["spdxVersion"],
        "createdBy": [person_id],
        "created": creation_time
    })

    # SPDX 主文件
    root_elements = []
    for package in data["packages"]:
        root_elements.append(f"https://my-aibom.com/{package['SPDXID']}")

    for file in data["files"]:
        root_elements.append(f"https://my-aibom.com/{file['SPDXID']}")

    spdx_document["@graph"].append({
        "type": "SpdxDocument",
        "spdxId": "https://my-aibom.com/document",
        "creationInfo": creation_info_id,
        "profileConformance": ["core", "software", "ai", "dataset"],
        "rootElement": root_elements
    })

    # 添加 AI 模型 (軟體包)
    for package in data["packages"]:
        model_id = f"https://my-aibom.com/{package['SPDXID']}"
        spdx_document["@graph"].append({
            "type": "software_Package",
            "spdxId": model_id,
            "creationInfo": creation_info_id,
            "name": package["name"],
            "software_downloadLocation": package["downloadLocation"],
            "originatedBy": [person_id],
            "software_primaryPurpose": package["primaryPurpose"],
            "software_version": package["versionInfo"],
            "releaseTime": package["releaseTime"],
            "buildTime": package["buildTime"],
            "supplier": package["supplier"],
            "licenseConcluded": package["licenseConcluded"],
            "licenseDeclared": package["licenseDeclared"]
        })

    # 添加 資料集 (軟體檔案)
    for file in data["files"]:
        dataset_id = f"https://my-aibom.com/{file['SPDXID']}"
        spdx_document["@graph"].append({
            "type": "software_File",
            "spdxId": dataset_id,
            "creationInfo": creation_info_id,
            "name": file["fileName"],
            "software_downloadLocation": file["downloadLocation"],
            "originatedBy": [person_id],
            "software_primaryPurpose": "語料庫資料集",
            "fileLicenseConcluded": file["fileLicenseConcluded"],
            "fileLicenseDeclared": file["fileLicenseDeclared"],
            "software_fileKind": "dataset"
        })

    # 關聯資訊 (AI 模型 -> 訓練用的資料集)
    for relation in data["relationships"]:
        spdx_document["@graph"].append({
            "type": "Relationship",
            "spdxId": f"https://my-aibom.com/relationship-{uuid.uuid4()}",
            "creationInfo": creation_info_id,
            "relationshipType": relation["relationshipType"],
            "from": f"https://my-aibom.com/{relation['relatedSpdxElement']}",
            "to": [f"https://my-aibom.com/{relation['spdxElementId']}"]
        })

    return spdx_document

# 🟢 執行程式
input_file = "spdx_ai_bom_20250225142955.json"
output_file = "ai_bom.json"

# 讀取 JSON 資料
input_data = load_json(input_file)

# 產生 AI BOM JSON
ai_bom_json = generate_spdx_3(input_data)

# 儲存為 JSON 檔案
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(ai_bom_json, f, indent=4, ensure_ascii=False)

print(f"✅ AI BOM JSON 檔案已成功產生！請查看 {output_file}")
