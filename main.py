import os
import requests
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header

# --- 1. 核心配置 (已按要求硬编码) ---
# 注意：SERPER_API_KEY 仍建议从环境变量读取，或你也直接填入字符串
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip() 
AI_API_KEY = "AIzaSyCi9wRq-FHyUvLNLuhxLFdj8MVzjp0Rj3I"
MAIL_USER = os.getenv("MAIL_USER", "").strip()
MAIL_PASS = os.getenv("MAIL_PASS", "").strip()

# 业务关键词：江西数字发改、数字化转型
SEARCH_QUERY = "数字发改 政策 数字化转型 数据要素 江西省 招标公示"
RECEIVERS = [MAIL_USER] 

def get_search_results():
    print("正在搜集数字发改资讯...")
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
    print(f"搜集到 {len(news_list)} 条动态，正在通过硬编码 Key 调用 Gemini...")

    news_text = "\n".join([f"- {n['title']}: {n.get('snippet','')}" for n in news_list[:8]])
    prompt = f"""你是一个数字发改专家。请将以下资讯整理成 HTML 简报。
    由于我司思创数码正在庆祝35周年，请在简报末尾为品牌市场部提供一条业务建议。
    同时，请额外增加一个“技术风向标”小板块，简述一项与今日动态相关的全球前沿技术动态。
    原始数据：{news_text}"""

    # --- 彻底纯净的 URL，不加任何外部变量拼接 ---
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={AI_API_KEY}"
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        res_json = response.json()
        
        if 'candidates' in res_json:
            print("AI 响应成功！")
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"AI 响应依然异常: {json.dumps(res_json)}")
            return None
    except Exception as e:
        print(f"请求环节出错: {e}")
        return None

def send_email(content):
    if not content: return
    print("正在发送简报邮件...")
    today = datetime.now().strftime('%Y-%m-%d')
    full_html = f"<html><body style='padding:20px;'>{content}</body></html>"
    
    msg = MIMEText(full_html, 'html', 'utf-8')
    msg['From'] = f"资讯助手 <{MAIL_USER}>"
    msg['To'] = ",".join(RECEIVERS)
    msg['Subject'] = Header(f"【决策内参】数字发改业务动态 ({today})", 'utf-8')

    try:
        smtp = smtplib.SMTP_SSL("smtp.qq.com", 465)
        smtp.login(MAIL_USER, MAIL_PASS)
        smtp.sendmail(MAIL_USER, RECEIVERS, msg.as_string())
        print("Done: 简报已成功送达！")
    except Exception as e:
        print(f"邮件发送失败: {e}")

if __name__ == "__main__":
    news = get_search_results()
    if news:
        report = summarize_with_ai(news)
        if report: send_email(report)
    else:
        print("今日无资讯更新。")
