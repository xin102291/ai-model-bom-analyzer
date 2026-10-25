# AI Model BOM Analyzer

Generate SPDX-style AI BOM files for Hugging Face models and identify an unknown model by comparing its structure, hyperparameters and weight statistics against known models, with a Tkinter GUI and an optional MySQL backend.

## 簡介

資策會（III）實習期間開發的 AI 模型物料清單（AI BOM）分析工具。目標是：拿到一個來源不明的模型時，能自動產出它的 BOM 並比對出最可能的原始模型，進一步帶出該模型已知的風險資訊。

主要功能：

1. **產生 AI BOM**：輸入 Hugging Face 模型名稱，用 `transformers` 載入設定與權重，輸出 SPDX AI Package 格式的 `_info.json`（架構、超參數、每層權重統計、訓練資料集）。
2. **模型相似度比對**：以「結構 30%、超參數 20%、權重 cosine similarity 50%」計算綜合分數，列出最相似的前 3 個已知模型。
3. **風險分析顯示**：相似度達門檻時，顯示該已知模型的資安、可解釋性、已知漏洞與法規符合度資訊（目前為示範資料）。
4. **資料庫版本**：抓取 Hugging Face 下載量前 100 名的公開模型，將模型資訊匯入 MySQL，再直接從資料庫比對。
5. **Tkinter GUI**：把匯入、比對、分析、產生 BOM 整合成一個桌面介面。

## 專案背景

- 單位：財團法人資訊工業策進會（III）
- 分工：全部功能由本人獨立設計與開發

## 架構

```
iii_internship/
├─ show.py                      # Tkinter GUI 主程式（入口）
├─ show_model_comparison.py     # 相似度比對核心（JSON 檔版本）
├─ show_model_analysis.py       # 讀取 _analysis.json、依門檻顯示風險分析
├─ model_information.py         # 產生單一模型的 _info.json（AI BOM）
├─ huggingface_list.py          # 抓 HF 下載量前 100 的公開模型 → CSV
├─ huggingface_top100_public_models.csv
├─ import_100.py                # 將模型資訊匯入 MySQL（含權重統計）
├─ update_model_architecture_fields.py  # 補齊資料庫中缺漏的架構欄位
├─ sql_model_comparison.py      # 相似度比對（MySQL 版本）
├─ model_sbom.py                # 實驗：用 CycloneDX 產生模型＋套件 SBOM
├─ file_information.py          # 實驗：從 GitHub repo 產生 SPDX 3.0 BOM
├─ bom/                         # 已知模型：*_info.json ＋ *_analysis.json
├─ data/                        # 已產生 _info.json、尚未寫分析的模型
├─ test/                        # 待檢測的未知模型 _info.json
├─ .env.example                 # 環境變數範本
└─ requirements.txt
```

### 資料夾

| 資料夾 | 內容 |
|---|---|
| `bom/` | 已知模型的比對基準。每個模型兩個檔：`*_info.json`（結構、超參數、權重統計）與 `*_analysis.json`（風險分析，示範資料）。 |
| `data/` | 只有 `*_info.json` 的模型，GUI 的「模型下載」分頁產出的檔案也放這裡。 |
| `test/` | 待檢測模型的 `*_info.json`，作為比對輸入。 |

### 處理流程

```
Hugging Face ──model_information.py──▶ test/ 或 data/ 的 *_info.json
                                              │
             bom/*_info.json ──────────▶ show_model_comparison.py ──▶ Top 3 相似模型
                                              │
             bom/*_analysis.json ──────▶ show_model_analysis.py ──▶ 風險分析
                                              │
                                          show.py（GUI）

資料庫版：
huggingface_list.py ──▶ CSV ──▶ import_100.py ──▶ MySQL
                                   │                 │
                   update_model_architecture_fields.py   sql_model_comparison.py
```

### 比對方法

| 面向 | 權重 | 做法 |
|---|---|---|
| 結構 | 30% | 比對 `model_type`、`model_architecture`、`layer_count`、`hidden_size`、`embedding_size`、`attention_heads` 六個欄位，相同的比例即為分數。 |
| 超參數 | 20% | 比對 `activation_function`、`initializer_range`、`hidden_dropout_prob`、`intermediate_size` 四個 key 的值。 |
| 權重 | 50% | 每層的 mean／std／min／max 串成向量，截到相同長度後算 cosine similarity。 |

```
final_score = 0.3 × 結構 + 0.2 × 超參數 + 0.5 × 權重相似度
```

GUI 在 `final_score ≥ 0.6` 時顯示風險分析；命令列版 `show_model_analysis.py` 預設門檻為 0.75。

### 資料庫

`import_100.py` 寫入三張表：`HF_model`（模型基本欄位與權限）、`HF_model_hyperparameters`（key／value）、`HF_model_weights_details`（每層權重統計）。建表 SQL 未包含在本 repo，欄位可對照 `import_100.py` 開頭的 INSERT 語句。

## 安裝

```bash
pip install -r requirements.txt
cp .env.example .env   # Windows 用 copy
```

編輯 `.env`：

- `DB_HOST`、`DB_USER`、`DB_PASSWORD`、`DB_NAME`：MySQL 連線（只有資料庫版本的三支腳本需要）。
- `HF_TOKEN`：Hugging Face token，下載 gated 模型時才需要；只處理公開模型可留空。

需要 Python 3 與 Tkinter（Windows 官方安裝包已內建）。

## 使用方式

### GUI

```bash
python show.py
```

- **匯入模型檔案**：選一個 `*_info.json`（例如 `test/` 裡的），右側顯示前 3 名相似模型與三項分數的長條圖。
- **模型分析建議**分頁：顯示相似度達門檻的模型風險資料。
- **模型下載**分頁：輸入 `供應商/模型名稱`，產生 `_info.json` 到 `data/`。
- **儲存分析結果**：輸出為 `.txt` 或 `.json`。

### 命令列

```bash
# 產生 _info.json（在檔案最後的 model_names 改成要處理的模型，輸出到 test/）
python model_information.py

# 比對（在 __main__ 裡改 unknown_model_path）
python show_model_comparison.py
python show_model_analysis.py
```

### 資料庫版本

```bash
python huggingface_list.py                   # 產生 huggingface_top100_public_models.csv
python import_100.py                         # 匯入模型（__main__ 裡指定模型清單或 CSV 範圍）
python update_model_architecture_fields.py   # 補齊缺漏欄位
python sql_model_comparison.py               # 從資料庫比對
```

`import_100.py` 會下載完整權重檔計算統計值後再刪除，大模型相當耗時與耗流量。

## 注意事項

- `bom/*_analysis.json` 的風險分析為示範資料，非實際評估結果。
- `model_sbom.py`（CycloneDX）與 `file_information.py`（GitHub repo 的 SPDX BOM）是早期實驗腳本，未納入主流程。
- `.env` 已列在 `.gitignore`，請勿把密碼或 token 寫回程式碼。
