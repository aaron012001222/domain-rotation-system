# backend/checker.py
import requests
from models import db, LandingDomain
from datetime import datetime

# 定义危险关键词，如果页面源码中包含这些，则认为不安全
DANGER_KEYWORDS = [
    'dangerous', 'deceptive', 'phishing', 'malware',
    '危险', '欺诈', '钓鱼', '恶意软件', '停止访问'
]

def check_domain_safety(domain):
    """
    检测单个域名的安全性
    返回: 'safe', 'unsafe'
    """
    try:
        # User-Agent 伪装成浏览器，防止被简单拦截
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 设置5秒超时
        response = requests.get(domain.url, headers=headers, timeout=5, allow_redirects=True)
        
        # 1. 检查HTTP状态码
        if response.status_code >= 400:
            return 'unsafe' # 访问失败

        # 2. 检查内容关键词
        content = response.text.lower()
        for keyword in DANGER_KEYWORDS:
            if keyword in content:
                return 'unsafe' # 包含危险关键词
        
        # 3. (可选) 检查是否是重定向到危险页面
        if response.history:
            final_url = response.url
            # 在这里可以添加对最终URL的额外检查
            pass

        # 如果所有检查都通过
        return 'safe'

    except requests.exceptions.Timeout:
        # 请求超时
        return 'unsafe'
    except requests.exceptions.RequestException as e:
        # 其他所有网络请求错误 (e.g., DNS解析失败)
        print(f"Error checking {domain.url}: {e}")
        return 'unsafe'

def run_check_job(app):
    """
    APScheduler 执行的作业函数
    """
    print(f"[{datetime.now()}] Starting domain health check job...")
    with app.app_context():
        # 检查所有 'pending' 或 'safe' 的域名
        domains_to_check = LandingDomain.query.filter(
            LandingDomain.status.in_(['pending', 'safe'])
        ).all()
        
        # 也检查之前 'unsafe' 的域名，但降低检查频率 (例如, 每3次才检查一次)
        # 这里为了简单，我们检查所有域名
        # domains_to_check = LandingDomain.query.all()

        if not domains_to_check:
            print("No domains to check.")
            return

        checked_count = 0
        for domain in domains_to_check:
            new_status = check_domain_safety(domain)
            domain.status = new_status
            domain.last_checked_at = datetime.utcnow()
            checked_count += 1
        
        db.session.commit()
        print(f"Job finished. Checked {checked_count} domains.")