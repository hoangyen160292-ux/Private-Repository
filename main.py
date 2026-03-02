import os
import requests
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header

# --- 1. 基础配置 (自动读取 GitHub Secrets) ---
SERPER_API_KEY = os.getenv("SERPER_API_KEY") 
AI_API_KEY = os.getenv("AI_API_KEY")
MAIL_USER = os.getenv("MAIL_USER")
MAIL_PASS = os.getenv("MAIL_PASS")

# 针对思创数码业务优化的搜索关键词
SEARCH_QUERY = "数字发改 政策 数字化转型 数据要素 江西省 招标公示"
# 默认发给自己（若要发给多人可写成 ["381248017@qq.com", "b@qq.com"]）
RECEIVERS = [MAIL_USER] 

def get_search_results():
    """使用 Serper 获取全网最新的数字发改资讯"""
    print("正在搜集数字发改相关资讯...")
    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": SEARCH_QUERY,
        "gl": "cn",
        "hl": "zh-cn",
        "tbs": "qdr:d" # 过去24小时
    })
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    try:
        response = requests.post(url, headers=headers, data=payload)
        return response.json().get('organic', [])
    except Exception as e:
        print(f"搜索失败: {e}")
        return []

def summarize_with_ai(news_list):
    """直接调用 Google Gemini 原生接口进行汇总"""
    print("正在通过 Google 原生接口调用 Gemini...")
    if not news_list: return None
        
    raw_text = "\n".join([f"标题: {n['title']}\n内容: {n.get('snippet','')}\n链接: {n['link']}" for n in news_list[:8]])
    
    # 结合思创数码35周年背景的定制化 Prompt
    prompt = f"""
    你是一个资深的数字发改行业分析师。请根据以下数据整理一份《数字发改每日简报》。
    要求：
    1. 分为：[政策动态]、[地方实践]、[业务机会] 三个板块。
    2. 每条资讯包含标题、100字内的摘要及来源链接。
    3. 特别注意：我司“思创数码(Thinvent)”正值35周年，总部位于南昌。请在简报末尾结合今日资讯，为我司品牌市场部提供一条业务拓展建议。
    4. 输出格式必须为纯 HTML 内容，不要包含 ```html 等标签。
    数据：{raw_text}
    """

    # --- 关键：使用 Google 官方原生地址 ---
    url = f"[https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key=](https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key=){AI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, json=payload)
        res_json = response.json()
        # 针对原生接口的解析逻辑
        if 'candidates' in res_json:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"AI 响应异常: {res_json}")
            return None
    except Exception as e:
        print(f"AI 调用失败: {e}")
        return None

def send_email(html_body):
    """通过 SMTP 发送邮件"""
    if not html_body: return
    print("正在准备发送邮件...")
    today = datetime.now().strftime('%Y-%m-%d')
    full_html = f"""
    <html>
    <body style="font-family: Arial; padding: 20px;">
        <div style="max-width: 600px; margin: auto; border: 1px solid #ddd; border-radius: 10px;">
            <div style="background: #1a73e8; color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                <h2 style="margin: 0;">数字发改 · 每日内参</h2>
                <p style="margin: 5px 0 0; opacity: 0.8;">{today} | 思创数码品牌市场部</p>
            </div>
            <div style="padding: 20px;">{html_body}</div>
        </div>
    </body>
    </html>
    """
    
    msg = MIMEText(full_html, 'html', 'utf-8')
    msg['From'] = f"发改资讯助手 <{MAIL_USER}>"
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
    news = get_search_results()
    if news:
        report = summarize_with_ai(news)
        send_email(report)
    else:
        print("今日无符合关键词的新闻更新。")
