import os
import requests
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header

# --- 1. 配置读取 (带自动清洗功能) ---
def get_clean_env(name):
    # 自动剔除可能存在的方括号、括号、引号和空格
    val = os.getenv(name, "").strip()
    return val.replace('[', '').replace(']', '').replace('(', '').replace(')', '').replace('"', '').replace("'", "")

SERPER_API_KEY = get_clean_env("SERPER_API_KEY")
AI_API_KEY = get_clean_env("AI_API_KEY")
MAIL_USER = get_clean_env("MAIL_USER")
MAIL_PASS = get_clean_env("MAIL_PASS")

SEARCH_QUERY = "数字发改 政策 数字化转型 数据要素 江西省 招标公示"
RECEIVERS = [MAIL_USER]

def get_search_results():
    print("正在搜集江西及全国数字发改资讯...")
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    payload = json.dumps({"q": SEARCH_QUERY, "gl": "cn", "hl": "zh-cn", "tbs": "qdr:d"})
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=20)
        return response.json().get('organic', [])
    except Exception as e:
        print(f"搜索环节出错: {e}")
        return []

def summarize_with_ai(news_list):
    if not news_list: return None
    print(f"搜集到 {len(news_list)} 条动态，正在调用 Gemini 分析...")

    news_text = "\n".join([f"- {n['title']}: {n.get('snippet','')}" for n in news_list[:8]])
    prompt = f"你是一个数字发改专家。请将以下资讯整理成 HTML 简报。作为思创数码(Thinvent)的一员，请在末尾为品牌市场部提供一条建议。数据：{news_text}"

    # --- 核心修复：纯净的 URL 拼接 ---
    base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    full_url = f"{base_url}?key={AI_API_KEY}"
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        # 这里再次确保 full_url 不含任何 Markdown 杂质
        clean_url = full_url.split(']')[0].split(')')[0].strip()
        response = requests.post(clean_url, json=payload, timeout=30)
        res_json = response.json()
        
        if 'candidates' in res_json:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"AI 响应详情: {json.dumps(res_json)}")
            return None
    except Exception as e:
        print(f"AI 调用阶段出错: {e}")
        return None

def send_email(content):
    if not content: return
    print("正在准备发送邮件...")
    today = datetime.now().strftime('%Y-%m-%d')
    html_msg = f"<html><body style='font-family:Arial; padding:20px;'>{content}</body></html>"
    
    msg = MIMEText(html_msg, 'html', 'utf-8')
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
    if not all([SERPER_API_KEY, AI_API_KEY, MAIL_USER, MAIL_PASS]):
        print("错误：Secrets 配置不全。")
    else:
        news = get_search_results()
        if news:
            report = summarize_with_ai(news)
            if report: send_email(report)
        else:
            print("今日暂无新资讯更新。")
