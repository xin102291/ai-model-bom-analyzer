import requests
import json

def get_github_repo_info(repo_url):
    """
    擷取 GitHub Repo 資料和內容
    """
    # 擷取 GitHub 的 Owner 和 Repo 名稱
    parts = repo_url.strip().split('/')
    owner, repo = parts[-2], parts[-1]

    # GitHub API endpoint for repository details
    repo_api_url = f"https://api.github.com/repos/{owner}/{repo}"
    contents_api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"

    # 獲取 repository 資訊
    response = requests.get(repo_api_url)
    if response.status_code == 200:
        repo_info = response.json()
    else:
        print(f"Failed to fetch repository info for {repo_url}")
        return None, None

    # 獲取 repository 內容（檔案和資料夾）
    contents_info = requests.get(contents_api_url).json()

    return repo_info, contents_info

def get_requirements_from_github(contents_info, repo_url):
    """
    從 GitHub 取得 requirements.txt 並解析出套件
    """
    requirements = []
    for content in contents_info:
        if content['name'] == 'requirements.txt' and content['type'] == 'file':
            # 下載 requirements.txt 內容
            file_url = content['download_url']
            response = requests.get(file_url)
            if response.status_code == 200:
                requirements = response.text.splitlines()
            else:
                print(f"Failed to fetch requirements.txt from {repo_url}.")
            break
    return requirements

def get_license_from_github(contents_info, repo_url):
    """
    從 GitHub 獲取 LICENSE 檔案並提取授權資訊
    """
    license_info = []
    for content in contents_info:
        if content['name'].lower() == 'license' and content['type'] == 'file':
            # 下載 LICENSE 檔案內容
            file_url = content['download_url']
            response = requests.get(file_url)
            if response.status_code == 200:
                # 假設 LICENSE 檔案可能包含多個授權條款，我們分割並提取它們
                license_info = response.text.strip().split("\n\n")  # 根據空行分割不同的授權條款
            else:
                print(f"Failed to fetch LICENSE file from {repo_url}.")
            break
    return license_info

def create_spdx_bom(repo_info, contents_info, model_name=None, dataset_name=None, ai_package_info=None):
    """
    創建 SPDX 物料清單 (BOM)
    """
    bom = {
        "@context": "https://spdx.org/rdf/3.0.0/spdx-context.jsonld",
        "@graph": []
    }

    # 添加 Person 資訊
    person = {
        "type": "Person",
        "spdxId": f"https://github.com/{repo_info['owner']['login']}",
        "name": repo_info['owner']['login'],
    }
    bom["@graph"].append(person)

    # 添加 CreationInfo 資訊
    creation_info = {
        "type": "CreationInfo",
        "@id": "_:creationinfo",
        "specVersion": "3.0.0",
        "createdBy": [person["spdxId"]],
        "created": repo_info['created_at']
    }
    bom["@graph"].append(creation_info)

    # 添加 SpdxDocument 資訊
    spdx_document = {
        "type": "SpdxDocument",
        "spdxId": f"https://my-first-aibom.com/{repo_info['name']}-bom",
        "creationInfo": "_:creationinfo",
        "profileConformance": ["core", "software", "ai", "dataset"],
        "rootElement": [f"https://my-first-aibom.com/{repo_info['name']}-bom"]
    }
    bom["@graph"].append(spdx_document)

    # 添加 model 和 dataset 的物料清單
    if model_name:
        model_info = {
            "type": "software_Package",
            "spdxId": f"https://my-first-aibom.com/{model_name}",
            "creationInfo": "_:creationinfo",
            "name": model_name,
            "software_downloadLocation": f"https://github.com/{repo_info['owner']['login']}/{repo_info['name']}/tree/master/{model_name}",
            "originatedBy": [person["spdxId"]]
        }
        bom["@graph"].append(model_info)

    if dataset_name:
        dataset_info = {
            "type": "software_Package",
            "spdxId": f"https://my-first-aibom.com/{dataset_name}",
            "creationInfo": "_:creationinfo",
            "name": dataset_name,
            "software_downloadLocation": f"https://github.com/{repo_info['owner']['login']}/{repo_info['name']}/tree/master/{dataset_name}",
            "originatedBy": [person["spdxId"]]
        }
        bom["@graph"].append(dataset_info)


    # 讀取 requirements.txt 並添加套件到物料清單
    requirements = get_requirements_from_github(contents_info, repo_info['html_url'])
    if requirements:
        for req in requirements:
            package_info = {
                "type": "software_Package",
                "spdxId": f"https://pypi.org/project/{req.split('==')[0]}/",
                "creationInfo": "_:creationinfo",
                "name": req.split('==')[0],
                "software_downloadLocation": f"https://pypi.org/project/{req.split('==')[0]}/",
                "software_homePage": f"https://pypi.org/project/{req.split('==')[0]}/",
                "software_packageVersion": req.split('==')[1] if '==' in req else "latest",
                "originatedBy": [person["spdxId"]],
                "software_primaryPurpose": "library",
                "description": f"Package {req.split('==')[0]} version {req.split('==')[1] if '==' in req else 'latest'}"
            }
            bom["@graph"].append(package_info)

    # 檢查 LICENSE 檔案並加入授權資訊
    license_info = get_license_from_github(contents_info, repo_info['html_url'])
    if license_info:
        for license_text in license_info:
            license = {
                "type": "simplelicensing_LicenseExpression",
                "spdxId": f"https://spdx.org/licenses/{license_text.split()[0]}",  # 根據授權條款的第一個字元來設置 spdxId
                "simplelicensing_licenseExpression": license_text,
                "simplelicensing_licenseListVersion": "3.24.0"
            }
            bom["@graph"].append(license)


    # 遍歷檔案和資料夾，將每個資料夾和檔案加入物料清單
    def process_contents(contents, parent_spdxId=None):
        for content in contents:
            if content['type'] == 'file':
                # 檔案
                file_info = {
                    "type": "software_File",
                    "spdxId": f"https://github.com/{repo_info['owner']['login']}/{repo_info['name']}/tree/{content['path']}",
                    "creationInfo": "_:creationinfo",
                    "name": content['path'],
                    "originatedBy": [person["spdxId"]],
                    "software_primaryPurpose": "executable",
                    "software_additionalPurpose": ["source"],
                    "software_fileKind": "file"
                }
                bom["@graph"].append(file_info)

                # 添加依賴項
                if 'model' in content['path']:
                    relationship = {
                        "type": "Relationship",
                        "spdxId": f"https://github.com/{repo_info['owner']['login']}/{repo_info['name']}/tree/{content['path']}-contains",
                        "creationInfo": "_:creationinfo",
                        "relationshipType": "contains",
                        "from": f"https://github.com/{repo_info['owner']['login']}/{repo_info['name']}/tree/{content['path']}",
                        "to": [
                            f"https://github.com/{repo_info['owner']['login']}/{repo_info['name']}/tree/model/word-model/charList",
                            f"https://github.com/{repo_info['owner']['login']}/{repo_info['name']}/tree/model/word-model/checkpoint"
                        ]
                    }
                    bom["@graph"].append(relationship)

            elif content['type'] == 'dir':
                # 資料夾
                folder_info = {
                    "type": "software_Package",
                    "spdxId": f"https://github.com/{repo_info['owner']['login']}/{repo_info['name']}/tree/{content['path']}",
                    "creationInfo": "_:creationinfo",
                    "name": content['path'],
                    "originatedBy": [person["spdxId"]]
                }
                bom["@graph"].append(folder_info)
                # 遞迴處理資料夾內容
                folder_contents = requests.get(content['url']).json()
                process_contents(folder_contents, content['path'])

    # 處理所有檔案與資料夾
    process_contents(contents_info)

    return bom

def generate_spdx_bom_for_github_repo(repo_url, model_name=None, dataset_name=None):
    """
    根據 GitHub Repo 生成 SPDX 物料清單
    """
    # 獲取 repo 資料
    repo_info, contents_info = get_github_repo_info(repo_url)

    if repo_info and contents_info:
        # 創建 SPDX 物料清單
        bom = create_spdx_bom(repo_info, contents_info, model_name, dataset_name)
        return bom
    else:
        print("Error: Failed to generate SPDX BOM due to missing data.")
        return None

def save_bom_to_json(bom, file_name="spdx_bom.json"):
    """
    將生成的 SPDX 物料清單保存為 JSON 檔案
    """
    with open(file_name, "w") as outfile:
        json.dump(bom, outfile, indent=4)
    print(f"SPDX BOM saved to {file_name}")

# 使用範例：生成 GPT-2 和 OpenWebText2 的 SPDX 物料清單
repo_url_gpt2 = "https://github.com/openai/gpt-2"
repo_url_openwebtext2 = "https://github.com/EleutherAI/openwebtext2"

# 假設我們知道 GPT-2 模型名為 "gpt2" 和 OpenWebText2 資料集名稱為 "openwebtext2"
bom_gpt2 = generate_spdx_bom_for_github_repo(repo_url_gpt2, model_name="gpt2", dataset_name="openwebtext2")
bom_openwebtext2 = generate_spdx_bom_for_github_repo(repo_url_openwebtext2, model_name="gpt2", dataset_name="openwebtext2")

# 保存物料清單到 JSON 文件
if bom_gpt2:
    save_bom_to_json(bom_gpt2, "gpt2_spdx_bom.json")
if bom_openwebtext2:
    save_bom_to_json(bom_openwebtext2, "openwebtext2_spdx_bom.json")
