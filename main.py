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

# 重点：修改为 Gemini 的 OpenAI 兼容接口地址
AI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai" 
SEARCH_QUERY = "数字发改 政策 数字化转型 数据要素 江西省 招标公示"
# 请在这里填入你的收件人邮箱
RECEIVERS = ["381248017@qq.com"] 

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
    print("正在调用 Gemini 进行分析汇总...")
    raw_text = "\n".join([f"标题: {n['title']}\n摘要: {n.get('snippet','')}\n链接: {n['link']}" for n in news_list[:8]])
    
    prompt = f"你是一个数字发改专家。请将以下资讯整理成 HTML 简报（包含政策导向、地方实践、行业动态），并附带业务点评。原始数据：{raw_text}"

    headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "gemini-1.5-flash", # 使用 Gemini Flash 模型
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5
    }
    
    try:
        response = requests.post(f"{AI_BASE_URL}/chat/completions", headers=headers, json=data)
        res_json = response.json()
        
        # 增加安全检查，防止列表索引报错
        if 'choices' in res_json:
            return res_json['choices'][0]['message']['content']
        else:
            print(f"AI 响应异常: {res_json}")
            return None
    except Exception as e:
        print(f"AI 总结失败: {e}")
        return None

def send_email(html_content):
    if not html_content: return
    print("正在发送邮件...")
    mail_user = os.getenv("MAIL_USER")
    mail_pass = os.getenv("MAIL_PASS")
    
    msg = MIMEText(html_content, 'html', 'utf-8')
    msg['From'] = mail_user
    msg['To'] = ",".join(RECEIVERS)
    msg['Subject'] = Header(f"【数字发改】每日业务动态 ({datetime.now().strftime('%Y-%m-%d')})", 'utf-8')

    try:
        smtp = smtplib.SMTP_SSL("smtp.qq.com", 465) # 这里以QQ邮箱为例
        smtp.login(mail_user, mail_pass)
        smtp.sendmail(mail_user, RECEIVERS, msg.as_string())
        print("Done: 简报已发送成功")
    except Exception as e:
        print(f"邮件发送失败: {e}")

if __name__ == "__main__":
    news = get_search_results()
    if news:
        report = summarize_with_ai(news)
        send_email(report)
    else:
        print("今日无相关业务资讯更新。")
