import os
import requests
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header

# --- 1. 基础配置 (自动从 GitHub Secrets 读取) ---
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()
AI_API_KEY = os.getenv("AI_API_KEY", "").strip()
MAIL_USER = os.getenv("MAIL_USER", "").strip()
MAIL_PASS = os.getenv("MAIL_PASS", "").strip()

# 针对思创数码(Thinvent)业务优化的搜索关键词
SEARCH_QUERY = "数字发改 政策 数字化转型 数据要素 江西省 招标公示"
# 默认发给自己的邮箱，若需发给多人可改为 ["email1", "email2"]
RECEIVERS = [MAIL_USER] 

def get_search_results():
    """使用 Serper 获取全网最新的数字发改资讯"""
    print("正在搜索江西及全国数字发改资讯...")
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    payload = json.dumps({
        "q": SEARCH_QUERY,
        "gl": "cn",
        "hl": "zh-cn",
        "tbs": "qdr:d"  # 仅限过去24小时
    })
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=20)
        return response.json().get('organic', [])
    except Exception as e:
        print(f"搜索环节出错: {e}")
        return []

def summarize_with_ai(news_list):
    """通过 Gemini v1beta 接口生成业务内参"""
    if not news_list:
        return None
    
    print(f"搜集到 {len(news_list)} 条动态，正在调用 Gemini 进行专家级汇总...")
    
    # 格式化新闻列表供 AI 阅读
    news_content = "\n".join([f"标题: {n['title']}\n摘要: {n.get('snippet','')}\n链接: {n['link']}" for n in news_list[:10]])
    
    # 结合思创数码(Thinvent)35周年及品牌市场部背景的提示词
    prompt = f"""
    你是一个资深的数字发改行业专家。请根据以下原始资讯，为“思创数码(Thinvent)”品牌市场部整理一份 HTML 格式的每日内参。
    
    要求：
    1. 分为 [政策要闻]、[江西动态]、[招标/市场机会] 三大板块。
    2. 每条资讯包含标题、100字内的核心提炼、以及来源链接。
    3. 特别任务：由于我司思创数码正值35周年，总部位于南昌。请在简报末尾结合今日动态，提供一条具体的品牌公关或业务拓展建议。
    4. 仅输出 HTML 内容，不要包含任何 Markdown 标识符(如 ```html )。
    
    数据源：
    {news_content}
    """

    # --- 核心修复：使用 v1beta 路径，适配已启用 API 的项目 ---
    url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=){AI_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        res_json = response.json()
        
        if 'candidates' in res_json:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            # 在日志中打印详细报错，方便排查
            print(f"AI 响应异常详情: {json.dumps(res_json, indent=2)}")
            return None
    except Exception as e:
        print(f"AI 调用失败: {e}")
        return None

def send_email(html_body):
    """发送 HTML 格式的精美邮件"""
    if not html_body:
        return
    
    print("正在通过邮件服务器发送简报...")
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 封装高颜值邮件外壳
    full_html = f"""
    <html>
    <body style="font-family: 'Microsoft YaHei', sans-serif; background-color: #f4f7f9; padding: 20px;">
        <div style="max-width: 650px; margin: auto; background: white; border-radius: 12px; overflow: hidden; border: 1px solid #e1e4e8;">
            <div style="background: #1a73e8; color: white; padding: 25px; text-align: center;">
                <h1 style="margin: 0; font-size: 24px;">数字发改 · 每日决策内参</h1>
                <p style="margin: 8px 0 0; opacity: 0.9;">{today} | 思创数码 35周年特刊</p>
            </div>
            <div style="padding: 30px; line-height: 1.8; color: #333;">
                {html_body}
            </div>
            <div style="background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #999;">
                本内参由 AI 自动化生成，仅供思创数码品牌市场部内部参考。
            </div>
        </div>
    </body>
    </html>
    """
    
    msg = MIMEText(full_html, 'html', 'utf-8')
    msg['From'] = f"发改资讯助手 <{MAIL_USER}>"
    msg['To'] = ",".join(RECEIVERS)
    msg['Subject'] = Header(f"【决策内参】数字发改业务动态 ({today})", 'utf-8')

    try:
        # 默认使用 QQ 邮箱服务器，如需更换请修改此处
        smtp = smtplib.SMTP_SSL("smtp.qq.com", 465)
        smtp.login(MAIL_USER, MAIL_PASS)
        smtp.sendmail(MAIL_USER, RECEIVERS, msg.as_string())
        smtp.quit()
        print("Done: 简报已成功发送至邮箱！")
    except Exception as e:
        print(f"发送邮件失败: {e}")

if __name__ == "__main__":
    # 环境自检
    if not all([SERPER_API_KEY, AI_API_KEY, MAIL_USER, MAIL_PASS]):
        print("错误：Secrets 配置不完整，请检查 GitHub Settings。")
    else:
        news = get_search_results()
        if news:
            report_content = summarize_with_ai(news)
            send_email(report_content)
        else:
            print("今日关键词下无新资讯更新。")
