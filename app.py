import os
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import joblib
import pandas as pd

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URL', 'sqlite:///users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS', 'False') == 'True'
db = SQLAlchemy(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
setattr(login_manager, 'login_view', 'login')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)          # FIX 1: added missing 'name' column
    username = db.Column(db.String(150), unique=True, nullable=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# FIX 2: create DB tables on startup
with app.app_context():
    db.create_all()

model = joblib.load("dc_power_model_daylight.joblib")


@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            session['user_id'] = user.id
            session['user_name'] = user.name   # FIX 3: user.name now exists
            flash('Login successful!', 'success')
            return redirect(url_for('upload'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validations
        if not name or len(name) < 2:
            flash('Name must be at least 2 characters long.', 'error')
            return redirect(url_for('signup'))

        if not email or '@' not in email:
            flash('Invalid email address.', 'error')
            return redirect(url_for('signup'))

        if (len(password) < 8
                or not any(char.isdigit() for char in password)
                or not any(char.isalpha() for char in password)
                or not any(not char.isalnum() for char in password)):
            flash('Password must be at least 8 characters long and contain letters, numbers and special characters.', 'error')
            return redirect(url_for('signup'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please log in.', 'error')
            return redirect(url_for('login'))

        hashed_password = generate_password_hash(password)
        new_user = User(
            name=name,
            email=email,
            password=hashed_password
        )
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'error')
            return redirect(url_for('signup'))

    return render_template('signup.html')

@app.route('/home')
def home():
    username = request.args.get('email')
    return render_template('home.html', username=username)

@app.route('/prediction', methods=['GET', 'POST'])
def prediction():
    if request.method == 'POST':
        try:
            ambient_temp = float(request.form['ambient_temp'])
            module_temp = float(request.form['module_temp'])
            irradiation = float(request.form['irradiation'])
            hour = int(request.form['hour'])
            day_of_week = int(request.form['day_of_week'])
            month = int(request.form['month'])
            plant_id = int(request.form['plant_id'])

            input_data = pd.DataFrame(
                [[ambient_temp, module_temp, irradiation, hour, day_of_week, month, plant_id]],
                columns=['AMBIENT_TEMPERATURE', 'MODULE_TEMPERATURE', 'IRRADIATION',
                         'hour', 'day_of_week', 'month', 'PLANT_ID']
            )

            prediction = model.predict(input_data)[0]
            return render_template('prediction.html',
                                   prediction_text=f"Predicted DC Power: {prediction:.2f}")
        except:
            return render_template('prediction.html',
                                   prediction_text="Invalid input! Please enter correct values.")

    return render_template('prediction.html')

if __name__ == '__main__':
    app.run(debug=True)