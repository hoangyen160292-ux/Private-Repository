import os
import requests
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header

# --- 1. 搜索配置 (推荐使用 Serper.dev，每月2500次免费，极其稳定) ---
SERPER_API_KEY = os.getenv("SERPER_API_KEY") 
SEARCH_QUERY = "数字发改 政策 数字化转型 数据要素 江西省 招标公示"

# --- 2. AI 配置 (适配 Google AI Studio) ---
AI_API_KEY = os.getenv("AI_API_KEY")
# 使用 Gemini 的 OpenAI 兼容模式地址
AI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"

def get_search_results():
    """从全网获取最新的行业资讯"""
    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": SEARCH_QUERY,
        "gl": "cn",
        "hl": "zh-cn",
        "tbs": "qdr:d" # 仅限过去24小时
    })
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    return response.json().get('organic', [])

def summarize_with_ai(news_list):
    """调用AI对搜索结果进行分类、总结和点评"""
    # 将搜索结果拼接成文本
    raw_text = "\n".join([f"标题: {n['title']}\n内容: {n.get('snippet','')}\n链接: {n['link']}" for n in news_list[:8]])
    
    prompt = f"""
    你是一个数字发改行业的资深分析师。请将以下搜索到的原始资讯整理成一份精美的《数字发改每日简报》。
    要求：
    1. 分为：[政策导向]、[地方实践]、[行业动态] 三个板块。
    2. 每条资讯包含标题、100字以内的核心摘要。
    3. 在每条后面附带一个【AI点评】，分析该资讯对业务的潜在影响。
    4. 使用HTML格式输出，不要包含 ```html 标签。
    原始数据：{raw_text}
    """

    headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "gemini-1.5-flash",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5
    }
    response = requests.post(f"{AI_BASE_URL}/chat/completions", headers=headers, json=data)
    return response.json()['choices'][0]['message']['content']

def send_email(html_body):
    """发送邮件"""
    today = datetime.now().strftime('%Y-%m-%d')
    mail_user = os.getenv("MAIL_USER")
    mail_pass = os.getenv("MAIL_PASS")
    receivers = ["381248017@qq.com"] # 替换为你的批量邮箱列表

    # 注入 HTML 模板头尾（见下文）
    full_html = get_full_html_template(today, html_body)

    message = MIMEText(full_html, 'html', 'utf-8')
    message['From'] = f"发改资讯助手 <{mail_user}>"
    message['To'] = ",".join(receivers)
    message['Subject'] = Header(f"【数字发改】每日业务动态简报 ({today})", 'utf-8')

    try:
        smtp = smtplib.SMTP_SSL("smtp.qq.com", 465)
        smtp.login(mail_user, mail_pass)
        smtp.sendmail(mail_user, receivers, message.as_string())
        print("Done: 简报已发送成功")
    except Exception as e:
        print(f"Error: {e}")

# 这里放入 HTML 模板函数（下文提供）
def get_full_html_template(date_str, content):
    # 拼接下方的 HTML 代码...
    pass

if __name__ == "__main__":
    news = get_search_results()
    if news:
        report = summarize_with_ai(news)
        send_email(report)
