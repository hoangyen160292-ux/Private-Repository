import os
import requests
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header

# --- 1. 核心配置 ---
# 已手动填入你提供的新 Key，并确保路径绝对纯净
AI_API_KEY = "AIzaSyCi9wRq-FHyUvLNLuhxLFdj8MVzjp0Rj3I".strip()
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()
MAIL_USER = os.getenv("MAIL_USER", "").strip()
MAIL_PASS = os.getenv("MAIL_PASS", "").strip()

# 针对江西数字发改业务定制
SEARCH_QUERY = "数字发改 政策 数字化转型 数据要素 江西省 招标公示"
RECEIVERS = [MAIL_USER] 

def get_actual_model():
    """实时诊断：检测该 Key 当前能看到的所有模型"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={AI_API_KEY}"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        # 提取有 generateContent 权限的模型
        models = [m['name'].split('/')[-1] for m in data.get('models', []) if 'generateContent' in m.get('supportedMethods', [])]
        print(f">>> 诊断：当前模型权限列表: {models}")
        
        for target in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]:
            if target in models: return target
        return models[0] if models else None
    except Exception as e:
        print(f">>> 诊断接口连接失败: {e}")
        return None

def get_search_results():
    """步骤 1: 搜集资讯"""
    print("正在搜集江西及全国数字发改资讯...")
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    payload = json.dumps({"q": SEARCH_QUERY, "gl": "cn", "hl": "zh-cn", "tbs": "qdr:d"})
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=20)
        return response.json().get('organic', [])
    except Exception as e:
        print(f"搜索环节失败: {e}")
        return []

def summarize_with_ai(news_list):
    """步骤 2: 调用 Gemini 生成分析"""
    if not news_list: return None
    
    model_name = get_actual_model()
    if not model_name:
        print(">>> 诊断列表仍为空。请确认 Google Cloud 限制已保存并生效（需约 5 分钟）。")
        return None
    
    print(f">>> 选定可用模型: {model_name}")
    news_text = "\n".join([f"- {n['title']}: {n.get('snippet','')}" for n in news_list[:10]])
    prompt = f"你是一个资深的数字发改分析专家。请将以下资讯整理成 HTML 简报。作为思创数码(Thinvent)品牌市场部的一员，请在末尾结合今日动态，为公司 35 周年提供一条品牌或业务拓展建议。数据：{news_text}"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={AI_API_KEY}"
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        res_json = response.json()
        if 'candidates' in res_json:
            print(">>> AI 响应成功！")
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f">>> AI 响应详情: {json.dumps(res_json)}")
            return None
    except Exception as e:
        print(f">>> AI 调用出错: {e}")
        return None

def send_email(html_body):
    """步骤 3: 发送邮件"""
    if not html_body: return
    print("正在准备发送简报邮件...")
    today = datetime.now().strftime('%Y-%m-%d')
    full_html = f"<html><body style='font-family:Arial; padding:20px;'>{html_body}<p style='color:grey; font-size:12px; margin-top:30px;'>思创数码品牌市场部 · 35周年自动化推送</p></body></html>"
    
    msg = MIMEText(full_html, 'html', 'utf-8')
    msg['From'] = f"资讯助手 <{MAIL_USER}>"
    msg['To'] = ",".join(RECEIVERS)
    msg['Subject'] = Header(f"【决策内参】数字发改业务动态 ({today})", 'utf-8')

    try:
        smtp = smtplib.SMTP_SSL("smtp.qq.com", 465)
        smtp.login(MAIL_USER, MAIL_PASS)
        smtp.sendmail(MAIL_USER, RECEIVERS, msg.as_string())
        print("Done: 简报已发送成功！")
    except Exception as e:
        print(f"邮件发送失败: {e}")

if __name__ == "__main__":
    news = get_search_results()
    if news:
        report = summarize_with_ai(news)
        if report:
            send_email(report)
    else:
        print("今日暂无资讯更新。")
