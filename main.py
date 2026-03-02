import os
import requests
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header

# --- 1. 核心配置 (硬编码) ---
# 已手动剔除可能的空格或隐形字符
AI_API_KEY = "AIzaSyCi9wRq-FHyUvLNLuhxLFdj8MVzjp0Rj3I".strip()
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()
MAIL_USER = os.getenv("MAIL_USER", "").strip()
MAIL_PASS = os.getenv("MAIL_PASS", "").strip()

def get_actual_model():
    """实时检测该 Key 到底能看到哪些模型"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={AI_API_KEY}"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        models = [m['name'].split('/')[-1] for m in data.get('models', []) if 'generateContent' in m.get('supportedMethods', [])]
        print(f">>> 诊断：此 Key 当前权限内的模型列表: {models}")
        
        # 按照优先级挑选
        for target in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]:
            if target in models: return target
        return models[0] if models else None
    except Exception as e:
        print(f">>> 诊断失败: {e}")
        return None

def summarize_with_ai(news_list):
    if not news_list: return None
    
    model_name = get_actual_model()
    if not model_name:
        print(">>> 错误：此 Key 目前无权调用任何生成式模型，请检查 Google Cloud 凭据限制。")
        return None
    
    print(f">>> 选定可用模型: {model_name}")
    news_text = "\n".join([f"- {n['title']}: {n.get('snippet','')}" for n in news_list[:8]])
    prompt = f"你是一个数字发改专家。请将以下资讯整理成 HTML 简报。作为思创数码(Thinvent)的一员，请在末尾为品牌市场部提供一条关于35周年的建议。数据：{news_text}"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={AI_API_KEY}"
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        res_json = response.json()
        if 'candidates' in res_json:
            print(">>> AI 响应成功！")
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f">>> AI 响应异常详情: {json.dumps(res_json)}")
            return None
    except Exception as e:
        print(f">>> 请求出错: {e}")
        return None

# ... (get_search_results 和 send_email 函数逻辑保持不变) ...

if __name__ == "__main__":
    news = get_search_results()
    if news:
        report = summarize_with_ai(news)
        if report:
            # 此处应调用你的 send_email(report)
            print("简报内容已生成，准备发送...")
