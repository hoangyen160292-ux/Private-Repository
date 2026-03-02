import os
import requests
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header

# --- 1. 核心配置 (安全读取，不留痕迹) ---
# 请确保已在 GitHub 仓库的 Settings > Secrets > Actions 中添加了 AI_API_KEY
AI_API_KEY = os.getenv("AI_API_KEY", "").strip()
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()
MAIL_USER = os.getenv("MAIL_USER", "").strip()
MAIL_PASS = os.getenv("MAIL_PASS", "").strip()

# 业务关键词：江西数字发改、数字化转型
SEARCH_QUERY = "数字发改 政策 数字化转型 数据要素 江西省 招标公示"
RECEIVERS = [MAIL_USER] 

def get_actual_model():
    """实时诊断：确认新 Key 的可用模型"""
    if not AI_API_KEY:
        print(">>> 错误：未在 GitHub Secrets 中检测到 AI_API_KEY。")
        return None
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={AI_API_KEY}"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        if "error" in data:
            print(f">>> API 异常详情: {data['error'].get('message', '未知错误')}")
            return None
            
        models = [m['name'].split('/')[-1] for m in data.get('models', []) if 'generateContent' in m.get('supportedMethods', [])]
        print(f">>> 诊断：当前模型权限列表: {models}")
        
        # 优先使用 flash 模型
        for target in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]:
            if target in models: return target
        return models[0] if models else None
    except Exception as e:
        print(f">>> 连接诊断接口失败: {e}")
        return None

def get_search_results():
    """第一步：搜集江西省数字发改资讯"""
    print("正在搜集江西及全国数字发改资讯...")
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
    """第二步：调用 AI 生成专家内参"""
    if not news_list: return None
    
    model_name = get_actual_model()
    if not model_name: return None
    
    print(f">>> 选定可用模型: {model_name}")
    news_text = "\n".join([f"- {n['title']}: {n.get('snippet','')}" for n in news_list[:10]])
    
    # 结合 35 周年背景的业务指令
    prompt = f"""
    你是一个江西数字发改专家。请将以下资讯整理成 HTML 简报。
    作为思创数码(Thinvent)的一员，请在简报末尾结合今日动态，为公司 35 周年品牌推广提供一条业务拓展建议。
    资讯内容：{news_text}
    """

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={AI_API_KEY}"
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        res_json = response.json()
        if 'candidates' in res_json:
            print(">>> AI 分析总结成功！")
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f">>> AI 响应详情: {json.dumps(res_json)}")
            return None
    except Exception as e:
        print(f">>> 调用失败: {e}")
        return None

def send_email(html_body):
    """第三步：发送精美 HTML 简报"""
    if not html_body: return
    print("正在发送内参邮件...")
    today = datetime.now().strftime('%Y-%m-%d')
    full_html = f"""
    <html>
    <body style="font-family: Arial; padding: 20px;">
        <h2 style="color: #1a73e8; border-bottom: 2px solid #1a73e8;">数字发改 · 每日内参</h2>
        <div>{html_body}</div>
        <hr style="border: none; border-top: 1px solid #eee; margin-top: 30px;">
        <p style="color: #999; font-size: 12px;">思创数码 35 周年 · 自动化内参推送</p>
    </body>
    </html>
    """
    
    msg = MIMEText(full_html, 'html', 'utf-8')
    msg['From'] = f"资讯助手 <{MAIL_USER}>"
    msg['To'] = ",".join(RECEIVERS)
    msg['Subject'] = Header(f"【决策内参】数字发改业务动态 ({today})", 'utf-8')

    try:
        smtp = smtplib.SMTP_SSL("smtp.qq.com", 465)
        smtp.login(MAIL_USER, MAIL_PASS)
        smtp.sendmail(MAIL_USER, RECEIVERS, msg.as_string())
        print("Done: 简报已成功送达您的邮箱！")
    except Exception as e:
        print(f"发送邮件出错: {e}")

if __name__ == "__main__":
    news = get_search_results()
    if news:
        report = summarize_with_ai(news)
        if report:
            send_email(report)
    else:
        print("今日暂无新资讯。")
