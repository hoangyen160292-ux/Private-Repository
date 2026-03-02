import os
import requests
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header

# --- 1. 核心配置 ---
# 已经使用你提供的新 API Key，并去除了所有可能的干扰字符
AI_API_KEY = "AIzaSyCi9wRq-FHyUvLNLuhxLFdj8MVzjp0Rj3I".strip()
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()
MAIL_USER = os.getenv("MAIL_USER", "").strip()
MAIL_PASS = os.getenv("MAIL_PASS", "").strip()

# 针对思创数码品牌市场部定制的搜索词
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
    """步骤 1: 搜集最新的数字发改资讯"""
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
    """步骤 2: 调用 Gemini 进行专家级汇总"""
    if not news_list: return None
    
    model_name = get_actual_model()
    if not model_name:
        print(">>> 严重错误：诊断列表仍为空。请稍等 5 分钟，确保 Google Cloud 的‘不限制密钥’设置生效。")
        return None
    
    print(f">>> 选定可用模型: {model_name}")
    news_text = "\n".join([f"- {n['title']}: {n.get('snippet','')}" for n in news_list[:10]])
    
    # 结合思创数码 35 周年背景的提示词
    prompt = f"""
    你是一个资深的数字发改专家。请将以下资讯整理成 HTML 简报。
    作为思创数码(Thinvent)品牌市场部的一员，请在末尾结合今日动态，为公司 35 周年庆典或品牌推广提供一条业务建议。
    数据：{news_text}
    """

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={AI_API_KEY}"
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        res_json = response.json()
        if 'candidates' in res_json:
            print(">>> AI 响应成功，已生成报告内容。")
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f">>> AI 响应异常: {json.dumps(res_json)}")
            return None
    except Exception as e:
        print(f">>> AI 请求出错: {e}")
        return None

def send_email(html_body):
    """步骤 3: 通过 SMTP 发送精美简报"""
    if not html_body: return
    print("正在准备发送简报邮件...")
    today = datetime.now().strftime('%Y-%m-%d')
    full_html = f"""
    <div style="font-family: Arial; padding: 20px; max-width: 600px; margin: auto; border: 1px solid #eee; border-radius: 10px;">
        <h2 style="color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 10px;">数字发改 · 每日决策内参</h2>
        <div style="line-height: 1.6;">{html_body}</div>
        <div style="margin-top: 30px; font-size: 12px; color: #999; text-align: center;">
            思创数码品牌市场部 · 35周年自动化特刊
        </div>
    </div>
    """
    
    msg = MIMEText(full_html, 'html', 'utf-8')
    msg['From'] = f"资讯助手 <{MAIL_USER}>"
    msg['To'] = ",".join(RECEIVERS)
    msg['Subject'] = Header(f"【每日内参】数字发改业务动态 ({today})", 'utf-8')

    try:
        # 使用 QQ 邮箱服务器，端口 465
        smtp = smtplib.SMTP_SSL("smtp.qq.com", 465)
        smtp.login(MAIL_USER, MAIL_PASS)
        smtp.sendmail(MAIL_USER, RECEIVERS, msg.as_string())
        smtp.quit()
        print("Done: 简报已成功送达您的邮箱！")
    except Exception as e:
        print(f"邮件发送失败: {e}")

if __name__ == "__main__":
    # 执行主业务逻辑
    news = get_search_results()
    if news:
        report = summarize_with_ai(news)
        if report:
            send_email(report)
    else:
        print("今日暂无符合关键词的新资讯更新。")
