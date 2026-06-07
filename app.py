import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import joblib
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# =========================
# FLASK APP CONFIG
# =========================

app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv(
    'SECRET_KEY',
    'your_secret_key'
)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'SQLALCHEMY_DATABASE_URL',
    'sqlite:///users.db'
)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# =========================
# FLASK LOGIN CONFIG
# =========================

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = 'login'

# =========================
# USER LOADER
# =========================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# =========================
# USER MODEL
# =========================

class User(UserMixin, db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(200),
        nullable=False
    )

# =========================
# CREATE DATABASE
# =========================

with app.app_context():
    db.create_all()

# =========================
# LOAD ML MODEL
# =========================

model = joblib.load("dc_power_model_daylight.joblib")

# =========================
# INDEX ROUTE
# =========================

@app.route('/')
def index():
    return redirect(url_for('login'))

# =========================
# LOGIN ROUTE
# =========================

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(
            email=email
        ).first()

        # CHECK PASSWORD

        if user and check_password_hash(
            user.password,
            password
        ):

            login_user(user)

            flash(
                'Login successful!',
                'success'
            )

            return redirect(
                url_for('home')
            )

        else:

            flash(
                'Invalid email or password.',
                'error'
            )

    return render_template('login.html')

# =========================
# SIGNUP ROUTE
# =========================

@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        name = request.form.get(
            'name',
            ''
        ).strip()

        email = request.form.get(
            'email',
            ''
        ).strip()

        password = request.form.get(
            'password',
            ''
        )

        confirm_password = request.form.get(
            'confirm_password',
            ''
        )

        # =========================
        # VALIDATIONS
        # =========================

        if len(name) < 2:

            flash(
                'Name must be at least 2 characters long.',
                'error'
            )

            return redirect(
                url_for('signup')
            )

        if '@' not in email:

            flash(
                'Invalid email address.',
                'error'
            )

            return redirect(
                url_for('signup')
            )

        # PASSWORD VALIDATION

        if (
            len(password) < 8
            or not any(char.isdigit() for char in password)
            or not any(char.isalpha() for char in password)
            or not any(not char.isalnum() for char in password)
        ):

            flash(
                'Password must contain letters, numbers and symbols.',
                'error'
            )

            return redirect(
                url_for('signup')
            )

        # PASSWORD MATCH

        if password != confirm_password:

            flash(
                'Passwords do not match.',
                'error'
            )

            return redirect(
                url_for('signup')
            )

        # EXISTING USER CHECK

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:

            flash(
                'Email already registered.',
                'error'
            )

            return redirect(
                url_for('login')
            )

        # HASH PASSWORD

        hashed_password = generate_password_hash(
            password
        )

        # CREATE USER

        new_user = User(
            name=name,
            email=email,
            password=hashed_password
        )

        try:

            db.session.add(new_user)

            db.session.commit()

            flash(
                'Registration successful! Please login.',
                'success'
            )

            return redirect(
                url_for('login')
            )

        except Exception as e:

            db.session.rollback()

            flash(
                'Registration failed.',
                'error'
            )

            return redirect(
                url_for('signup')
            )

    return render_template('signup.html')

# =========================
# HOME PAGE
# =========================

@app.route('/home')
@login_required
def home():

    return render_template(
        'home.html',
        username=current_user.name
    )

# =========================
# PREDICTION ROUTE
# =========================

@app.route('/prediction', methods=['GET', 'POST'])
@login_required
def prediction():

    if request.method == 'POST':

        try:

            ambient_temp = float(
                request.form['ambient_temp']
            )

            module_temp = float(
                request.form['module_temp']
            )

            irradiation = float(
                request.form['irradiation']
            )

            hour = int(
                request.form['hour']
            )

            day_of_week = int(
                request.form['day_of_week']
            )

            month = int(
                request.form['month']
            )

            plant_id = int(
                request.form['plant_id']
            )

            # CREATE DATAFRAME

            input_data = pd.DataFrame(
                [[
                    ambient_temp,
                    module_temp,
                    irradiation,
                    hour,
                    day_of_week,
                    month,
                    plant_id
                ]],

                columns=[
                    'AMBIENT_TEMPERATURE',
                    'MODULE_TEMPERATURE',
                    'IRRADIATION',
                    'hour',
                    'day_of_week',
                    'month',
                    'PLANT_ID'
                ]
            )

            # PREDICT

            prediction = model.predict(
                input_data
            )[0]

            return render_template(
                'prediction.html',
                prediction_text=f"Predicted DC Power: {prediction:.2f}"
            )

        except Exception as e:

            return render_template(
                'prediction.html',
                prediction_text="Invalid input! Please enter correct values."
            )

    return render_template('prediction.html')

@app.route('/dashboard')
@login_required
def dashboard():

    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go

    # =========================
    # LOAD DATASETS
    # =========================

    generation_data = pd.read_csv(
        'Plant_1_Generation_Data.csv'
    )

    weather_data = pd.read_csv(
        'Plant_1_Weather_Sensor_Data.csv'
    )

    # =========================
    # USE LIMITED DATA
    # =========================

    generation_data = generation_data.head(3000)

    weather_data = weather_data.head(3000)

    # =========================
    # DATE CONVERSION
    # =========================

    generation_data['DATE_TIME'] = pd.to_datetime(
        generation_data['DATE_TIME']
    )

    weather_data['DATE_TIME'] = pd.to_datetime(
        weather_data['DATE_TIME']
    )

    # =========================
    # KEEP REQUIRED COLUMNS
    # =========================

    weather_data = weather_data[[
        'DATE_TIME',
        'AMBIENT_TEMPERATURE',
        'MODULE_TEMPERATURE',
        'IRRADIATION'
    ]]

    # =========================
    # MERGE DATA
    # =========================

    merged_data = pd.merge(
        generation_data,
        weather_data,
        on='DATE_TIME',
        how='inner'
    )

    # =========================
    # EXTRACT HOUR
    # =========================

    generation_data['HOUR'] = generation_data[
        'DATE_TIME'
    ].dt.hour

    # =========================
    # CHART 1
    # DC POWER TREND
    # =========================

    power_chart = px.line(
        generation_data,
        x='DATE_TIME',
        y='DC_POWER',
        title='DC Power Generation Trend',
        height=450
        
    )

    power_graph = power_chart.to_html(
        full_html=False,
        config={'responsive': True}
    )

    # =========================
    # CHART 2
    # AC VS DC POWER
    # =========================

    compare_chart = go.Figure()

    compare_chart.add_trace(
        go.Scatter(
            x=generation_data['DATE_TIME'],
            y=generation_data['DC_POWER'],
            mode='lines',
            name='DC Power'
        )
    )

    compare_chart.add_trace(
        go.Scatter(
            x=generation_data['DATE_TIME'],
            y=generation_data['AC_POWER'],
            mode='lines',
            name='AC Power'
        )
    )

    compare_chart.update_layout(
        title='AC Power vs DC Power',
        height=450
    )

    compare_graph = compare_chart.to_html(
        full_html=False,
        config={'responsive': True}
    )

    # =========================
    # CHART 3
    # IRRADIATION VS POWER
    # =========================

    scatter_chart = px.scatter(
        merged_data,
        x='IRRADIATION',
        y='DC_POWER',
        title='Irradiation vs DC Power',
        height=450
    )

    scatter_graph = scatter_chart.to_html(
        full_html=False,
        config={'responsive': True}
    )

    # =========================
    # CHART 4
    # TEMPERATURE ANALYSIS
    # =========================

    temp_chart = px.line(
        merged_data,
        x='DATE_TIME',
        y='MODULE_TEMPERATURE',
        title='Module Temperature Analysis',
        height=450
    )

    temp_graph = temp_chart.to_html(
        full_html=False,
        config={'responsive': True}
    )

    # =========================
    # CHART 5
    # HOURLY POWER
    # =========================

    hourly_avg = generation_data.groupby(
        'HOUR'
    )['DC_POWER'].mean().reset_index()

    hourly_chart = px.bar(
        hourly_avg,
        x='HOUR',
        y='DC_POWER',
        title='Hourly Average Power',
        height=450
    )

    hourly_graph = hourly_chart.to_html(
        full_html=False,
        config={'responsive': True}
    )

    # =========================
    # DASHBOARD CARDS
    # =========================

    total_power = round(
        generation_data['DC_POWER'].sum(),
        2
    )

    avg_temp = round(
        merged_data['AMBIENT_TEMPERATURE'].mean(),
        2
    )

    max_power = round(
        generation_data['DC_POWER'].max(),
        2
    )

    avg_irradiation = round(
        merged_data['IRRADIATION'].mean(),
        2
    )

    return render_template(
        'dashboard.html',
        username=current_user.name,
        total_power=total_power,
        avg_temp=avg_temp,
        max_power=max_power,
        avg_irradiation=avg_irradiation,
        power_graph=power_graph,
        compare_graph=compare_graph,
        scatter_graph=scatter_graph,
        temp_graph=temp_graph,
        hourly_graph=hourly_graph
    )
# =========================
# LOGOUT ROUTE
# =========================

@app.route('/logout')
@login_required
def logout():

    logout_user()

    flash(
        'Logged out successfully.',
        'success'
    )

    return redirect(
        url_for('login')
    )

# =========================
# RUN APP
# =========================

if __name__ == '__main__':

    app.run(debug=True)