# backend/models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# 辅助表，用于多对多关系 (一个组可以有多个中转，一个中转也可以在多个组... 不，我们保持简单)
# 我们保持一对多关系：一个中转域名只属于一个组

class DomainGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系定义
    transit_domains = db.relationship('TransitDomain', backref='group', lazy=True, cascade="all, delete-orphan")
    landing_domains = db.relationship('LandingDomain', backref='group', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'transit_domains_count': len(self.transit_domains),
            'landing_domains_count': len(self.landing_domains)
        }

class TransitDomain(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255), nullable=False) # 例如 "go1.my-domain.com"
    group_id = db.Column(db.Integer, db.ForeignKey('domain_group.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # --- [新字段] ---
    # 路径 (例如 "/go" 或 "/aB3xZ7")
    path = db.Column(db.String(100), nullable=False, default='/go') 
    # 健康状态
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, safe, unsafe
    # 最后检测时间
    last_checked_at = db.Column(db.DateTime)
    
    # [新] 确保 "域名 + 路径" 的组合是唯一的
    __table_args__ = (db.UniqueConstraint('url', 'path', name='_url_path_uc'),)

    def to_dict(self):
        return {
            'id': self.id,
            'url': self.url,
            'path': self.path, # [新]
            'full_url': f"http://{self.url}{self.path}", # [新] 组合网址
            'status': self.status, # [新]
            'last_checked_at': self.last_checked_at.isoformat() if self.last_checked_at else None, # [新]
            'group_id': self.group_id,
            'created_at': self.created_at.isoformat()
        }

class LandingDomain(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255), unique=True, nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, safe, unsafe
    group_id = db.Column(db.Integer, db.ForeignKey('domain_group.id'), nullable=False)
    last_checked_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'url': self.url,
            'status': self.status,
            'group_id': self.group_id,
            'last_checked_at': self.last_checked_at.isoformat() if self.last_checked_at else None,
            'created_at': self.created_at.isoformat()
        }