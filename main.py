import os
import requests
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header

# --- 1. 核心配置 (自动读取 Secrets) ---
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()
AI_API_KEY = os.getenv("AI_API_KEY", "").strip()
MAIL_USER = os.getenv("MAIL_USER", "").strip()
MAIL_PASS = os.getenv("MAIL_PASS", "").strip()

# 针对思创数码(Thinvent)业务优化的关键词
SEARCH_QUERY = "数字发改 政策 数字化转型 数据要素 江西省 招标公示"
RECEIVERS = [MAIL_USER] 

def get_search_results():
    print("正在搜索江西及全国数字发改资讯...")
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
    if not news_list: return None
    print(f"搜集到 {len(news_list)} 条动态，正在调用 Gemini 分析...")

    news_text = "\n".join([f"- {n['title']}: {n.get('snippet','')}" for n in news_list[:8]])
    prompt = f"你是一个数字发改专家。请将以下资讯整理成 HTML 简报。作为思创数码(Thinvent)的一员，请在末尾为品牌市场部提供一条关于35周年的建议。数据：{news_text}"

    # --- 防错处理：确保 URL 绝对纯净 ---
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={AI_API_KEY}"
    
    # 这一行会自动删除复制时可能带入的 [ ] ( ) 和空格
    api_url = api_url.replace('[', '').replace(']', '').split('(')[0].strip()
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(api_url, json=payload, timeout=30)
        res_json = response.json()
        if 'candidates' in res_json:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"AI 响应异常: {json.dumps(res_json)}")
            return None
    except Exception as e:
        print(f"AI 请求失败: {e}")
        return None

def send_email(content):
    if not content: return
    print("正在发送内参邮件...")
    today = datetime.now().strftime('%Y-%m-%d')
    # 封装精美 HTML 外壳
    full_html = f"""
    <div style="font-family:Arial; max-width:600px; margin:auto; border:1px solid #eee; padding:20px; border-radius:10px;">
        <h2 style="color:#1a73e8; border-bottom:2px solid #1a73e8; padding-bottom:10px;">数字发改 · 每日内参</h2>
        {content}
        <div style="margin-top:30px; padding-top:10px; border-top:1px solid #eee; font-size:12px; color:#999;">
            思创数码品牌市场部 · 35周年自动化内参系统
        </div>
    </div>
    """
    
    msg = MIMEText(full_html, 'html', 'utf-8')
    msg['From'] = f"资讯助手 <{MAIL_USER}>"
    msg['To'] = ",".join(RECEIVERS)
    msg['Subject'] = Header(f"【每日内参】数字发改业务动态 ({today})", 'utf-8')

    try:
        smtp = smtplib.SMTP_SSL("smtp.qq.com", 465)
        smtp.login(MAIL_USER, MAIL_PASS)
        smtp.sendmail(MAIL_USER, RECEIVERS, msg.as_string())
        print("Done: 简报已成功送达您的邮箱！")
    except Exception as e:
        print(f"邮件发送失败: {e}")

if __name__ == "__main__":
    if not all([SERPER_API_KEY, AI_API_KEY, MAIL_USER, MAIL_PASS]):
        print("错误：Secrets 配置不完整。")
    else:
        news = get_search_results()
        if news:
            report = summarize_with_ai(news)
            if report: send_email(report)
        else:
            print("今日暂无资讯更新。")
