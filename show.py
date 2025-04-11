import tkinter as tk
from tkinter import filedialog, messagebox
from show_model_comparison import match_top_n
from show_model_analysis import load_analysis_json

def load_file():
    # 讓使用者選擇檔案
    filepath = filedialog.askopenfilename(
        title="選擇模型檔案",
        filetypes=(("JSON Files", "*.json"), ("All Files", "*.*"))
    )
    if filepath:
        unknown_model_path.set(filepath)
        analyze_model(filepath)

def analyze_model(unknown_model_path):
    # 根據使用者選擇的檔案進行分析
    known_models_dir = './bom/'
    analysis_dir = './bom/'

    # 匹配相似模型
    matches = match_top_n(unknown_model_path, known_models_dir)

    # 顯示分析結果
    result_text.delete(1.0, tk.END)
    for i, m in enumerate(matches):
        result_text.insert(tk.END, f"#{i+1}: {m['name']} ({m['file']})\n")
        result_text.insert(tk.END, f"   ➤ Structure Match:   {m['structure']:.2f}\n")
        result_text.insert(tk.END, f"   ➤ Hyperparam Match:  {m['hyperparam']:.2f}\n")
        result_text.insert(tk.END, f"   ➤ Weight Similarity: {m['weight_sim']:.2f}\n")
        result_text.insert(tk.END, f"   ✅ Final Score:       {m['final_score']:.2f}\n")
        result_text.insert(tk.END, "---\n")

    # 顯示模型分析
    analysis_label.config(text="📘 模型分析建議 (相似度 >= 80%):")
    
    analysis_dict = load_analysis_json(analysis_dir)
    analysis_results = ""
    
    for match in matches:
        if match['final_score'] >= 0.8:  # 只顯示相似度大於 80%的模型分析
            model_name = match['name']
            analysis = analysis_dict.get(model_name, None)
            
            if analysis:
                analysis_results += f"\n🔍 分析: {model_name}\n"
                
                # 資安等級
                sec = analysis.get("security", {})
                adversarial_attack = sec.get("adversarial_attack_vulnerabilities", {})
                susceptibility_level = adversarial_attack.get('susceptibility_level', '未知')
                analysis_results += f"- 🔐 資安等級: {susceptibility_level}\n"
                
                # 可解釋性
                interp = analysis.get("interpretability", {})
                difficulty_level = interp.get('difficulty_level', '未知')
                interpretability_notes = interp.get('interpretability_notes', '無詳細說明')
                analysis_results += f"- 🧠 可解釋性: {difficulty_level} - {interpretability_notes}\n"
                
                # 已知漏洞數
                vul = analysis.get("vulnerabilities", {}).get("known_exploits", [])
                analysis_results += f"- ⚠️ 已知漏洞數: {len(vul)}\n"
                for v in vul:
                    exploit_name = v.get('exploit_name', '未知漏洞')
                    severity = v.get('severity', '未知')
                    patch_status = v.get('patch_status', '未知')
                    analysis_results += f"  • {exploit_name} ({severity}) - {patch_status}\n"
                
                # 歐盟法規符合度
                reg = analysis.get("regulatory_compliance", {})
                eu_compliance = reg.get("eu_ai_act_compliance", '未知')
                gdpr_compliance = reg.get("data_privacy_compliance", '未知')
                analysis_results += f"- 📝 歐盟法規符合度: {eu_compliance}, GDPR: {gdpr_compliance}\n"
            else:
                analysis_results += f"🔸 {model_name} 沒有找到分析資料。\n"

    # 顯示整理過的分析結果
    if analysis_results:
        analysis_text.delete(1.0, tk.END)
        analysis_text.insert(tk.END, analysis_results)
    else:
        analysis_text.delete(1.0, tk.END)
        analysis_text.insert(tk.END, "目前沒有符合條件的模型分析建議。")

# 主視窗設置
root = tk.Tk()
root.title("AI 模型分析器")
root.geometry("650x650")  # 調整視窗大小
root.configure(bg="#f4f8fb")  # 淺灰背景色

# 使用者選擇的檔案路徑
unknown_model_path = tk.StringVar()

# 匯入檔案按鈕
import_button = tk.Button(
    root,
    text="匯入模型檔案",
    command=load_file,
    font=("Arial", 10),
    bg="#4CAF50",  # 按鈕背景顏色
    fg="white",  # 按鈕文字顏色
    relief="raised",
    padx=15,
    pady=10
)
import_button.pack(pady=30)

# 顯示比對結果區域
result_frame = tk.Frame(root, bg="#f4f8fb")
result_frame.pack(padx=20, pady=20)

result_text = tk.Text(
    result_frame,
    height=10,  # 降低高度
    width=70,   # 降低寬度
    font=("Courier New", 10),
    bg="#ffffff",  # 設定背景顏色
    fg="#333333",  # 設定字體顏色
    padx=10,
    pady=10
)
result_text.pack()

# 顯示分析建議區域
analysis_label = tk.Label(
    root,
    text="📘 模型分析建議 (相似度 >= 80%):",
    font=("Helvetica", 14, "bold"),
    bg="#f4f8fb",
    fg="#333333"
)
analysis_label.pack(padx=10, pady=5)

analysis_text = tk.Text(
    root,
    height=10,  # 降低高度
    width=70,   # 降低寬度
    font=("Courier New", 10),
    bg="#f9f9f9",  # 設定分析區域背景顏色
    fg="#333333",  # 設定字體顏色
    padx=10,
    pady=10
)
analysis_text.pack(padx=10, pady=5)

root.mainloop()
