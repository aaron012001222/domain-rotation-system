# backend/models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

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
    url = db.Column(db.String(255), unique=True, nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('domain_group.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'url': self.url,
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