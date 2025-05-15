# iii_internship

📁 bom/

存放已知模型的 BOM（物料清單）資料，用於比對。

每個模型包含兩種檔案：

xxx_info.json：模型的基本資訊（結構、超參數、權重統計）

xxx_analysis.json：模型的風險分析結果(假資料)

📁 data/

存放各種模型的基本 BOM 資料（僅有 _info.json，尚未產生分析結果）。

📁 test/

存放待檢測模型的 _info.json 檔案。

這些檔案會與 bom/ 中的已知模型進行比對。

📄 file_information.py

功能：透過 GitHub 連結，擷取模型的每個檔案資訊。

背景：根據 SPDX 的 AI BOM 範例，每個模型應包含所需檔案的詳細資訊。

狀態：目前此功能暫未使用，因為這部分資訊尚未納入分析流程，有時間的話之後會改成連結huggingface。

📄 model_information.py

功能：輸入 Hugging Face 上的模型名稱（格式：供應商/模型名稱），即可自動產生該模型的 _info.json。

主要用途：建立符合比對格式的模型資料檔案。

📄 show_model_comparison.py

功能：進行模型相似度比對，輸出與目標模型最接近的前 3 個模型。

評分方法：

結構特徵（30%）：逐項比對模型結構是否一致

超參數設定（20%）：key-value 配對

權重特徵（50%）：以 cosine similarity 比對權重統計資料

綜合評分公式：

final_score = 0.3 * 結構 + 0.2 * 超參數 + 0.5 * 權重相似度

📄 show_model_analysis.py

功能與 show_model_comparison.py 類似。

除了比對模型相似度外，額外顯示與該模型相似度超過 65% 的模型風險分析結果。


📄 show.py

將模型比對與分析結果整合進 Tkinter 圖形介面（GUI）。

使用者可進行模型上傳、比對與結果查看。

以下是目前收集在資料夾data的模型

distilbert/distilbert-base-uncased-finetuned-sst-2-english

state-spaces/mamba-130m-hf

teknium/OpenHermes-2.5-Mistral-7B

HuggingFaceH4/zephyr-7b-beta

stabilityai/stablelm-2-zephyr-1_6b

openchat/openchat-3.5-0106

EleutherAI/gpt-j-6bs

google/flan-t5-xl

facebook/opt-6.7b

mosaicml/mpt-7b-instruct

cerebras/Cerebras-GPT-6.7B
