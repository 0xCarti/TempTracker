import os
import io
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
import pytz

from flask import (Flask, render_template, request, redirect, url_for,
                   session, send_file, flash)
from werkzeug.utils import secure_filename
import qrcode

app = Flask(__name__)
app.config['DATABASE'] = os.path.join(app.root_path, 'app.db')
app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD', 'admin')
app.secret_key = os.environ.get('SECRET_KEY', 'dev')
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def get_db():
    db = sqlite3.connect(app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    db.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
    return db


def init_db():
    db = get_db()
    with app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))
    db.close()


if not os.path.exists(app.config['DATABASE']):
    init_db()


def admin_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return view(**kwargs)
    return wrapped_view


def get_timezone():
    db = get_db()
    row = db.execute("SELECT value FROM settings WHERE key='timezone'").fetchone()
    db.close()
    return row['value'] if row else 'UTC'


def format_timestamp(ts, tzname):
    dt = datetime.fromisoformat(ts)
    dt = pytz.utc.localize(dt).astimezone(pytz.timezone(tzname))
    return dt.strftime('%H:%M %d/%m/%Y')


@app.route('/')
def index():
    db = get_db()
    locations = db.execute('SELECT * FROM location').fetchall()
    db.close()
    return render_template('index.html', locations=locations)


@app.route('/location/<int:location_id>')
def location_page(location_id):
    db = get_db()
    location = db.execute('SELECT * FROM location WHERE id=?', (location_id,)).fetchone()
    coolers = db.execute('SELECT * FROM cooler WHERE location_id=?', (location_id,)).fetchall()
    db.close()
    if location is None:
        return redirect(url_for('index'))
    return render_template('location.html', location=location, coolers=coolers)


@app.route('/cooler/<int:cooler_id>')
def cooler_page(cooler_id):
    db = get_db()
    cooler = db.execute('SELECT * FROM cooler WHERE id=?', (cooler_id,)).fetchone()
    today = datetime.utcnow().date().isoformat()
    logs = db.execute(
        'SELECT shift, temperature, timestamp FROM log WHERE cooler_id=? AND DATE(timestamp)=?',
        (cooler_id, today)
    ).fetchall()
    start_log = next((log for log in logs if log['shift'] == 'start'), None)
    end_log = next((log for log in logs if log['shift'] == 'end'), None)
    db.close()
    tzname = get_timezone()
    if start_log:
        start_log = dict(start_log)
        start_log['timestamp'] = format_timestamp(start_log['timestamp'], tzname)
    if end_log:
        end_log = dict(end_log)
        end_log['timestamp'] = format_timestamp(end_log['timestamp'], tzname)
    if cooler is None:
        return redirect(url_for('index'))
    return render_template('cooler.html', cooler=cooler, start_log=start_log, end_log=end_log, timezone=tzname)


@app.route('/cooler/<int:cooler_id>/submit/<shift>', methods=['POST'])
def submit_log(cooler_id, shift):
    temp = request.form.get('temperature')
    signature = request.form.get('signature')
    timestamp = datetime.utcnow().isoformat()
    if not temp or not signature:
        flash('Temperature and signature required.', 'warning')
        return redirect(url_for('cooler_page', cooler_id=cooler_id))
    try:
        temp_val = float(temp)
    except (TypeError, ValueError):
        flash('Invalid temperature.', 'error')
        return redirect(url_for('cooler_page', cooler_id=cooler_id))
    db = get_db()
    db.execute('INSERT INTO log (cooler_id, shift, temperature, timestamp, signature) VALUES (?, ?, ?, ?, ?)',
               (cooler_id, shift, temp_val, timestamp, signature))
    db.commit()
    db.close()
    flash('Temperature saved.', 'success')
    return redirect(url_for('cooler_page', cooler_id=cooler_id))


@app.route('/cooler/<int:cooler_id>/qr')
def cooler_qr(cooler_id):
    url = request.url_root.strip('/') + url_for('cooler_page', cooler_id=cooler_id)
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        if request.form.get('password') == app.config['ADMIN_PASSWORD']:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Invalid password'
    return render_template('admin/login.html', error=error)


@app.route('/admin/logout')
@admin_required
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html')


@app.route('/admin/locations', methods=['GET', 'POST'])
@admin_required
def admin_locations():
    db = get_db()
    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            db.execute('INSERT INTO location (name) VALUES (?)', (name,))
            db.commit()
    locations = db.execute('SELECT * FROM location').fetchall()
    db.close()
    return render_template('admin/locations.html', locations=locations)


@app.route('/admin/locations/<int:location_id>/delete')
@admin_required
def delete_location(location_id):
    db = get_db()
    db.execute('DELETE FROM location WHERE id=?', (location_id,))
    db.commit()
    db.close()
    return redirect(url_for('admin_locations'))


@app.route('/admin/coolers', methods=['GET', 'POST'])
@admin_required
def admin_coolers():
    db = get_db()
    locations = db.execute('SELECT * FROM location').fetchall()
    if request.method == 'POST':
        name = request.form.get('name')
        location_id = request.form.get('location_id')
        image = request.files.get('image')
        image_path = None
        if image and image.filename:
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = os.path.join('uploads', filename)
        if name and location_id:
            db.execute('INSERT INTO cooler (location_id, name, image_path) VALUES (?, ?, ?)',
                       (location_id, name, image_path))
            db.commit()
    coolers = db.execute('SELECT cooler.*, location.name as location_name FROM cooler JOIN location ON cooler.location_id = location.id').fetchall()
    db.close()
    return render_template('admin/coolers.html', coolers=coolers, locations=locations)


@app.route('/admin/coolers/<int:cooler_id>/delete')
@admin_required
def delete_cooler(cooler_id):
    db = get_db()
    db.execute('DELETE FROM cooler WHERE id=?', (cooler_id,))
    db.commit()
    db.close()
    return redirect(url_for('admin_coolers'))


@app.route('/admin/logs')
@admin_required
def admin_logs():
    db = get_db()
    logs = db.execute('''SELECT log.*, cooler.name as cooler_name, location.name as location_name
                          FROM log
                          JOIN cooler ON log.cooler_id = cooler.id
                          JOIN location ON cooler.location_id = location.id
                          ORDER BY log.timestamp DESC''').fetchall()
    db.close()
    tzname = get_timezone()
    logs = [dict(log) for log in logs]
    for log in logs:
        log['timestamp'] = format_timestamp(log['timestamp'], tzname)
    return render_template('admin/logs.html', logs=logs, timezone=tzname)


@app.route('/admin/reports/averages', methods=['GET', 'POST'])
@admin_required
def report_average():
    db = get_db()
    locations = db.execute('SELECT * FROM location').fetchall()
    results = None
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        location_id = request.form.get('location_id')
        query = ('SELECT log.shift, log.temperature, log.timestamp '
                 'FROM log JOIN cooler ON log.cooler_id = cooler.id '
                 'WHERE DATE(log.timestamp) BETWEEN ? AND ?')
        params = [start_date, end_date]
        if location_id != 'all':
            query += ' AND cooler.location_id = ?'
            params.append(location_id)
        logs = db.execute(query, params).fetchall()
        tz = pytz.timezone(get_timezone())
        start_times, start_temps, end_times, end_temps = [], [], [], []
        for log in logs:
            dt = datetime.fromisoformat(log['timestamp'])
            dt_local = pytz.utc.localize(dt).astimezone(tz)
            seconds = dt_local.hour * 3600 + dt_local.minute * 60 + dt_local.second
            if log['shift'] == 'start':
                start_temps.append(log['temperature'])
                start_times.append(seconds)
            elif log['shift'] == 'end':
                end_temps.append(log['temperature'])
                end_times.append(seconds)

        def avg_time(values):
            if not values:
                return 'N/A'
            avg_sec = sum(values) / len(values)
            h = int(avg_sec // 3600)
            m = int((avg_sec % 3600) // 60)
            return f"{h:02d}:{m:02d}"

        def avg_temp(values):
            if not values:
                return 'N/A'
            return round(sum(values) / len(values), 2)

        results = {
            'start_time': avg_time(start_times),
            'start_temp': avg_temp(start_temps),
            'end_time': avg_time(end_times),
            'end_temp': avg_temp(end_temps),
        }
    db.close()
    return render_template('admin/report_avg.html', locations=locations, results=results)


@app.route('/admin/reports/missed', methods=['GET', 'POST'])
@admin_required
def report_missed():
    db = get_db()
    locations = db.execute('SELECT * FROM location').fetchall()
    total = None
    weekday_counts = None
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        location_id = request.form.get('location_id')
        start_dt = datetime.fromisoformat(start_date).date()
        end_dt = datetime.fromisoformat(end_date).date()
        if location_id != 'all':
            cooler_rows = db.execute('SELECT id FROM cooler WHERE location_id=?', (location_id,)).fetchall()
            logs = db.execute('''SELECT log.cooler_id, log.shift, DATE(log.timestamp) as d
                                 FROM log JOIN cooler ON log.cooler_id=cooler.id
                                 WHERE DATE(log.timestamp) BETWEEN ? AND ? AND cooler.location_id=?''',
                              (start_date, end_date, location_id)).fetchall()
        else:
            cooler_rows = db.execute('SELECT id FROM cooler').fetchall()
            logs = db.execute('''SELECT log.cooler_id, log.shift, DATE(log.timestamp) as d
                                 FROM log JOIN cooler ON log.cooler_id=cooler.id
                                 WHERE DATE(log.timestamp) BETWEEN ? AND ?''',
                              (start_date, end_date)).fetchall()
        cooler_ids = [row['id'] for row in cooler_rows]
        existing = {(row['cooler_id'], row['d'], row['shift']) for row in logs}
        total = 0
        weekday_counts = {day: 0 for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']}
        current = start_dt
        while current <= end_dt:
            day_name = current.strftime('%A')
            d_str = current.isoformat()
            for cid in cooler_ids:
                for shift in ('start', 'end'):
                    if (cid, d_str, shift) not in existing:
                        total += 1
                        weekday_counts[day_name] += 1
            current += timedelta(days=1)
    db.close()
    return render_template('admin/report_missed.html', locations=locations, total=total, weekday_counts=weekday_counts)

@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    current_tz = get_timezone()
    if request.method == 'POST':
        tz = request.form.get('timezone')
        if tz in pytz.all_timezones:
            db = get_db()
            db.execute("REPLACE INTO settings (key, value) VALUES ('timezone', ?)", (tz,))
            db.commit()
            db.close()
            flash('Timezone updated.', 'success')
            current_tz = tz
        else:
            flash('Invalid timezone.', 'error')
    return render_template('admin/settings.html', timezone=current_tz, timezones=sorted(pytz.all_timezones))


if __name__ == '__main__':
    app.run(debug=True)
