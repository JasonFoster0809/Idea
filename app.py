import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import func

from database import db
from models import User, Question, Contribution, Event, Purchase, FortuneCookie, InventoryItem, RANK_THRESHOLDS

def calculate_rewards(difficulty):
    """Calculate XP and coins based on question difficulty"""
    rewards = {
        'Easy': {'xp': 1, 'coins': 5},
        'Medium': {'xp': 3, 'coins': 10},
        'Hard': {'xp': 5, 'coins': 15}
    }
    return rewards.get(difficulty, {'xp': 1, 'coins': 5})

# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_key")

# Configure database with absolute path
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'instance', 'quiz.db'))
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Ensure instance directory exists
os.makedirs(os.path.dirname(db_path), exist_ok=True)

# Remove existing database if schema changed
if os.path.exists(db_path):
    os.remove(db_path)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return redirect(url_for('homepage'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('homepage'))
        flash('Tên đăng nhập hoặc mật khẩu không đúng')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Tên đăng nhập đã tồn tại')
            return redirect(url_for('register'))

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            coins=10  # New users start with 10 coins
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('homepage'))
    return render_template('login.html', register=True)

@app.route('/homepage')
@login_required
def homepage():
    top_users = User.query.order_by(User.coins.desc()).limit(10).all()
    return render_template('homepage.html', 
                         user=current_user, 
                         top_users=top_users,
                         RANK_THRESHOLDS=RANK_THRESHOLDS)

@app.route('/mainquiz')
@login_required
def mainquiz():
    subjects = ['Toán', 'Văn', 'Hóa', 'Lý', 'Sinh', 
                'Sử', 'Địa',  'Kinh tế háp luật', 'Tin học', 'Tiếng Anh']
    return render_template('mainquiz.html', subjects=subjects)

@app.route('/contribute', methods=['GET', 'POST'])
@login_required
def contribute():
    if request.method == 'POST':
        contribution = Contribution(
            subject=request.form.get('subject'),
            grade=request.form.get('grade'),
            question=request.form.get('question'),
            option_a=request.form.get('option_a'),
            option_b=request.form.get('option_b'),
            option_c=request.form.get('option_c'),
            option_d=request.form.get('option_d'),
            correct_answer=request.form.get('correct_answer'),
            explanation=request.form.get('explanation'),
            user_id=current_user.id
        )
        db.session.add(contribution)
        db.session.commit()
        flash('Câu hỏi đã được gửi và đang chờ phê duyệt')
        return redirect(url_for('contribute'))
    return render_template('contribute.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'admin123':
            user = User.query.filter_by(username='admin').first()
            if not user:
                user = User(
                    username='admin',
                    email='admin@example.com',
                    password_hash=generate_password_hash('admin123'),
                    is_admin=True
                )
                db.session.add(user)
                db.session.commit()
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        flash('Invalid admin credentials')
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return redirect(url_for('homepage'))

    # Statistics for dashboard
    total_users = User.query.count()
    pending_contributions = Contribution.query.filter_by(approved=False).count()
    total_questions = Question.query.count()

    # New users in last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    new_users = User.query.filter(User.id > 0).count()  # Placeholder until we add registration date

    # Top contributors
    top_contributors = db.session.query(
        User,
        func.count(Contribution.id).label('contributions')
    ).join(Contribution).group_by(User).order_by(
        func.count(Contribution.id).desc()
    ).limit(20).all()

    return render_template('admin/dashboard.html',
        total_users=total_users,
        pending_contributions=pending_contributions,
        total_questions=total_questions,
        new_users=new_users,
        top_contributors=top_contributors
    )

@app.route('/admin/contributions')
@login_required
def admin_contributions():
    if not current_user.is_admin:
        return redirect(url_for('homepage'))

    pending_contributions = Contribution.query.filter_by(approved=False).all()
    return render_template('admin/contributions.html', contributions=pending_contributions)

@app.route('/admin/contribution/<int:id>/approve', methods=['POST'])
@login_required
def approve_contribution(id):
    if not current_user.is_admin:
        return redirect(url_for('homepage'))

    contribution = Contribution.query.get_or_404(id)
    contribution.approved = True

    # Create a new question from the contribution
    question = Question(
        subject=contribution.subject,
        grade=contribution.grade,
        difficulty='Medium',  # Set default difficulty
        question_text=contribution.question,
        option_a=contribution.option_a,
        option_b=contribution.option_b,
        option_c=contribution.option_c,
        option_d=contribution.option_d,
        correct_answer=contribution.correct_answer,
        explanation=contribution.explanation
    )

    # Award coins to the contributor
    contributor = User.query.get(contribution.user_id)
    contributor.coins += 20

    db.session.add(question)
    db.session.commit()
    flash('Đã phê duyệt đóng góp và tặng 20 xu cho người đóng góp')
    return redirect(url_for('admin_contributions'))

@app.route('/admin/contribution/<int:id>/reject', methods=['POST'])
@login_required
def reject_contribution(id):
    if not current_user.is_admin:
        return redirect(url_for('homepage'))

    contribution = Contribution.query.get_or_404(id)
    db.session.delete(contribution)
    db.session.commit()
    flash('Đã từ chối đóng góp')
    return redirect(url_for('admin_contributions'))

# Add these new routes after the existing admin routes

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        return redirect(url_for('homepage'))
    users = User.query.filter_by(is_admin=False).all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/<int:user_id>/modify-coins', methods=['POST'])
@login_required
def modify_user_coins(user_id):
    if not current_user.is_admin:
        return redirect(url_for('homepage'))

    user = User.query.get_or_404(user_id)
    coin_amount = int(request.form.get('coin_amount', 0))
    reason = request.form.get('reason', '')

    user.coins += coin_amount
    if user.coins < 0:
        user.coins = 0

    db.session.commit()
    flash(f'Đã điều chỉnh số xu của {user.username} thành công')
    return redirect(url_for('admin_users'))


@app.route('/admin/fortune-cookies', methods=['GET', 'POST'])
@login_required
def admin_fortune_cookies():
    if not current_user.is_admin:
        return redirect(url_for('homepage'))

    if request.method == 'POST':
        message = request.form.get('message')
        cookie = FortuneCookie(message=message)
        db.session.add(cookie)
        db.session.commit()
        flash('Fortune cookie added successfully')

    cookies = FortuneCookie.query.all()
    return render_template('admin/fortune_cookies.html', cookies=cookies)

@app.route('/event')
@login_required
def event():
    events = Event.query.all()
    return render_template('event.html', events=events)

@app.route('/shop')
@login_required
def shop():
    return render_template('shop.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/answer_question', methods=['POST'])
@login_required
def answer_question():
    data = request.get_json()
    question_id = data.get('question_id')
    user_answer = data.get('answer')

    question = Question.query.get_or_404(question_id)
    is_correct = question.correct_answer == user_answer

    response = {
        'correct': is_correct,
        'correct_answer': question.correct_answer,
        'explanation': question.explanation
    }

    if is_correct:
        rewards = calculate_rewards(question.difficulty)
        xp_gained = current_user.add_experience(rewards['xp'])
        coins_gained = current_user.add_coins(rewards['coins'])

        response.update({
            'xp_gained': xp_gained,
            'coins_gained': coins_gained,
            'new_rank': current_user.rank,
            'new_xp': current_user.experience,
            'new_coins': current_user.coins
        })

        db.session.commit()

    return jsonify(response)

# Update admin creation with 10,000 initial coins
with app.app_context():
    db.create_all()
    # Create admin user if it doesn't exist
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@example.com',
            password_hash=generate_password_hash('admin123'),
            is_admin=True,
            coins=10000  # Set initial coins to 10,000
        )
        db.session.add(admin)
        db.session.commit()
    elif admin.coins < 10000:  # Ensure existing admin has at least 10,000 coins
        admin.coins = 10000
        db.session.commit()

@app.route('/inventory')
@login_required
def inventory():
    inventory_items = InventoryItem.query.filter_by(user_id=current_user.id).order_by(InventoryItem.acquired_date.desc()).all()
    return render_template('inventory.html', inventory_items=inventory_items)

@app.route('/api/purchase', methods=['POST'])
@login_required
def purchase_item():
    try:
        data = request.get_json()
        item_name = data.get('item')
        cost = data.get('cost')

        if not item_name or not cost:
            return jsonify({'success': False, 'message': 'Invalid purchase data'}), 400

        if current_user.coins < cost:
            return jsonify({'success': False, 'message': 'Không đủ xu'}), 400

        # Create purchase record
        purchase = Purchase(
            user_id=current_user.id,
            item_type='help_item',
            item_name=item_name,
            cost=cost
        )

        # Add to inventory
        existing_item = InventoryItem.query.filter_by(
            user_id=current_user.id,
            item_name=item_name,
            is_used=False
        ).first()

        if existing_item:
            existing_item.quantity += 1
        else:
            inventory_item = InventoryItem(
                user_id=current_user.id,
                item_name=item_name
            )
            db.session.add(inventory_item)

        # Deduct coins
        current_user.coins -= cost

        db.session.add(purchase)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Mua hàng thành công',
            'newBalance': current_user.coins
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)