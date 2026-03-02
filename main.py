import os
import requests
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header

# --- 1. 核心配置 ---
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
AI_API_KEY = os.getenv("AI_API_KEY")
MAIL_USER = os.getenv("MAIL_USER")
MAIL_PASS = os.getenv("MAIL_PASS")

# 针对思创数码业务优化的关键词
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
    print("正在通过 Gemini v1beta 接口进行汇总...")
    if not news_list: return None
    
    # 提取前8条新闻
    raw_text = "\n".join([f"标题: {n['title']}\n摘要: {n.get('snippet','')}\n链接: {n['link']}" for n in news_list[:8]])
    
    prompt = f"""你是一个数字发改专家。请将以下资讯整理成 HTML 简报。
    作为思创数码(Thinvent)的一员，请在末尾为品牌市场部提供一条关于35周年的业务建议。
    原始数据：{raw_text}"""

    # --- 修复核心：使用 v1beta 路径并确保 URL 绝对纯净 ---
    # 这里的 URL 不允许有任何空格或方括号
    base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    full_url = f"{base_url}?key={AI_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        # 使用 .strip() 彻底清理可能存在的隐形换行符
        response = requests.post(full_url.strip(), json=payload, timeout=30)
        res_json = response.json()
        
        if 'candidates' in res_json:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            # 打印完整的错误响应，方便我们精准排查
            print(f"AI 响应内容详情: {json.dumps(res_json, indent=2)}")
            return None
    except Exception as e:
        print(f"网络请求失败: {e}")
        return None

def send_email(html_body):
    if not html_body: return
    print("正在发送内参邮件...")
    today = datetime.now().strftime('%Y-%m-%d')
    # 简单的外观封装
    email_content = f"""
    <div style="font-family:sans-serif; max-width:600px; margin:auto; border:1px solid #eee; padding:20px;">
        <h2 style="color:#1a73e8;">数字发改 · 每日内参</h2>
        <hr>
        {html_body}
        <p style="font-size:12px; color:#999; margin-top:30px;">思创数码品牌市场部 · 自动化推送</p>
    </div>
    """
    
    msg = MIMEText(email_content, 'html', 'utf-8')
    msg['From'] = f"资讯助手 <{MAIL_USER}>"
    msg['To'] = ",".join(RECEIVERS)
    msg['Subject'] = Header(f"【每日内参】数字发改业务动态 ({today})", 'utf-8')

    try:
        smtp = smtplib.SMTP_SSL("smtp.qq.com", 465)
        smtp.login(MAIL_USER, MAIL_PASS)
        smtp.sendmail(MAIL_USER, RECEIVERS, msg.as_string())
        print("Done: 邮件已成功送达！")
    except Exception as e:
        print(f"邮件发送环节出错: {e}")

if __name__ == "__main__":
    # 安全检查
    if not all([SERPER_API_KEY, AI_API_KEY, MAIL_USER, MAIL_PASS]):
        print("错误：Secrets 变量缺失，请检查 GitHub 设置。")
    else:
        news = get_search_results()
        if news:
            report = summarize_with_ai(news)
            send_email(report)
        else:
            print("今日未发现符合条件的江西数字发改资讯。")
