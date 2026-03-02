import os
import requests
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header

# --- 1. 配置区 ---
SERPER_API_KEY = os.getenv("SERPER_API_KEY") 
AI_API_KEY = os.getenv("AI_API_KEY")
MAIL_USER = os.getenv("MAIL_USER")
MAIL_PASS = os.getenv("MAIL_PASS")

# 针对思创数码业务优化的搜索关键词
SEARCH_QUERY = "数字发改 政策 数字化转型 数据要素 江西省 招标公示"
RECEIVERS = [MAIL_USER] 

def get_search_results():
    print("正在搜集数字发改相关资讯...")
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": SEARCH_QUERY, "gl": "cn", "hl": "zh-cn", "tbs": "qdr:d"})
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    try:
        response = requests.post(url, headers=headers, data=payload)
        return response.json().get('organic', [])
    except Exception as e:
        print(f"搜索失败: {e}")
        return []

def summarize_with_ai(news_list):
    print("正在通过 Google 原生接口调用 Gemini...")
    if not news_list: return None
    
    raw_text = "\n".join([f"标题: {n['title']}\n摘要: {n.get('snippet','')}\n链接: {n['link']}" for n in news_list[:8]])
    
    prompt = f"""你是一个数字发改专家。请将以下资讯整理成简洁的 HTML 简报。
    由于我司思创数码正在庆祝35周年，请在末尾为品牌市场部提供一条建议。
    原始数据：{raw_text}"""

    # 关键点：这一行必须是干净的引号开头，不能有方括号
    api_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={AI_API_KEY}"
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        # 移除可能存在的隐形字符
        api_url = api_url.strip()
        response = requests.post(api_url, json=payload)
        res_json = response.json()
        if 'candidates' in res_json:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"AI 响应异常: {res_json}")
            return None
    except Exception as e:
        print(f"AI 调用失败: {e}")
        return None

def send_email(html_body):
    if not html_body: return
    print("正在准备发送邮件...")
    today = datetime.now().strftime('%Y-%m-%d')
    full_html = f"<html><body><div style='padding:20px; border:1px solid #eee;'>{html_body}</div></body></html>"
    
    msg = MIMEText(full_html, 'html', 'utf-8')
    msg['From'] = f"资讯助手 <{MAIL_USER}>"
    msg['To'] = ",".join(RECEIVERS)
    msg['Subject'] = Header(f"【每日内参】数字发改业务动态 ({today})", 'utf-8')

    try:
        smtp = smtplib.SMTP_SSL("smtp.qq.com", 465)
        smtp.login(MAIL_USER, MAIL_PASS)
        smtp.sendmail(MAIL_USER, RECEIVERS, msg.as_string())
        print("Done: 邮件已发送成功！")
    except Exception as e:
        print(f"邮件发送失败: {e}")

if __name__ == "__main__":
    # 简单的环境检查
    if not all([SERPER_API_KEY, AI_API_KEY, MAIL_USER, MAIL_PASS]):
        print("错误：Secrets 配置不完整，请检查 GitHub Settings。")
    else:
        news = get_search_results()
        if news:
            report = summarize_with_ai(news)
            send_email(report)
        else:
            print("今日暂无新资讯。")
