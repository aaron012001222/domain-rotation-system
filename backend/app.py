# backend/app.py
from flask import Flask, jsonify, request, redirect
from flask_cors import CORS
from config import Config
from models import db, DomainGroup, TransitDomain, LandingDomain
from flask_migrate import Migrate
import random
import re
from threading import Thread
from apscheduler.schedulers.background import BackgroundScheduler
from checker import run_check_job
import string # [新] 导入 string 模块用于生成随机路径

# --- App Initialization ---
app = Flask(__name__)
scheduler = BackgroundScheduler(daemon=True)
app.config.from_object(Config)

# --- Extensions Initialization ---
db.init_app(app)
migrate = Migrate(app, db)
CORS(app) 

# --- [!!! 关键修复 !!!] ---
# 将调度器任务的添加和启动移到全局作用域
# 这样 Gunicorn 才能在导入时执行它
scheduler.add_job(
    id='DomainCheckJob', 
    func=run_check_job, 
    args=[app], 
    trigger='interval', 
    minutes=5 
)
scheduler.start()
print("Scheduler started... running job every 5 minutes.")
# --- [!!! 修复结束 !!!] ---


# --- [新] 辅助函数：生成随机路径 ---
def generate_random_path(length=6):
    """生成一个 5-8 位的随机字母和数字路径"""
    if length < 5: length = 5
    if length > 8: length = 8
    chars = string.ascii_letters + string.digits
    path = ''.join(random.choice(chars) for _ in range(length))
    # 以 / 开头
    return f"/{path}"

# --- API Endpoints ---

@app.route('/')
def index():
    return "Backend is running!"

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取仪表盘统计数据"""
    total_domains = LandingDomain.query.count()
    safe_domains = LandingDomain.query.filter_by(status='safe').count()
    unsafe_domains = LandingDomain.query.filter_by(status='unsafe').count()
    
    return jsonify({
        'total': total_domains,
        'safe': safe_domains,
        'unsafe': unsafe_domains
    })

@app.route('/api/domains', methods=['GET'])
def get_all_domains():
    """获取所有落地域名（用于全局搜索或总览）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    status_filter = request.args.get('status')
    search_query = request.args.get('search')

    query = LandingDomain.query

    if status_filter:
        query = query.filter_by(status=status_filter)
    if search_query:
        query = query.filter(LandingDomain.url.like(f'%{search_query}%'))
        
    pagination = query.order_by(LandingDomain.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    domains = pagination.items
    
    domain_list = []
    for d in domains:
        domain_list.append({
            'id': d.id, 
            'url': d.url, 
            'status': d.status, 
            'last_checked': d.last_checked_at.isoformat() if d.last_checked_at else None,
            'group': { 'name': d.group.name } if d.group else { 'name': 'N/A' }
        })

    return jsonify({
        'domains': domain_list,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })

@app.route('/api/domains', methods=['DELETE'])
def delete_domains():
    """批量删除落地域名"""
    data = request.get_json()
    if not data or 'ids' not in data:
        return jsonify({'error': 'Missing domain ids'}), 400

    ids_to_delete = data['ids']
    LandingDomain.query.filter(LandingDomain.id.in_(ids_to_delete)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({'message': 'Domains deleted successfully.'})

@app.route('/api/groups', methods=['GET'])
def get_groups():
    """获取所有域名组的列表"""
    groups = DomainGroup.query.order_by(DomainGroup.created_at.desc()).all()
    return jsonify([group.to_dict() for group in groups])

@app.route('/api/groups', methods=['POST'])
def create_group():
    """创建一个新的域名组"""
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': 'Missing group name'}), 400
    if DomainGroup.query.filter_by(name=data['name']).first():
        return jsonify({'error': 'Group name already exists'}), 400
    new_group = DomainGroup(name=data['name'])
    db.session.add(new_group)
    db.session.commit()
    return jsonify(new_group.to_dict()), 201

@app.route('/api/groups/<int:group_id>', methods=['GET'])
def get_group_details(group_id):
    """获取单个组的详细信息及其所有域名"""
    group = DomainGroup.query.get_or_404(group_id)
    transit_domains = [td.to_dict() for td in group.transit_domains]
    landing_domains = [ld.to_dict() for ld in group.landing_domains]
    return jsonify({
        'group': group.to_dict(),
        'transit_domains': transit_domains,
        'landing_domains': landing_domains
    })

@app.route('/api/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    """删除一个组（及其所有关联域名）"""
    group = DomainGroup.query.get_or_404(group_id)
    db.session.delete(group)
    db.session.commit()
    return jsonify({'message': f'Group "{group.name}" deleted successfully.'})

# --- [新] 辅助函数：处理中转域名添加 ---
def process_and_add_transit_domains(urls_input, group_id, path_type, custom_path):
    if isinstance(urls_input, str):
        urls_to_add = [url.strip() for url in re.split(r'[\s,;\n]+', urls_input)]
    elif isinstance(urls_input, list):
        urls_to_add = [url.strip() for url in urls_input]
    else:
        return 0, 0

    added_count = 0
    skipped_count = 0

    for url in urls_to_add:
        if not url:
            continue
        
        path = "/go" # 默认路径
        if path_type == 'custom':
            if not custom_path:
                custom_path = "/custom" # 备用自定义路径
            path = custom_path if custom_path.startswith('/') else f"/{custom_path}"
        elif path_type == 'random':
            path = generate_random_path(random.randint(5, 8))

        # 检查 "域名+路径" 组合是否已存在
        exists = TransitDomain.query.filter_by(url=url, path=path).first()
        
        if not exists:
            new_domain = TransitDomain(url=url, group_id=group_id, path=path)
            db.session.add(new_domain)
            added_count += 1
        else:
            skipped_count += 1
            
    db.session.commit()
    return added_count, skipped_count

# --- 辅助函数：处理落地域名添加 ---
def process_and_add_landing_domains(urls_input, group_id, DomainModel):
    if isinstance(urls_input, str):
        urls_to_add = [url.strip() for url in re.split(r'[\s,;\n]+', urls_input)]
    elif isinstance(urls_input, list):
        urls_to_add = [url.strip() for url in urls_input]
    else:
        return 0

    added_count = 0
    for url in urls_to_add:
        if url and not DomainModel.query.filter_by(url=url).first():
            new_domain = DomainModel(url=url, group_id=group_id)
            db.session.add(new_domain)
            added_count += 1
    db.session.commit()
    return added_count

# --- 批量添加 API ---
@app.route('/api/groups/<int:group_id>/landing_domains', methods=['POST'])
def add_landing_domains_to_group(group_id):
    """批量添加落地域名到指定组"""
    group = DomainGroup.query.get_or_404(group_id)
    data = request.get_json()
    if not data or 'urls' not in data:
        return jsonify({'error': 'Missing urls'}), 400
    added_count = process_and_add_landing_domains(data['urls'], group.id, LandingDomain)
    return jsonify({'message': f'Successfully added {added_count} landing domains.'}), 201

# --- [新] 更新：批量添加中转域名 API ---
@app.route('/api/groups/<int:group_id>/transit_domains', methods=['POST'])
def add_transit_domains_to_group(group_id):
    """批量添加中转域名到指定组（支持自定义路径）"""
    group = DomainGroup.query.get_or_404(group_id)
    data = request.get_json()
    if not data or 'urls' not in data:
        return jsonify({'error': 'Missing urls'}), 400

    path_type = data.get('path_type', 'default') # 'default', 'custom', 'random'
    custom_path = data.get('custom_path', '')

    added_count, skipped_count = process_and_add_transit_domains(
        data['urls'], group.id, path_type, custom_path
    )
    
    message = f"成功添加 {added_count} 个新中转域名。"
    if skipped_count > 0:
        message += f" {skipped_count} 个域名（因 '域名+路径' 组合已存在）被跳过。"
        
    return jsonify({'message': message}), 201

# --- [新] 核心跳转逻辑（动态路径） ---
@app.route('/<path:path>')
def dynamic_redirect_to_landing(path):
    """
    这是新的核心动态跳转路由。
    它会匹配所有路径，例如 /go, /aB3xZ7, /my/custom/path
    """
    
    # 1. [安全] 过滤掉对后台管理页面的访问
    #    (这是 Nginx 规则 1 的第二层保险)
    admin_paths = ['api', 'assets', 'all-domains', 'group']
    if path == '/' or any(path.startswith(p) for p in admin_paths):
        # 如果 Nginx 配置错误，Flask 会在这里捕获并拒绝
        return "Not Found (Admin Endpoint)", 404

    # 2. [防爬虫] User-Agent 过滤
    user_agent = request.headers.get('User-Agent', '').lower()
    blocked_uas = [
        'bot', 'spider', 'crawler', 'python-requests', 'curl', 
        'wget', 'httpclient', 'java', 'go-http-client'
    ]
    if any(ua in user_agent for ua in blocked_uas):
        return "Not Found (Bot)", 404

    # 3. 获取域名和路径
    transit_url = request.host
    if ':' in transit_url:
        transit_url = transit_url.split(':')[0]
    
    transit_path = f"/{path}"

    # 4. 查找有效且健康的 "域名+路径" 组合
    transit_domain = TransitDomain.query.filter_by(
        url=transit_url, 
        path=transit_path,
        status='safe'  # [新] 只使用健康的中转链接
    ).first()

    if not transit_domain:
        # 找不到，或者中转链接本身不健康
        return "Invalid or unhealthy transit link.", 404

    # 5. 查找该组所有“安全”的落地域名
    group_id = transit_domain.group_id
    safe_landing_domains = LandingDomain.query.filter_by(
        group_id=group_id,
        status='safe'
    ).all()

    if not safe_landing_domains:
        return "No healthy landing page available.", 404

    # 6. 从健康列表中随机选择一个
    chosen_domain = random.choice(safe_landing_domains)

    # 7. [防红优化] 返回 JS/Meta 重定向页面
    html = f"""
    <html>
        <head>
            <title>Loading...</title>
            <meta http-equiv="refresh" content="0;url={chosen_domain.url}" />
        </head>
        <body>
            <p>Loading, please wait...</p>
            <script type="text/javascript">
                window.location.href = "{chosen_domain.url}";
            </script>
        </body>
    </html>
    """
    return html

# --- 手动触发检测 API ---
@app.route('/api/tasks/run_check', methods=['POST'])
def trigger_check_job():
    """手动触发一次健康检测"""
    Thread(target=run_check_job, args=[app]).start()
    return jsonify({'message': 'Health check job triggered.'})

# --- [新] 删除中转域名 API ---
@app.route('/api/transit_domains/<int:domain_id>', methods=['DELETE'])
def delete_transit_domain(domain_id):
    """删除单个中转域名"""
    domain = TransitDomain.query.get_or_404(domain_id)
    db.session.delete(domain)
    db.session.commit()
    return jsonify({'message': 'Transit domain deleted successfully.'})

# --- [新] 调度器控制 API ---
@app.route('/api/scheduler/pause', methods=['POST'])
def pause_scheduler():
    """暂停自动检测任务"""
    scheduler.pause_job('DomainCheckJob')
    return jsonify({'status': 'paused'})

@app.route('/api/scheduler/resume', methods=['POST'])
def resume_scheduler():
    """恢复自动检测任务"""
    scheduler.resume_job('DomainCheckJob')
    return jsonify({'status': 'running'})

@app.route('/api/scheduler/status', methods=['GET'])
def get_scheduler_status():
    """获取自动检测任务的状态"""
    job = scheduler.get_job('DomainCheckJob')
    if not job:
        return jsonify({'status': 'not_found'})
    if job.next_run_time is None:
        return jsonify({'status': 'paused'})
    else:
        return jsonify({'status': 'running', 'next_run': job.next_run_time.isoformat()})

# --- [新] 跳转测试 API ---
@app.route('/api/test_redirect', methods=['POST'])
def test_redirect():
    """
    模拟 /go 路由的逻辑，用于后台测试
    接收 {"url": "go1.example.com", "path": "/go"}
    """
    data = request.get_json()
    if not data or 'url' not in data or 'path' not in data:
        return jsonify({'status': 'error', 'message': 'Missing URL or Path'}), 400

    transit_url = data['url']
    transit_path = data['path']

    # 1. 查找有效的中转域名
    transit_domain = TransitDomain.query.filter_by(
        url=transit_url,
        path=transit_path
    ).first()

    if not transit_domain:
        return jsonify({'status': 'error', 'message': '无效的中转链接 (未在数据库中找到)'}), 404

    # 2. 查找该组所有“安全”的落地域名
    group_id = transit_domain.group_id
    safe_landing_domains = LandingDomain.query.filter_by(
        group_id=group_id,
        status='safe'
    ).all()

    if not safe_landing_domains:
        return jsonify({'status': 'error', 'message': '没有可用的“安全”落地域名'}), 404

    # 3. 从健康列表中随机选择一个
    chosen_domain = random.choice(safe_landing_domains)

    # 4. 返回成功
    return jsonify({
        'status': 'success',
        'landing_url': chosen_domain.url,
        'group_name': transit_domain.group.name
    })

# --- Main Execution ---
if __name__ == '__main__':
    # [!!! 关键修复 !!!] ---
    # 这一部分只在 `flask run` (开发) 时运行
    # Gunicorn 启动时不会运行这里
    # 我们的修复是把 add_job 和 start 移到 Gunicorn 也能加载的全局作用域
    
    # 我们只保留 app.run() 在这里
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)