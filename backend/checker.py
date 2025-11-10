# backend/checker.py
import requests
from models import db, LandingDomain, TransitDomain # [新] 导入 TransitDomain
from datetime import datetime

# 定义危险关键词
DANGER_KEYWORDS = [
    'dangerous', 'deceptive', 'phishing', 'malware',
    '危险', '欺诈', '钓鱼', '恶意软件', '停止访问'
]

def check_domain_safety(url):
    """
    [新] 这是一个通用函数，检测任何 URL 的安全性
    返回: 'safe', 'unsafe'
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # [新] 自动为没有 http/https 的 URL 添加 http://
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'http://' + url
            
        response = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
        
        if response.status_code >= 400:
            # 对于中转链接， 404 (来自我们后端的) 也是一种 "safe"
            # 但为了通用性，我们先将其标记为 unsafe，除非是我们自己的 404
            # 为了简单起见，所有 400+ 都是 unsafe
            return 'unsafe' 

        content = response.text.lower()
        for keyword in DANGER_KEYWORDS:
            if keyword in content:
                return 'unsafe' 
        
        return 'safe'

    except requests.exceptions.Timeout:
        return 'unsafe'
    except requests.exceptions.RequestException as e:
        print(f"Error checking {url}: {e}")
        return 'unsafe'

def run_check_job(app):
    """
    APScheduler 执行的作业函数
    [新] 现在会同时检测中转和落地
    """
    print(f"[{datetime.now()}] Starting domain health check job...")
    with app.app_context():
        
        # 1. 检测所有需要检测的落地域名
        landing_domains_to_check = LandingDomain.query.filter(
            LandingDomain.status.in_(['pending', 'safe'])
        ).all()
        
        checked_landing = 0
        for domain in landing_domains_to_check:
            new_status = check_domain_safety(domain.url)
            domain.status = new_status
            domain.last_checked_at = datetime.utcnow()
            checked_landing += 1
        
        print(f"Checked {checked_landing} landing domains.")

        # 2. [新] 检测所有需要检测的中转域名
        transit_domains_to_check = TransitDomain.query.filter(
            TransitDomain.status.in_(['pending', 'safe'])
        ).all()
        
        checked_transit = 0
        for domain in transit_domains_to_check:
            # 我们检测完整的 URL (e.g., http://go1.my-domain.com/go)
            full_url = f"http://{domain.url}{domain.path}"
            new_status = check_domain_safety(full_url)
            domain.status = new_status
            domain.last_checked_at = datetime.utcnow()
            checked_transit += 1
            
        print(f"Checked {checked_transit} transit domains.")

        # 3. 提交所有更改
        if checked_landing > 0 or checked_transit > 0:
            db.session.commit()
            
        print(f"Job finished. Checked {checked_landing} landing, {checked_transit} transit.")