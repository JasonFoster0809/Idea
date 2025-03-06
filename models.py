from database import db
from flask_login import UserMixin
from datetime import datetime

# Rank configuration
RANK_THRESHOLDS = {
    'Newbie': 0,
    'Bronze': 300,
    'Iron': 750,
    'Tin': 1875,
    'Silver': 4600,
    'Gold': 11500,
    'Platinum': 27600,
    'Titanium': 60720,
    'Emerald': 125000,
    'Ruby': 131000,
    'Diamond': 200000
}

RANK_BONUS = {
    'Newbie': 0,
    'Bronze': 0.20,  # 20% bonus
    'Iron': 0.25,
    'Tin': 0.30,
    'Silver': 0.35,
    'Gold': 0.40,
    'Platinum': 0.42,
    'Titanium': 0.45,
    'Emerald': 0.47,
    'Ruby': 0.48,
    'Diamond': 0.50  # 50% bonus
}

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    coins = db.Column(db.Integer, default=10)  # New users start with 10 coins
    experience = db.Column(db.Integer, default=0)  # Experience points
    rank = db.Column(db.String(50), default='Newbie')
    is_admin = db.Column(db.Boolean, default=False)
    contributions = db.relationship('Contribution', backref='author', lazy=True)
    inventory_items = db.relationship('InventoryItem', backref='owner', lazy=True)

    def add_experience(self, base_xp):
        """Add experience points with rank bonus"""
        if self.experience >= 999999:  # Max XP cap
            return 0

        bonus_multiplier = 1 + RANK_BONUS.get(self.rank, 0)
        xp_gained = int(base_xp * bonus_multiplier)

        self.experience = min(self.experience + xp_gained, 999999)
        self.update_rank()
        return xp_gained

    def update_rank(self):
        """Update user's rank based on experience"""
        for rank, threshold in sorted(RANK_THRESHOLDS.items(), key=lambda x: x[1], reverse=True):
            if self.experience >= threshold:
                if self.rank != rank:  # Rank up!
                    self.rank = rank
                break

    def get_coin_multiplier(self):
        """Get the coin multiplier based on rank"""
        return 1 + RANK_BONUS.get(self.rank, 0)

    def add_coins(self, base_coins):
        """Add coins with rank bonus"""
        bonus_multiplier = self.get_coin_multiplier()
        coin_amount = int(base_coins * bonus_multiplier)
        self.coins += coin_amount
        return coin_amount

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100), nullable=False)
    grade = db.Column(db.Integer, nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(200), nullable=False)
    option_b = db.Column(db.String(200), nullable=False)
    option_c = db.Column(db.String(200), nullable=False)
    option_d = db.Column(db.String(200), nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)
    explanation = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Contribution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100), nullable=False)
    grade = db.Column(db.Integer, nullable=False)
    question = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(200), nullable=False)
    option_b = db.Column(db.String(200), nullable=False)
    option_c = db.Column(db.String(200), nullable=False)
    option_d = db.Column(db.String(200), nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)
    explanation = db.Column(db.Text)
    approved = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    prize_pool = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_type = db.Column(db.String(50), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    cost = db.Column(db.Integer, nullable=False)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)

class InventoryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    acquired_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_used = db.Column(db.Boolean, default=False)

class FortuneCookie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)