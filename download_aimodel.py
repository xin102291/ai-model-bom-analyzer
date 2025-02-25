from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "gpt2"
save_dir = "./gpt2_model"  # 下載後儲存的資料夾

# 下載 GPT-2 模型與 tokenizer
model = AutoModelForCausalLM.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# 儲存到本地
model.save_pretrained(save_dir)
tokenizer.save_pretrained(save_dir)

print(f"GPT-2 已下載並儲存到 {save_dir}")
