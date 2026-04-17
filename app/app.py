from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Prediction
import joblib
import numpy as np
import os

app = Flask(__name__)
app.secret_key = 'churnguard_secret_2024'

@app.route('/')
def index():
    return redirect(url_for('login'))

# Database config
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'churnguard.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login to access ChurnGuard.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Load ML model
model  = joblib.load('../models/xgboost.pkl')
scaler = joblib.load('../models/scaler.pkl')

CONTRACT_MAP = {0: 'Month-to-month', 1: 'One year', 2: 'Two year'}

# ─── REGISTER 
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username'].strip()
        email    = request.form['email'].strip()
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Username already exists. Try another.', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please login.', 'danger')
            return redirect(url_for('register'))

        hashed = generate_password_hash(password)
        user   = User(username=username, email=email, password=hashed)
        db.session.add(user)
        db.session.commit()
        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# ─── LOGIN 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        user     = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

# ─── LOGOUT 
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

# ─── DASHBOARD 
@app.route('/dashboard')
@login_required
def dashboard():
    predictions = Prediction.query.filter_by(user_id=current_user.id)\
                                  .order_by(Prediction.created_at.desc())\
                                  .limit(10).all()
    total       = Prediction.query.filter_by(user_id=current_user.id).count()
    churned     = Prediction.query.filter_by(user_id=current_user.id, result='WILL CHURN').count()
    safe        = total - churned
    return render_template('dashboard.html',
                           predictions=predictions,
                           total=total,
                           churned=churned,
                           safe=safe)

# ─── PREDICT 
@app.route('/predict', methods=['GET', 'POST'])
@login_required
def predict():
    if request.method == 'GET':
        return render_template('index.html')
    try:
        tenure   = int(request.form['tenure'])
        monthly  = float(request.form['MonthlyCharges'])
        contract = int(request.form['Contract'])

        features = [
            int(request.form['gender']),
            int(request.form['SeniorCitizen']),
            int(request.form['Partner']),
            int(request.form['Dependents']),
            tenure,
            int(request.form['PhoneService']),
            int(request.form['MultipleLines']),
            int(request.form['InternetService']),
            int(request.form['OnlineSecurity']),
            int(request.form['OnlineBackup']),
            int(request.form['DeviceProtection']),
            int(request.form['TechSupport']),
            int(request.form['StreamingTV']),
            int(request.form['StreamingMovies']),
            contract,
            int(request.form['PaperlessBilling']),
            int(request.form['PaymentMethod']),
            monthly,
            float(request.form['TotalCharges']),
        ]

        arr         = np.array(features).reshape(1, -1)
        arr_scaled  = scaler.transform(arr)
        prediction  = model.predict(arr_scaled)[0]
        probability = round(model.predict_proba(arr_scaled)[0][1] * 100, 2)
        result      = 'WILL CHURN' if prediction == 1 else 'WILL NOT CHURN'
        color       = 'danger'     if prediction == 1 else 'success'

        # Save to database
        p = Prediction(
            user_id     = current_user.id,
            result      = result,
            probability = probability,
            contract    = CONTRACT_MAP[contract],
            tenure      = tenure,
            monthly     = monthly
        )
        db.session.add(p)
        db.session.commit()

        return render_template('result.html', result=result,
                               probability=probability, color=color)
    except Exception as e:
        flash(f'Error: {e}', 'danger')
        return redirect(url_for('predict'))

# ─── INIT DB & RUN 
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database ready!")
    app.run(debug=True)