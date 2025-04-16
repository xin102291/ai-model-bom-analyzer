import json
import os

def load_analysis_json(analysis_dir):
    """
    讀取分析資料夾下的所有分析 JSON，回傳字典形式 {model_name: analysis_dict}
    """
    analysis_data = {}
    for fname in os.listdir(analysis_dir):
        if not fname.endswith('_analysis.json'):
            continue
        path = os.path.join(analysis_dir, fname)
        with open(path, 'r') as f:
            try:
                data = json.load(f)
                model_name = data.get('name')
                if model_name:
                    analysis_data[model_name] = data
            except Exception as e:
                print(f"❌ Failed to load {fname}: {e}")
    return analysis_data

def show_model_analysis_if_needed(matches, analysis_dict, threshold=0.75):
    print("\n📘 模型分析建議 (相似度 >= {:.0%}):".format(threshold))
    for match in matches:
        if match['final_score'] >= threshold:
            model_name = match['name']
            analysis = analysis_dict.get(model_name)
            if analysis:
                print(f"\n🔍 分析: {model_name}")
                # 範例內容簡要摘要
                sec = analysis.get("security", {})
                vul = analysis.get("vulnerabilities", {}).get("known_exploits", [])
                interp = analysis.get("interpretability", {})
                reg = analysis.get("regulatory_compliance", {})
                print(f"- 🔐 資安等級: {sec.get('adversarial_attack_vulnerabilities', {}).get('susceptibility_level')}")
                print(f"- 🧠 可解釋性: {interp.get('difficulty_level')} - {interp.get('interpretability_notes')}")
                print(f"- ⚠️ 已知漏洞數: {len(vul)}")
                for v in vul:
                    print(f"  • {v['exploit_name']} ({v['severity']}) - {v['patch_status']}")
                print(f"- 📝 歐盟法規符合度: {reg.get('eu_ai_act_compliance')}, GDPR: {reg.get('data_privacy_compliance')}")
            else:
                print(f"🔸 {model_name} 沒有找到分析資料。")

# 範例使用：
if __name__ == '__main__':
    from show_model_comparison import match_top_n

    unknown_model_path = 'EleutherAI_gpt-neo-1.3B_info.json'
    known_models_dir = './bom/'
    analysis_dir = './bom/'
    
    matches = match_top_n(unknown_model_path, known_models_dir)
    print("\n🔍 Top 3 Similar Models:")
    for i, m in enumerate(matches):
        print(f"#{i+1}: {m['name']} ({m['file']})")
        print(f"   ➤ Structure Match:   {m['structure']}")
        print(f"   ➤ Hyperparam Match:  {m['hyperparam']}")
        print(f"   ➤ Weight Similarity: {m['weight_sim']}")
        print(f"   ✅ Final Score:       {m['final_score']}")
        print("---")

    analysis_dict = load_analysis_json(analysis_dir)

    show_model_analysis_if_needed(matches, analysis_dict, threshold=0.75)
