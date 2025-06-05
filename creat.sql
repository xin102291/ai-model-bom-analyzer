-- 1. 建立 models 表（模型基本資訊）
CREATE TABLE IF NOT EXISTS models (
    id SERIAL PRIMARY KEY,  -- 模型唯一 ID
    name TEXT NOT NULL,  -- 模型名稱 (如 GPT-2, ResNet-50)
    version TEXT,  -- 模型版本
    framework TEXT,  -- 模型框架 (如 PyTorch, TensorFlow)
    source TEXT,  -- 模型來源 (如 HuggingFace)
    layers INTEGER,  -- 模型層數
    architecture TEXT,  -- 模型架構 (如 Transformer, CNN)
    parameter_count BIGINT,  -- 模型參數總數
    weight_hash TEXT,  -- 模型權重的哈希值（用於比對權重）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT unique_model UNIQUE (name, version)  -- 確保同一版本的模型不重複
);

-- 2. 建立 model_architecture 表（模型架構細節）
CREATE TABLE IF NOT EXISTS model_architecture (
    id SERIAL PRIMARY KEY,  
    model_id INTEGER REFERENCES models(id) ON DELETE CASCADE,  
    layer_index INTEGER NOT NULL,  -- 層次編號
    layer_type TEXT NOT NULL,  -- 層類型 (如 Convolution, Self-Attention)
    activation TEXT,  -- 激活函數 (如 ReLU, GELU)
    num_params BIGINT,  -- 該層的參數數量
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  
);

-- 3. 建立 model_weights 表（權重摘要資訊）
CREATE TABLE IF NOT EXISTS model_weights (
    id SERIAL PRIMARY KEY,  
    model_id INTEGER REFERENCES models(id) ON DELETE CASCADE,  
    layer_index INTEGER NOT NULL,  
    weight_hash TEXT NOT NULL,  -- 權重的哈希值
    weight_size INTEGER,  -- 權重檔案大小
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  
    CONSTRAINT unique_weight_hash UNIQUE (weight_hash)  -- 確保權重不重複
);

-- 4. 建立 sbom_packages 表（SBOM 軟體套件清單）
CREATE TABLE IF NOT EXISTS sbom_packages (
    id SERIAL PRIMARY KEY,  
    model_id INTEGER REFERENCES models(id) ON DELETE CASCADE,  
    package_name TEXT NOT NULL,  -- 套件名稱 (如 torch, transformers)
    version TEXT,  -- 套件版本
    license TEXT,  -- 套件授權 (如 MIT, Apache-2.0)
    source TEXT,  -- 套件來源
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  
    CONSTRAINT unique_package_version UNIQUE (package_name, version)  -- 確保同樣的 package/version 不重複
);

-- 5. 建立 vulnerabilities 表（漏洞 & 威脅資訊）
CREATE TABLE IF NOT EXISTS vulnerabilities (
    id SERIAL PRIMARY KEY,  
    model_id INTEGER REFERENCES models(id) ON DELETE CASCADE,  
    package_name TEXT,  
    cve_id TEXT,  -- 漏洞 ID (CVE-2024-XXXX)
    severity TEXT,  -- 嚴重程度 (如 高風險, 低風險)
    description TEXT,  -- 漏洞描述
    reference TEXT,  -- 漏洞參考資料 (如 CVE 官網連結)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  
    CONSTRAINT unique_vulnerability UNIQUE (package_name, cve_id)  -- 確保相同漏洞不重複
);

-- 6. 建立 model_metadata 表（存放額外資訊，如訓練數據、微調資訊）
CREATE TABLE IF NOT EXISTS model_metadata (
    id SERIAL PRIMARY KEY,  
    model_id INTEGER REFERENCES models(id) ON DELETE CASCADE,  
    key TEXT NOT NULL,  
    value TEXT NOT NULL,  
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  
);

-- **建立索引以提高查詢效率**
CREATE INDEX IF NOT EXISTS idx_models_name ON models(name);
CREATE INDEX IF NOT EXISTS idx_model_weights_model_layer ON model_weights(model_id, layer_index);
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_model ON vulnerabilities(model_id);
CREATE INDEX IF NOT EXISTS idx_sbom_packages_model ON sbom_packages(model_id);
