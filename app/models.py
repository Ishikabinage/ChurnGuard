from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    username     = db.Column(db.String(80), unique=True, nullable=False)
    email        = db.Column(db.String(120), unique=True, nullable=False)
    password     = db.Column(db.String(200), nullable=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    predictions  = db.relationship('Prediction', backref='user', lazy=True)

class Prediction(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    result       = db.Column(db.String(20), nullable=False)
    probability  = db.Column(db.Float, nullable=False)
    contract     = db.Column(db.String(30))
    tenure       = db.Column(db.Integer)
    monthly      = db.Column(db.Float)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)