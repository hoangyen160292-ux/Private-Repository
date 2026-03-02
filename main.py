import os
import requests
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header

# --- 1. 核心配置 (硬编码确保万无一失) ---
AI_API_KEY = "AIzaSyCi9wRq-FHyUvLNLuhxLFdj8MVzjp0Rj3I"
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()
MAIL_USER = os.getenv("MAIL_USER", "").strip()
MAIL_PASS = os.getenv("MAIL_PASS", "").strip()

SEARCH_QUERY = "数字发改 政策 数字化转型 数据要素 江西省 招标公示"
RECEIVERS = [MAIL_USER]

def get_available_model():
    """诊断函数：获取当前 API Key 真正拥有权限的模型名称"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={AI_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        models = response.json().get('models', [])
        # 优先寻找 1.5 flash，找不到则寻找 1.5 pro，再找不到则返回第一个支持 generateContent 的模型
        model_names = [m['name'].split('/')[-1] for m in models if 'generateContent' in m.get('supportedMethods', [])]
        print(f"当前 API Key 可用模型列表: {model_names}")
        
        for target in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]:
            if target in model_names:
                return target
        return model_names[0] if model_names else "gemini-1.5-flash"
    except Exception as e:
        print(f"无法获取模型列表: {e}")
        return "gemini-1.5-flash"

def get_search_results():
    print("正在搜集江西数字发改资讯...")
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    payload = json.dumps({"q": SEARCH_QUERY, "gl": "cn", "hl": "zh-cn", "tbs": "qdr:d"})
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=20)
        return response.json().get('organic', [])
    except Exception as e:
        print(f"搜索失败: {e}")
        return []

def summarize_with_ai(news_list):
    if not news_list: return None
    
    # 动态确定可用模型
    model_name = get_available_model()
    print(f"决定使用模型: {model_name} 进行业务分析...")

    news_text = "\n".join([f"- {n['title']}: {n.get('snippet','')}" for n in news_list[:8]])
    prompt = f"你是一个数字发改专家。请将以下资讯整理成 HTML 简报。作为思创数码(Thinvent)的一员，请在末尾为品牌市场部提供一条关于35周年的建议。数据：{news_text}"

    # 关键点：使用动态获取的模型名，并确保 URL 绝对纯净
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={AI_API_KEY}"
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        res_json = response.json()
        if 'candidates' in res_json:
            print("AI 响应成功！")
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"AI 响应详情: {json.dumps(res_json)}")
            return None
    except Exception as e:
        print(f"AI 调用阶段失败: {e}")
        return None

def send_email(content):
    if not content: return
    print("正在准备发送邮件...")
    today = datetime.now().strftime('%Y-%m-%d')
    full_html = f"<html><body style='font-family:Arial; padding:20px;'>{content}</body></html>"
    msg = MIMEText(full_html, 'html', 'utf-8')
    msg['From'] = f"资讯助手 <{MAIL_USER}>"
    msg['To'] = ",".join(RECEIVERS)
    msg['Subject'] = Header(f"【每日内参】数字发改业务动态 ({today})", 'utf-8')

    try:
        smtp = smtplib.SMTP_SSL("smtp.qq.com", 465)
        smtp.login(MAIL_USER, MAIL_PASS)
        smtp.sendmail(MAIL_USER, RECEIVERS, msg.as_string())
        print("Done: 简报已成功送达！")
    except Exception as e:
        print(f"邮件发送失败: {e}")

if __name__ == "__main__":
    if not all([SERPER_API_KEY, MAIL_USER, MAIL_PASS]):
        print("错误：Secrets (SERPER/MAIL) 配置不完整。")
    else:
        news = get_search_results()
        if news:
            report = summarize_with_ai(news)
            if report: send_email(report)
        else:
            print("今日关键词下暂无新资讯。")
