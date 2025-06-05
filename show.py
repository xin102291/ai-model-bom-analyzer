# 整合版 show.py：簡化為只保留 info 檔案產生，並移入分頁內，含進度條

import tkinter as tk
from tkinter import ttk, filedialog
from show_model_comparison import match_top_n
from show_model_analysis import load_analysis_json
from model_information import get_model_info
import numpy as np
import json
import os
from datetime import datetime
import threading

# 顏色風格
BG_COLOR = "#f4f8fb"
TEXT_COLOR = "#333333"

root = tk.Tk()
root.title("🧠 AI 模型分析器 Pro")
root.geometry("800x600")
root.configure(bg=BG_COLOR)

style = ttk.Style()
style.theme_use("clam")
style.configure("TNotebook", background=BG_COLOR)
style.configure("TFrame", background=BG_COLOR)
style.configure("TLabel", background=BG_COLOR, font=("Helvetica", 11))
style.configure("TButton", font=("Helvetica", 11), padding=6)

unknown_model_path = tk.StringVar()
model_name_var = tk.StringVar()

analysis_summary = ""
analysis_json_data = {}
match_scores = []

# ======== 匯入分析功能區 ========
def load_file():
    filepath = filedialog.askopenfilename(
        title="選擇模型檔案",
        filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
    )
    if filepath:
        unknown_model_path.set(filepath)
        analyze_model(filepath)

def save_analysis():
    global analysis_summary, analysis_json_data, match_scores
    if not analysis_summary.strip():
        return
    filetypes = [("Text Files", "*.txt"), ("JSON Files", "*.json")]
    filepath = filedialog.asksaveasfilename(
        title="儲存分析結果",
        defaultextension=".txt",
        filetypes=filetypes
    )
    if filepath:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if filepath.endswith(".json"):
            data = {
                "generated_at": timestamp,
                "input_model": unknown_model_path.get(),
                "top_matches": match_scores,
                "analysis": analysis_json_data
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"分析時間：{timestamp}\n")
                f.write(f"模型路徑：{unknown_model_path.get()}\n\n")
                for item in match_scores:
                    f.write(f"模型：{item['name']}\n")
                    f.write(f"  - 結構相似度：{item['structure']:.2f}\n")
                    f.write(f"  - 超參數相似度：{item['hyperparam']:.2f}\n")
                    f.write(f"  - 權重相似度：{item['weight_sim']:.2f}\n")
                    f.write(f"  ✅ 總分：{item['final_score']:.2f}\n\n")
                f.write(analysis_summary)

# ======== GUI 元件：上方工具列 ========
frame_top = ttk.Frame(root)
frame_top.pack(pady=10)
btn_import = ttk.Button(frame_top, text="📂 匯入模型檔案", command=load_file)
btn_import.pack(side=tk.LEFT, padx=5)
btn_save = ttk.Button(frame_top, text="💾 儲存分析結果", command=save_analysis)
btn_save.pack(side=tk.LEFT, padx=5)
path_label = ttk.Label(frame_top, textvariable=unknown_model_path, foreground=TEXT_COLOR)
path_label.pack(side=tk.LEFT, padx=5)

# ======== 分頁介面 ========
notebook = ttk.Notebook(root)
tab_result = ttk.Frame(notebook)
tab_analysis = ttk.Frame(notebook)
tab_info = ttk.Frame(notebook)
notebook.add(tab_result, text="📊 模型比對結果")
notebook.add(tab_analysis, text="🔍 模型分析建議")
notebook.add(tab_info, text="📦 模型下載")
notebook.pack(pady=10, expand=1, fill="both")

canvas_result = tk.Canvas(tab_result, bg="white", bd=0, highlightthickness=0)
scrollbar = ttk.Scrollbar(tab_result, orient="vertical", command=canvas_result.yview)
scrollable_frame = ttk.Frame(canvas_result)
scrollable_frame.bind("<Configure>", lambda e: canvas_result.configure(scrollregion=canvas_result.bbox("all")))
canvas_result.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas_result.configure(yscrollcommand=scrollbar.set)
canvas_result.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

analysis_text = tk.Text(tab_analysis, wrap="word", bg="#ffffff", font=("Courier New", 10), fg=TEXT_COLOR)
analysis_text.pack(padx=10, pady=10, fill="both", expand=True)

# ======== 模型資訊分頁內的輸入欄與進度條 ========
frame_info_input = ttk.Frame(tab_info)
frame_info_input.pack(pady=10)
label_model = ttk.Label(frame_info_input, text="模型名稱：")
label_model.pack(side=tk.LEFT, padx=5)
entry_model_name = ttk.Entry(frame_info_input, width=40, textvariable=model_name_var)
entry_model_name.pack(side=tk.LEFT, padx=5)
progress = ttk.Progressbar(frame_info_input, length=150, mode="indeterminate")
progress.pack(side=tk.LEFT, padx=5)
btn_generate_info = ttk.Button(frame_info_input, text="📝 產生 info 檔案", command=lambda: threading.Thread(target=generate_info_file).start())
btn_generate_info.pack(side=tk.LEFT, padx=5)

info_text = tk.Text(tab_info, wrap="word", bg="#ffffff", font=("Courier New", 10), fg=TEXT_COLOR)
info_text.pack(padx=10, pady=10, fill="both", expand=True)

# ======== 條狀圖繪製 ========
def draw_bar(canvas, x, y, label, value, color):
    label_text = f"{label}: {value*100:.1f}%"
    canvas.create_text(x, y, anchor="w", text=label_text, font=("Arial", 10))
    bar_start = x + 140
    bar_length = min(value * 200, 200)
    canvas.create_rectangle(bar_start, y - 5, bar_start + bar_length, y + 10, fill=color, width=0)
    if value >= 0.95:
        canvas.create_text(bar_start + bar_length - 5, y + 2, anchor="e", text="|", fill=color)

# ======== 分析主邏輯 ========
def analyze_model(path):
    global analysis_summary, analysis_json_data, match_scores
    known_models_dir = './bom/'
    analysis_dir = './bom/'
    matches = match_top_n(path, known_models_dir)
    analysis_dict = load_analysis_json(analysis_dir)

    for widget in scrollable_frame.winfo_children():
        widget.destroy()
    analysis_text.delete(1.0, tk.END)
    analysis_summary = ""
    analysis_json_data = {}
    match_scores = matches

    for i, m in enumerate(matches):
        final_score = float(m['final_score'])
        emoji = "✅" if final_score >= 0.75 else "⚠️" if final_score >= 0.6 else "❌"
        frame = ttk.LabelFrame(scrollable_frame, text=f"#{i+1}: {emoji} {m['name']} ({m['file']})", padding=10)
        frame.pack(fill="x", pady=5, padx=10)
        canvas = tk.Canvas(frame, height=100, bg="white", highlightthickness=0)
        canvas.pack(fill="x")
        draw_bar(canvas, 10, 20, "結構相似度", m['structure'], "#3E92CC")
        draw_bar(canvas, 10, 40, "超參數相似度", m['hyperparam'], "#63C132")
        draw_bar(canvas, 10, 60, "權重相似度", float(m['weight_sim']), "#F5A623")
        canvas.create_text(10, 80, anchor="w", text=f"{emoji} Final Score: {final_score:.3f}", font=("Arial", 11, "bold"))

        if final_score >= 0.6:
            analysis = analysis_dict.get(m['name'])
            if analysis:
                analysis_text.insert(tk.END, f"🔍 分析: {m['name']}\n")
                sec = analysis.get("security", {})
                vul = analysis.get("vulnerabilities", {}).get("known_exploits", [])
                interp = analysis.get("interpretability", {})
                reg = analysis.get("regulatory_compliance", {})
                sec_text = f"- 🔐 資安等級: {sec.get('adversarial_attack_vulnerabilities', {}).get('susceptibility_level', '未知')}\n"
                interp_text = f"- 🧠 可解釋性: {interp.get('difficulty_level', '未知')} - {interp.get('interpretability_notes', '')}\n"
                vul_text = f"- ⚠️ 已知漏洞數: {len(vul)}\n"
                vul_details = "".join([f"  • {v.get('exploit_name')} ({v.get('severity')}) - {v.get('patch_status')}\n" for v in vul])
                reg_text = f"- 📝 歐盟法規符合度: {reg.get('eu_ai_act_compliance')}, GDPR: {reg.get('data_privacy_compliance')}\n\n"
                total_text = sec_text + interp_text + vul_text + vul_details + reg_text
                analysis_text.insert(tk.END, total_text)
                analysis_summary += total_text
                analysis_json_data[m['name']] = analysis
            else:
                no_data_text = f"🔸 {m['name']} 沒有找到分析資料。\n"
                analysis_text.insert(tk.END, no_data_text)
                analysis_summary += no_data_text
                analysis_json_data[m['name']] = {"error": "無分析資料"}

# ======== 產生模型資訊檔案（含進度顯示） ========
def generate_info_file():
    model_name = model_name_var.get().strip()
    if not model_name:
        info_text.insert(tk.END, "❗ 請輸入模型名稱\n")
        return
    try:
        progress.start()
        info_text.delete(1.0, tk.END)
        info_text.insert(tk.END, f"⏳ 正在產生 {model_name} 的 info 檔案...\n")
        info = get_model_info(model_name)
        save_dir = "data"
        os.makedirs(save_dir, exist_ok=True)
        filename = f"{save_dir}/{model_name.replace('/', '_')}_info.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2, default=str)
        info_text.insert(tk.END, f"✅ 完成並儲存：{filename}\n")
    except Exception as e:
        info_text.insert(tk.END, f"❌ 發生錯誤：{str(e)}\n")
    finally:
        progress.stop()
        

root.mainloop()