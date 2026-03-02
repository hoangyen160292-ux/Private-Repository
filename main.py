import os
import requests
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header

# --- 1. 环境与配置检查 ---
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()
AI_API_KEY = os.getenv("AI_API_KEY", "").strip()
MAIL_USER = os.getenv("MAIL_USER", "").strip()
MAIL_PASS = os.getenv("MAIL_PASS", "").strip()

# 关键词针对思创数码业务优化
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
        print(f"搜索环节失败: {e}")
        return []

def summarize_with_ai(news_list):
    """双模型备份机制，解决 404 报错"""
    if not news_list: return None
    
    raw_text = "\n".join([f"标题: {n['title']}\n摘要: {n.get('snippet','')}\n链接: {n['link']}" for n in news_list[:8]])
    prompt = f"你是一个数字发改专家。请将以下资讯整理成 HTML 简报。作为思创数码(Thinvent)的一员，请在末尾为品牌市场部提供一条关于35周年的业务建议。原始数据：{raw_text}"

    # 依次尝试的模型列表
    models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
    
    for model_name in models:
        print(f"正在尝试使用 {model_name} 进行分析...")
        # 使用 v1 稳定版接口
        api_url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent?key={AI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        try:
            response = requests.post(api_url, json=payload, timeout=30)
            res_json = response.json()
            
            if 'candidates' in res_json:
                print(f"成功！已通过 {model_name} 生成内容。")
                return res_json['candidates'][0]['content']['parts'][0]['text']
            else:
                print(f"模型 {model_name} 反馈异常，准备尝试下一个。详情: {res_json.get('error', {}).get('message', '未知错误')}")
        except Exception as e:
            print(f"请求 {model_name} 失败: {e}")
            
    print("所有可用模型均无法调用，请检查 API Key 权限。")
    return None

def send_email(html_body):
    if not html_body: return
    print("正在准备发送邮件...")
    today = datetime.now().strftime('%Y-%m-%d')
    full_html = f"""
    <div style="font-family:Arial; max-width:600px; margin:auto; border:1px solid #eee; padding:20px; border-radius:10px;">
        <h2 style="color:#1a73e8; border-bottom:2px solid #1a73e8; padding-bottom:10px;">数字发改 · 每日决策内参</h2>
        {html_body}
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
    if not AI_API_KEY or len(AI_API_KEY) < 10:
        print("错误：AI_API_KEY 读取失败，请检查 GitHub Secrets 配置。")
    else:
        news = get_search_results()
        if news:
            report = summarize_with_ai(news)
            send_email(report)
        else:
            print("今日暂无符合条件的资讯更新。")
