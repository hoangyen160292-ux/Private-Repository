import os
import requests
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header

# --- 1. 配置区 (自动读取 GitHub Secrets) ---
SERPER_API_KEY = os.getenv("SERPER_API_KEY") 
AI_API_KEY = os.getenv("AI_API_KEY")
MAIL_USER = os.getenv("MAIL_USER")
MAIL_PASS = os.getenv("MAIL_PASS")

# 针对思创数码业务优化的搜索关键词
SEARCH_QUERY = "数字发改 政策 数字化转型 数据要素 江西省 招标公示"
# 在此处填入你的批量收件人邮箱
RECEIVERS = [MAIL_USER]  # 默认发给自己，若发给多人请写成 ["a@qq.com", "b@qq.com"]

def get_search_results():
    """使用 Serper 搜集最新的行业资讯"""
    print("正在搜集数字发改相关资讯...")
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
    try:
        response = requests.post(url, headers=headers, data=payload)
        return response.json().get('organic', [])
    except Exception as e:
        print(f"搜索失败: {e}")
        return []

def summarize_with_ai(news_list):
    """调用 Gemini 原生接口进行分析汇总"""
    print("正在调用 Gemini 进行分析汇总...")
    if not news_list:
        return None
        
    raw_text = "\n".join([f"标题: {n['title']}\n摘要: {n.get('snippet','')}\n链接: {n['link']}" for n in news_list[:10]])
    
    # 结合思创数码35周年背景的定制化 Prompt
    prompt = f"""
    你是一个资深的数字发改行业分析师。请根据以下原始数据，整理一份《数字发改每日简报》。
    要求：
    1. 分为：[政策动向]、[地方实践]、[业务机会] 三个板块。
    2. 每条资讯包含标题、100字内的摘要。
    3. 特别注意：我司“思创数码(Thinvent)”正值35周年，总部位于南昌。请在简报末尾结合今日资讯，为我司品牌市场部提供一条业务拓展或品牌传播建议。
    4. 输出格式必须为纯 HTML 内容，不要包含 ```html 等标签。
    
    数据：{raw_text}
    """

    # Gemini 原生 REST 接口
    url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=){AI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, json=payload)
        res_json = response.json()
        if 'candidates' in res_json:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"AI 响应异常: {res_json}")
            return None
    except Exception as e:
        print(f"AI 调用失败: {e}")
        return None

def get_html_template(date_str, content):
    """高颜值 HTML 邮件模板"""
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <div style="max-width: 650px; margin: 0 auto; border: 1px solid #ddd; border-radius
