from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import sqlite3
import os
import hashlib
import secrets
from datetime import datetime, date, timedelta
import csv
import io

app = Flask(__name__)
app.secret_key = 'assettrack-secret-2024-xK9m'

DB_PATH = 'assettrack.db'

# ─── Flask-Login Setup ─────────────────────────────────────────────────────────

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login to access AssetTrack.'
login_manager.login_message_category = 'info'

class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return User(row['id'], row['username'], row['role'])
    return None

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ─── Database Setup ────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'viewer',
            created_at TEXT DEFAULT (datetime('now'))
        )
    ''')

    # Assets table
    c.execute('''
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            manufacturer TEXT,
            serial_number TEXT,
            location TEXT,
            assigned_to TEXT,
            install_date TEXT,
            warranty_expiry TEXT,
            status TEXT DEFAULT 'Active',
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            severity TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Open',
            reported_by TEXT,
            reported_date TEXT,
            resolved_date TEXT,
            resolution_notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS deployments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id TEXT NOT NULL,
            deployed_to TEXT NOT NULL,
            deployed_by TEXT,
            deploy_date TEXT,
            return_date TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
        )
    ''')

    # Default admin user
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)",
                  ('admin', hash_password('admin123'), 'admin'))
        c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)",
                  ('viewer', hash_password('viewer123'), 'viewer'))

    # Sample data
    c.execute("SELECT COUNT(*) FROM assets")
    if c.fetchone()[0] == 0:
        sample_assets = [
            ('KW-LAP-0001', 'Dell Latitude 5540', 'Laptop', 'Dell', 'DL-KW2934', 'Floor 1 – Dept A', 'Ahmed Al-Mutairi', '2024-01-15', '2027-01-15', 'Active', 'Standard corporate laptop'),
            ('KW-SRV-0001', 'HP ProLiant DL380', 'Server', 'HP', 'HP-SRV8821', 'Data Center – Rack B', 'IT Dept', '2022-03-03', '2025-03-03', 'In Repair', 'Main application server'),
            ('KW-NET-0001', 'Cisco Catalyst 2960', 'Network', 'Cisco', 'CSC-NW4412', 'Floor 2 – Server Room', 'Network Team', '2021-08-22', '2024-08-22', 'Active', 'Core network switch'),
            ('KW-LAP-0002', 'Lenovo ThinkPad E15', 'Laptop', 'Lenovo', 'LN-KW1123', 'Floor 1 – HR', 'Sara Al-Rashidi', '2020-06-10', '2023-06-10', 'Retired', 'End of life'),
            ('KW-PRT-0001', 'HP LaserJet Pro M404', 'Printer', 'HP', 'HP-PRT3341', 'Floor 2 – Finance', 'Finance Dept', '2023-02-01', '2026-02-01', 'Active', 'Finance department printer'),
            ('KW-SRV-0002', 'Dell PowerEdge R740', 'Server', 'Dell', 'DL-SRV5521', 'Data Center – Rack A', 'IT Dept', '2023-06-15', '2026-06-15', 'Active', 'Database server'),
        ]
        c.executemany('''
            INSERT INTO assets (asset_id, name, category, manufacturer, serial_number, location, assigned_to, install_date, warranty_expiry, status, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ''', sample_assets)

        sample_issues = [
            ('KW-SRV-0001', 'Disk failure warning', 'SMART diagnostic shows bad sectors on disk 2 in RAID array. Backup taken, replacement ordered.', 'Critical', 'Open', 'Usama', '2026-06-10', None, None),
            ('KW-LAP-0001', 'Screen flickering', 'Screen flickers above 70% brightness. Possible display cable issue.', 'Medium', 'Resolved', 'Ahmed', '2026-06-08', '2026-06-12', 'Replaced display cable, issue resolved.'),
            ('KW-PRT-0001', 'Paper jam recurring', 'Tray 2 paper jam happening frequently. Roller cleaning scheduled.', 'Low', 'In Progress', 'Finance Dept', '2026-06-05', None, None),
        ]
        c.executemany('''
            INSERT INTO issues (asset_id, title, description, severity, status, reported_by, reported_date, resolved_date, resolution_notes)
            VALUES (?,?,?,?,?,?,?,?,?)
        ''', sample_issues)

        sample_deployments = [
            ('KW-LAP-0001', 'Ahmed Al-Mutairi – Dept A', 'IT Support', '2024-01-15', None, 'Initial deployment'),
            ('KW-LAP-0002', 'Sara Al-Rashidi – HR', 'IT Support', '2020-06-10', '2024-06-10', 'Retired after 4 years'),
        ]
        c.executemany('''
            INSERT INTO deployments (asset_id, deployed_to, deployed_by, deploy_date, return_date, notes)
            VALUES (?,?,?,?,?,?)
        ''', sample_deployments)

    conn.commit()
    conn.close()

# ─── Helper Functions ──────────────────────────────────────────────────────────

CATEGORY_CODES = {
    'Laptop': 'LAP', 'Monitor': 'MON', 'Server': 'SRV', 'Network': 'NET',
    'Printer': 'PRT', 'UPS': 'UPS', 'Desktop': 'DSK', 'Other': 'OTH',
}

def generate_asset_id(category):
    code = CATEGORY_CODES.get(category, 'OTH')
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM assets WHERE asset_id LIKE ?", (f'GBA-{code}-%',))
    count = c.fetchone()[0]
    conn.close()
    return f'GBA-{code}-{str(count + 1).zfill(4)}'

def days_until(date_str):
    if not date_str:
        return None
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        return (d - date.today()).days
    except:
        return None

def format_date(date_str):
    if not date_str:
        return '—'
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').strftime('%d %b %Y')
    except:
        return date_str

# ─── Auth Routes ───────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?",
                  (username, hash_password(password)))
        row = c.fetchone()
        conn.close()
        if row:
            user = User(row['id'], row['username'], row['role'])
            login_user(user, remember=True)
            flash(f'Welcome back, {username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ─── User Management (Admin only) ─────────────────────────────────────────────

@app.route('/users')
@login_required
def users_list():
    if current_user.role != 'admin':
        flash('Access denied. Admin only.', 'error')
        return redirect(url_for('dashboard'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, username, role, created_at FROM users ORDER BY id")
    users = c.fetchall()
    conn.close()
    return render_template('users.html', users=users, format_date=format_date)

@app.route('/users/new', methods=['POST'])
@login_required
def add_user():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    role = request.form.get('role', 'viewer')
    if not username or not password:
        flash('Username and password required.', 'error')
        return redirect(url_for('users_list'))
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)",
                     (username, hash_password(password), role))
        conn.commit()
        flash(f'User "{username}" created successfully!', 'success')
    except sqlite3.IntegrityError:
        flash(f'Username "{username}" already exists.', 'error')
    finally:
        conn.close()
    return redirect(url_for('users_list'))

@app.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    if user_id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('users_list'))
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    flash('User deleted.', 'info')
    return redirect(url_for('users_list'))

@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    old_pw = request.form.get('old_password', '')
    new_pw = request.form.get('new_password', '')
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=? AND password=?",
              (current_user.id, hash_password(old_pw)))
    if not c.fetchone():
        conn.close()
        flash('Current password is incorrect.', 'error')
        return redirect(url_for('users_list'))
    conn.execute("UPDATE users SET password=? WHERE id=?",
                 (hash_password(new_pw), current_user.id))
    conn.commit()
    conn.close()
    flash('Password changed successfully!', 'success')
    return redirect(url_for('users_list'))

# ─── Main Routes (protected) ───────────────────────────────────────────────────

@app.route('/')
@login_required
def dashboard():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM assets")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM assets WHERE status='Active'")
    active = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM assets WHERE status='In Repair'")
    in_repair = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM assets WHERE status='Retired'")
    retired = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM issues WHERE status='Open' AND severity='Critical'")
    critical_issues = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM issues WHERE status='Open'")
    open_issues = c.fetchone()[0]
    c.execute("SELECT category, COUNT(*) as cnt FROM assets GROUP BY category ORDER BY cnt DESC")
    by_category = c.fetchall()
    c.execute("SELECT location, COUNT(*) as cnt FROM assets GROUP BY location ORDER BY cnt DESC LIMIT 5")
    by_location = c.fetchall()
    today = date.today()
    warn_date = (today + timedelta(days=90)).strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')
    c.execute("""
        SELECT asset_id, name, warranty_expiry FROM assets
        WHERE warranty_expiry IS NOT NULL AND warranty_expiry != ''
        AND warranty_expiry BETWEEN ? AND ?
        ORDER BY warranty_expiry ASC LIMIT 5
    """, (today_str, warn_date))
    expiring = c.fetchall()
    c.execute("""
        SELECT i.*, a.name as asset_name FROM issues i
        JOIN assets a ON i.asset_id = a.asset_id
        ORDER BY i.created_at DESC LIMIT 5
    """)
    recent_issues = c.fetchall()
    conn.close()
    return render_template('dashboard.html',
        total=total, active=active, in_repair=in_repair, retired=retired,
        critical_issues=critical_issues, open_issues=open_issues,
        by_category=by_category, by_location=by_location,
        expiring=expiring, recent_issues=recent_issues,
        format_date=format_date, days_until=days_until
    )


@app.route('/assets')
@login_required
def assets():
    conn = get_db()
    c = conn.cursor()
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '')
    status = request.args.get('status', '')
    query = "SELECT * FROM assets WHERE 1=1"
    params = []
    if search:
        query += " AND (asset_id LIKE ? OR name LIKE ? OR location LIKE ? OR assigned_to LIKE ? OR serial_number LIKE ?)"
        s = f'%{search}%'
        params.extend([s, s, s, s, s])
    if category:
        query += " AND category = ?"
        params.append(category)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC"
    c.execute(query, params)
    asset_list = c.fetchall()
    conn.close()
    return render_template('assets.html',
        assets=asset_list, search=search, category=category, status=status,
        format_date=format_date, days_until=days_until,
        categories=list(CATEGORY_CODES.keys())
    )


@app.route('/assets/new', methods=['GET', 'POST'])
@login_required
def add_asset():
    if request.method == 'POST':
        category = request.form.get('category')
        asset_id = generate_asset_id(category)
        conn = get_db()
        try:
            conn.execute('''
                INSERT INTO assets (asset_id, name, category, manufacturer, serial_number,
                    location, assigned_to, install_date, warranty_expiry, status, notes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ''', (
                asset_id, request.form.get('name'), category,
                request.form.get('manufacturer'), request.form.get('serial_number'),
                request.form.get('location'), request.form.get('assigned_to'),
                request.form.get('install_date'), request.form.get('warranty_expiry'),
                request.form.get('status', 'Active'), request.form.get('notes'),
            ))
            conn.commit()
            flash(f'Asset {asset_id} saved successfully!', 'success')
            return redirect(url_for('assets'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
        finally:
            conn.close()
    preview_ids = {cat: generate_asset_id(cat) for cat in CATEGORY_CODES}
    return render_template('asset_form.html',
        asset=None, preview_ids=preview_ids, categories=list(CATEGORY_CODES.keys())
    )


@app.route('/assets/<asset_id>')
@login_required
def asset_detail(asset_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM assets WHERE asset_id=?", (asset_id,))
    asset = c.fetchone()
    if not asset:
        flash('Asset not found.', 'error')
        return redirect(url_for('assets'))
    c.execute("SELECT * FROM issues WHERE asset_id=? ORDER BY created_at DESC", (asset_id,))
    issues = c.fetchall()
    c.execute("SELECT * FROM deployments WHERE asset_id=? ORDER BY deploy_date DESC", (asset_id,))
    deployments = c.fetchall()
    conn.close()
    return render_template('asset_detail.html',
        asset=asset, issues=issues, deployments=deployments,
        format_date=format_date, days_until=days_until
    )


@app.route('/assets/<asset_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_asset(asset_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM assets WHERE asset_id=?", (asset_id,))
    asset = c.fetchone()
    if not asset:
        flash('Asset not found.', 'error')
        return redirect(url_for('assets'))
    if request.method == 'POST':
        try:
            conn.execute('''
                UPDATE assets SET name=?, category=?, manufacturer=?, serial_number=?,
                    location=?, assigned_to=?, install_date=?, warranty_expiry=?, status=?, notes=?
                WHERE asset_id=?
            ''', (
                request.form.get('name'), request.form.get('category'),
                request.form.get('manufacturer'), request.form.get('serial_number'),
                request.form.get('location'), request.form.get('assigned_to'),
                request.form.get('install_date'), request.form.get('warranty_expiry'),
                request.form.get('status'), request.form.get('notes'), asset_id
            ))
            conn.commit()
            flash(f'Asset {asset_id} updated!', 'success')
            return redirect(url_for('asset_detail', asset_id=asset_id))
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
        finally:
            conn.close()
    conn.close()
    return render_template('asset_form.html', asset=asset, categories=list(CATEGORY_CODES.keys()))


@app.route('/assets/<asset_id>/delete', methods=['POST'])
@login_required
def delete_asset(asset_id):
    if current_user.role != 'admin':
        flash('Only admins can delete assets.', 'error')
        return redirect(url_for('asset_detail', asset_id=asset_id))
    conn = get_db()
    conn.execute("DELETE FROM issues WHERE asset_id=?", (asset_id,))
    conn.execute("DELETE FROM deployments WHERE asset_id=?", (asset_id,))
    conn.execute("DELETE FROM assets WHERE asset_id=?", (asset_id,))
    conn.commit()
    conn.close()
    flash(f'Asset {asset_id} deleted.', 'info')
    return redirect(url_for('assets'))


@app.route('/issues')
@login_required
def issues():
    conn = get_db()
    c = conn.cursor()
    severity = request.args.get('severity', '')
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '').strip()
    query = """
        SELECT i.*, a.name as asset_name FROM issues i
        JOIN assets a ON i.asset_id = a.asset_id WHERE 1=1
    """
    params = []
    if severity:
        query += " AND i.severity=?"
        params.append(severity)
    if status_filter:
        query += " AND i.status=?"
        params.append(status_filter)
    if search:
        query += " AND (i.title LIKE ? OR i.asset_id LIKE ? OR a.name LIKE ?)"
        s = f'%{search}%'
        params.extend([s, s, s])
    query += " ORDER BY i.created_at DESC"
    c.execute(query, params)
    issue_list = c.fetchall()
    conn.close()
    return render_template('issues.html',
        issues=issue_list, severity=severity,
        status_filter=status_filter, search=search, format_date=format_date
    )


@app.route('/issues/new', methods=['GET', 'POST'])
@login_required
def add_issue():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT asset_id, name FROM assets ORDER BY asset_id")
    asset_list = c.fetchall()
    if request.method == 'POST':
        try:
            conn.execute('''
                INSERT INTO issues (asset_id, title, description, severity, status, reported_by, reported_date)
                VALUES (?,?,?,?,?,?,?)
            ''', (
                request.form.get('asset_id'), request.form.get('title'),
                request.form.get('description'), request.form.get('severity', 'Medium'),
                request.form.get('status', 'Open'), request.form.get('reported_by'),
                request.form.get('reported_date') or date.today().strftime('%Y-%m-%d'),
            ))
            conn.commit()
            flash('Issue logged successfully!', 'success')
            return redirect(url_for('issues'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
        finally:
            conn.close()
    prefill_asset = request.args.get('asset_id', '')
    conn.close()
    return render_template('issue_form.html', issue=None, assets=asset_list, prefill_asset=prefill_asset)


@app.route('/issues/<int:issue_id>/resolve', methods=['POST'])
@login_required
def resolve_issue(issue_id):
    notes = request.form.get('resolution_notes', '')
    conn = get_db()
    conn.execute('''
        UPDATE issues SET status='Resolved', resolved_date=?, resolution_notes=? WHERE id=?
    ''', (date.today().strftime('%Y-%m-%d'), notes, issue_id))
    conn.commit()
    conn.close()
    flash('Issue marked as resolved.', 'success')
    return redirect(url_for('issues'))


@app.route('/deployments/new', methods=['POST'])
@login_required
def add_deployment():
    conn = get_db()
    try:
        conn.execute('''
            INSERT INTO deployments (asset_id, deployed_to, deployed_by, deploy_date, notes)
            VALUES (?,?,?,?,?)
        ''', (
            request.form.get('asset_id'), request.form.get('deployed_to'),
            request.form.get('deployed_by'),
            request.form.get('deploy_date') or date.today().strftime('%Y-%m-%d'),
            request.form.get('notes'),
        ))
        conn.commit()
        flash('Deployment record added!', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    finally:
        conn.close()
    return redirect(url_for('asset_detail', asset_id=request.form.get('asset_id')))


@app.route('/export/csv')
@login_required
def export_csv():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM assets ORDER BY asset_id")
    rows = c.fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Asset ID', 'Name', 'Category', 'Manufacturer', 'Serial Number',
                     'Location', 'Assigned To', 'Install Date', 'Warranty Expiry', 'Status', 'Notes'])
    for row in rows:
        writer.writerow([row['asset_id'], row['name'], row['category'], row['manufacturer'],
                         row['serial_number'], row['location'], row['assigned_to'],
                         row['install_date'], row['warranty_expiry'], row['status'], row['notes']])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'assets_{date.today().strftime("%Y%m%d")}.csv'
    )


@app.route('/api/next-id/<category>')
@login_required
def next_id(category):
    return jsonify({'id': generate_asset_id(category)})


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
