-- 1. 建立 models 表（模型基本資訊）
CREATE TABLE IF NOT EXISTS models (
    id SERIAL PRIMARY KEY, -- 模型唯一 ID
    name TEXT NOT NULL, -- 模型名稱 (如 GPT-2, ResNet-50)
    version TEXT, -- 模型版本
    framework TEXT, -- 模型框架 (如 PyTorch, TensorFlow)
    source TEXT, -- 模型來源 (如 HuggingFace)
    layers INTEGER, -- 模型層數
    architecture TEXT, -- 模型架構 (如 Transformer, CNN)
    parameter_count BIGINT, -- 模型參數總數
    weight_hash TEXT, -- 模型權重的哈希值（用於比對權重）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 創建時間
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP -- 更新時間
);

-- 2. 建立 model_architecture 表（模型架構細節）
CREATE TABLE IF NOT EXISTS model_architecture (
    id SERIAL PRIMARY KEY, -- 唯一 ID
    model_id INTEGER REFERENCES models(id) ON DELETE CASCADE, -- 關聯 models 表的 model_id
    layer_index INTEGER NOT NULL, -- 層次編號
    layer_type TEXT NOT NULL, -- 層類型 (如 Convolution, Self-Attention)
    activation TEXT, -- 激活函數 (如 ReLU, GELU)
    num_params BIGINT, -- 該層的參數數量
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- 創建時間
);

-- 3. 建立 model_weights 表（權重摘要資訊）
CREATE TABLE IF NOT EXISTS model_weights (
    id SERIAL PRIMARY KEY, -- 唯一 ID
    model_id INTEGER REFERENCES models(id) ON DELETE CASCADE, -- 關聯 models 表的 model_id
    layer_index INTEGER NOT NULL, -- 層次編號，對應 model_architecture 中的 layer_index
    weight_hash TEXT NOT NULL, -- 權重的哈希值
    weight_size INTEGER, -- 權重檔案大小
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- 創建時間
);

-- 4. 建立 sbom_packages 表（SBOM 軟體套件清單）
CREATE TABLE IF NOT EXISTS sbom_packages (
    id SERIAL PRIMARY KEY, -- 唯一 ID
    model_id INTEGER REFERENCES models(id) ON DELETE CASCADE, -- 關聯 models 表的 model_id
    package_name TEXT NOT NULL, -- 套件名稱 (如 torch, transformers)
    version TEXT, -- 套件版本
    license TEXT, -- 套件授權 (如 MIT, Apache-2.0)
    source TEXT, -- 套件來源
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- 創建時間
);

-- 5. 建立 vulnerabilities 表（漏洞 & 威脅資訊）
CREATE TABLE IF NOT EXISTS vulnerabilities (
    id SERIAL PRIMARY KEY, -- 唯一 ID
    model_id INTEGER REFERENCES models(id) ON DELETE CASCADE, -- 關聯 models 表的 model_id
    package_name TEXT, -- 套件名稱
    cve_id TEXT, -- 漏洞 ID (CVE-2024-XXXX)
    severity TEXT, -- 嚴重程度 (如 高風險, 低風險)
    description TEXT, -- 漏洞描述
    reference TEXT, -- 漏洞參考資料 (如 CVE 官網連結)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- 創建時間
);

-- **建立索引以提高查詢效率**
-- 這些索引會加速模型、權重、架構和漏洞的查詢

-- 為 models 表的 name 欄位建立索引，便於快速查詢模型名稱
CREATE INDEX IF NOT EXISTS idx_models_name ON models(name);

-- 為 model_weights 表的 model_id 和 layer_index 欄位建立索引，便於快速查詢權重
CREATE INDEX IF NOT EXISTS idx_model_weights_model_layer ON model_weights(model_id, layer_index);

-- 為 vulnerabilities 表的 model_id 欄位建立索引，便於快速查詢漏洞
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_model ON vulnerabilities(model_id);

-- 為 sbom_packages 表的 model_id 欄位建立索引，便於快速查詢 SBOM 相關資訊
CREATE INDEX IF NOT EXISTS idx_sbom_packages_model ON sbom_packages(model_id);


