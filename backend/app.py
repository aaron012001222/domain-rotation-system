# backend/app.py
from flask import Flask, jsonify, request, redirect # 修正：添加了 redirect
from flask_cors import CORS
from config import Config
from models import db, DomainGroup, TransitDomain, LandingDomain
from flask_migrate import Migrate
import random
import re # 修正：添加了 re
from threading import Thread
from apscheduler.schedulers.background import BackgroundScheduler
from checker import run_check_job

# --- App Initialization ---
app = Flask(__name__)
# [修正] 将 scheduler 移到全局作用域
scheduler = BackgroundScheduler(daemon=True)
app.config.from_object(Config)

# --- Extensions Initialization ---
db.init_app(app)
migrate = Migrate(app, db)
CORS(app) # 允许所有来源的跨域请求，方便开发

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
    """
    获取所有落地域名（用于全局搜索或总览）
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    status_filter = request.args.get('status') # 'safe', 'unsafe', 'pending'
    search_query = request.args.get('search')

    query = LandingDomain.query

    if status_filter:
        query = query.filter_by(status=status_filter)
    
    if search_query:
        query = query.filter(LandingDomain.url.like(f'%{search_query}%'))
        
    # [新] 为 "AllDomains" 页面添加所属组的信息
    pagination = query.order_by(LandingDomain.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    domains = pagination.items
    
    domain_list = []
    for d in domains:
        domain_list.append({
            'id': d.id, 
            'url': d.url, 
            'status': d.status, 
            'last_checked': d.last_checked_at,
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
    # 确保 models.py 中有 to_dict() 方法
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
    # 确保 models.py 中有 to_dict() 方法
    return jsonify(new_group.to_dict()), 201

@app.route('/api/groups/<int:group_id>', methods=['GET'])
def get_group_details(group_id):
    """获取单个组的详细信息及其所有域名"""
    group = DomainGroup.query.get_or_404(group_id)
    
    # 确保 models.py 中有 to_dict() 方法
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

# --- 辅助函数 ---
def process_and_add_domains(urls_input, group_id, DomainModel):
    """辅助函数：处理并批量添加域名到数据库"""
    if isinstance(urls_input, str):
        # 如果是字符串，按空格、换行符、逗号等分割
        urls_to_add = [url.strip() for url in re.split(r'[\s,;\n]+', urls_input)]
    elif isinstance(urls_input, list):
        urls_to_add = [url.strip() for url in urls_input]
    else:
        return 0

    added_count = 0
    for url in urls_to_add:
        # 确保 URL 不为空，并且在数据库中不存在
        if url and not DomainModel.query.filter_by(url=url).first():
            new_domain = DomainModel(url=url, group_id=group_id)
            db.session.add(new_domain)
            added_count += 1
            
    db.session.commit() # 在循环外提交一次
    return added_count

# --- 批量添加 API ---
@app.route('/api/groups/<int:group_id>/landing_domains', methods=['POST'])
def add_landing_domains_to_group(group_id):
    """批量添加落地域名到指定组"""
    group = DomainGroup.query.get_or_404(group_id)
    data = request.get_json()
    if not data or 'urls' not in data:
        return jsonify({'error': 'Missing urls'}), 400

    added_count = process_and_add_domains(data['urls'], group.id, LandingDomain)
    return jsonify({'message': f'Successfully added {added_count} landing domains.'}), 201

@app.route('/api/groups/<int:group_id>/transit_domains', methods=['POST'])
def add_transit_domains_to_group(group_id):
    """批量添加中转域名到指定组"""
    group = DomainGroup.query.get_or_404(group_id)
    data = request.get_json()
    if not data or 'urls' not in data:
        return jsonify({'error': 'Missing urls'}), 400

    added_count = process_and_add_domains(data['urls'], group.id, TransitDomain)
    return jsonify({'message': f'Successfully added {added_count} transit domains.'}), 201

# --- 核心跳转逻辑 ---
@app.route('/go')
def redirect_to_landing():
    """
    这是核心跳转路由。
    所有中转域名都应该解析到这台服务器，并指向这个路由。
    """
    
    # 1. [防爬虫] User-Agent 过滤
    user_agent = request.headers.get('User-Agent', '').lower()
    blocked_uas = [
        'bot', 'spider', 'crawler', 'python-requests', 'curl', 
        'wget', 'httpclient', 'java', 'go-http-client'
    ]
    if any(ua in user_agent for ua in blocked_uas):
        # 返回 404，假装这个页面不存在
        return "Not Found", 404

    # 2. 获取用户访问的中转域名
    transit_url = request.host
    if ':' in transit_url:
        transit_url = transit_url.split(':')[0]

    # 3. 查找有效的中转域名
    transit_domain = TransitDomain.query.filter(
        (TransitDomain.url == transit_url) |
        (TransitDomain.url == f"http://{transit_url}") |
        (TransitDomain.url == f"https://{transit_url}")
    ).first()

    if not transit_domain:
        # 如果数据库里没有这个域名
        return "Invalid transit domain.", 404

    # 4. 查找该组所有“安全”的落地域名
    group_id = transit_domain.group_id
    safe_landing_domains = LandingDomain.query.filter_by(
        group_id=group_id,
        status='safe'
    ).all()

    if not safe_landing_domains:
        # 如果组里没有健康的链接
        return "No healthy landing page available.", 404

    # 5. 从健康列表中随机选择一个
    chosen_domain = random.choice(safe_landing_domains)

    # 6. [防红优化] 返回 JS/Meta 重定向页面
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

# --- 新增：删除中转域名 API ---
@app.route('/api/transit_domains/<int:domain_id>', methods=['DELETE'])
def delete_transit_domain(domain_id):
    """删除单个中转域名"""
    domain = TransitDomain.query.get_or_404(domain_id)
    db.session.delete(domain)
    db.session.commit()
    return jsonify({'message': 'Transit domain deleted successfully.'})

# --- 新增：调度器控制 API ---
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

# --- 新增：跳转测试 API ---
@app.route('/api/test_redirect', methods=['POST'])
def test_redirect():
    """
    模拟 /go 路由的逻辑，用于后台测试
    接收 {"url": "zhongzhuan.com"}
    返回 {"status": "success", "landing_url": "..."} 或 {"status": "error", "message": "..."}
    """
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'status': 'error', 'message': 'Missing URL'}), 400

    transit_url = data['url']

    # 1. 查找有效的中转域名
    transit_domain = TransitDomain.query.filter(
        (TransitDomain.url == transit_url) |
        (TransitDomain.url == f"http://{transit_url}") |
        (TransitDomain.url == f"https://{transit_url}")
    ).first()

    if not transit_domain:
        return jsonify({'status': 'error', 'message': '无效的中转域名 (未在数据库中找到)'}), 404

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
    # 初始化并启动定时任务
    scheduler.add_job(
        id='DomainCheckJob', 
        func=run_check_job, 
        args=[app], 
        trigger='interval', 
        minutes=5 # 对应您的需求：每5分钟检测一次
    )
    scheduler.start()
    
    print("Scheduler started... running job every 5 minutes.")
    
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
    # 注意: debug=True 和 use_reloader=True 可能会导致 APScheduler 运行两次。
    # 我们设置 use_reloader=False 来避免这个问题。
    # 在生产环境中，我们会使用 Gunicorn，则没有此问题。