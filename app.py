import os
import io
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   session, send_file, flash)
import qrcode

app = Flask(__name__)
app.config['DATABASE'] = os.path.join(app.root_path, 'app.db')
app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD', 'admin')
app.secret_key = os.environ.get('SECRET_KEY', 'dev')


def get_db():
    db = sqlite3.connect(app.config['DATABASE'])
    db.row_factory = sqlite3.Row
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
    if cooler is None:
        return redirect(url_for('index'))
    return render_template('cooler.html', cooler=cooler, start_log=start_log, end_log=end_log)


@app.route('/cooler/<int:cooler_id>/submit/<shift>', methods=['POST'])
def submit_log(cooler_id, shift):
    temp = request.form.get('temperature')
    signature = request.form.get('signature')
    timestamp = datetime.utcnow().isoformat()
    if not temp or not signature:
        flash('Temperature and signature required.')
        return redirect(url_for('cooler_page', cooler_id=cooler_id))
    try:
        temp_val = float(temp)
    except (TypeError, ValueError):
        flash('Invalid temperature.')
        return redirect(url_for('cooler_page', cooler_id=cooler_id))
    db = get_db()
    db.execute('INSERT INTO log (cooler_id, shift, temperature, timestamp, signature) VALUES (?, ?, ?, ?, ?)',
               (cooler_id, shift, temp_val, timestamp, signature))
    db.commit()
    db.close()
    flash('Temperature saved.')
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
        image_url = request.form.get('image_url')
        if name and location_id:
            db.execute('INSERT INTO cooler (location_id, name, image_url) VALUES (?, ?, ?)',
                       (location_id, name, image_url))
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
    return render_template('admin/logs.html', logs=logs)


if __name__ == '__main__':
    app.run(debug=True)
