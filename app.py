from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import threading
import webbrowser
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'studforge-sk-2024-xK9mP2qR'
DATABASE = 'studforge.db'

STATUSES = {
    'anfrage':    {'label': 'Anfrage',    'css': 'anfrage'},
    'angeboten':  {'label': 'Angeboten',  'css': 'angeboten'},
    'bestaetigt': {'label': 'Bestätigt',  'css': 'bestaetigt'},
    'druck':      {'label': 'Im Druck',   'css': 'druck'},
    'fertig':     {'label': 'Fertig',     'css': 'fertig'},
    'abgeholt':   {'label': 'Abgeholt',   'css': 'abgeholt'},
    'storniert':  {'label': 'Storniert',  'css': 'storniert'},
}

MATERIALS = [
    'Resin (Standard)', 'Resin (ABS-Like)', 'Resin (Flex)', 'Resin (Water-Washable)',
    'PLA', 'PLA+', 'PETG', 'ABS', 'ASA', 'TPU', 'Nylon', 'PC',
    'CNC – Holz', 'CNC – Aluminium', 'CNC – Kunststoff',
    'Sonstiges',
]

CATEGORIES = [
    '3D Druck – Resin', '3D Druck – FDM', 'CNC Fräsen',
    'Nachbearbeitung', 'Design & Modellierung', 'Sonstiges',
]


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS customers (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT    NOT NULL,
            email     TEXT    DEFAULT '',
            phone     TEXT    DEFAULT '',
            address   TEXT    DEFAULT '',
            notes     TEXT    DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS products (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            description TEXT    DEFAULT '',
            price       REAL    DEFAULT 0.0,
            price_unit  TEXT    DEFAULT 'Stück',
            material    TEXT    DEFAULT '',
            category    TEXT    DEFAULT '',
            active      INTEGER DEFAULT 1,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS orders (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number    TEXT,
            customer_id     INTEGER,
            title           TEXT    NOT NULL,
            description     TEXT    DEFAULT '',
            status          TEXT    DEFAULT 'anfrage',
            material        TEXT    DEFAULT '',
            color           TEXT    DEFAULT '',
            layer_height    TEXT    DEFAULT '',
            infill          TEXT    DEFAULT '',
            supports        TEXT    DEFAULT '',
            file_name       TEXT    DEFAULT '',
            quantity        INTEGER DEFAULT 1,
            estimated_price REAL    DEFAULT 0.0,
            final_price     REAL    DEFAULT 0.0,
            paid            INTEGER DEFAULT 0,
            notes           TEXT    DEFAULT '',
            due_date        DATE,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
    ''')
    db.commit()
    db.close()


def next_order_number():
    db = get_db()
    year = datetime.now().year
    count = db.execute(
        "SELECT COUNT(*) FROM orders WHERE strftime('%Y', created_at) = ?",
        (str(year),)
    ).fetchone()[0]
    db.close()
    return f'SF-{year}-{count + 1:04d}'


@app.context_processor
def inject_globals():
    return dict(STATUSES=STATUSES, MATERIALS=MATERIALS, CATEGORIES=CATEGORIES, now=datetime.now())


# ── Dashboard ──────────────────────────────────────────────────────────────────

@app.route('/')
def dashboard():
    db = get_db()
    stats = {
        'customers':     db.execute('SELECT COUNT(*) FROM customers').fetchone()[0],
        'orders_total':  db.execute('SELECT COUNT(*) FROM orders').fetchone()[0],
        'orders_active': db.execute(
            "SELECT COUNT(*) FROM orders WHERE status NOT IN ('abgeholt','storniert')"
        ).fetchone()[0],
        'revenue_month': db.execute(
            "SELECT COALESCE(SUM(final_price),0) FROM orders "
            "WHERE strftime('%Y-%m',created_at)=strftime('%Y-%m','now') AND paid=1"
        ).fetchone()[0],
    }
    recent = db.execute('''
        SELECT o.*, c.name customer_name
        FROM orders o LEFT JOIN customers c ON o.customer_id = c.id
        ORDER BY o.created_at DESC LIMIT 10
    ''').fetchall()
    counts = {r['status']: r['cnt'] for r in db.execute(
        'SELECT status, COUNT(*) cnt FROM orders GROUP BY status'
    ).fetchall()}
    db.close()
    return render_template('dashboard.html', stats=stats, recent=recent, counts=counts)


# ── Kunden ─────────────────────────────────────────────────────────────────────

@app.route('/kunden')
def kunden_list():
    q = request.args.get('q', '')
    db = get_db()
    if q:
        rows = db.execute(
            "SELECT c.*, COUNT(o.id) cnt FROM customers c "
            "LEFT JOIN orders o ON c.id = o.customer_id "
            "WHERE c.name LIKE ? OR c.email LIKE ? OR c.phone LIKE ? "
            "GROUP BY c.id ORDER BY c.name",
            (f'%{q}%', f'%{q}%', f'%{q}%')
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT c.*, COUNT(o.id) cnt FROM customers c "
            "LEFT JOIN orders o ON c.id = o.customer_id "
            "GROUP BY c.id ORDER BY c.name"
        ).fetchall()
    db.close()
    return render_template('kunden/list.html', customers=rows, q=q)


@app.route('/kunden/neu', methods=['GET', 'POST'])
def kunden_neu():
    if request.method == 'POST':
        f = request.form
        db = get_db()
        db.execute(
            'INSERT INTO customers (name,email,phone,address,notes) VALUES (?,?,?,?,?)',
            (f['name'], f.get('email', ''), f.get('phone', ''), f.get('address', ''), f.get('notes', ''))
        )
        db.commit(); db.close()
        flash('Kunde erfolgreich erstellt!', 'success')
        return redirect(url_for('kunden_list'))
    return render_template('kunden/form.html', customer=None, page_title='Neuer Kunde')


@app.route('/kunden/<int:id>')
def kunden_detail(id):
    db = get_db()
    c = db.execute('SELECT * FROM customers WHERE id = ?', (id,)).fetchone()
    if not c:
        db.close(); flash('Kunde nicht gefunden.', 'danger')
        return redirect(url_for('kunden_list'))
    orders = db.execute(
        'SELECT * FROM orders WHERE customer_id = ? ORDER BY created_at DESC', (id,)
    ).fetchall()
    db.close()
    return render_template('kunden/detail.html', customer=c, orders=orders)


@app.route('/kunden/<int:id>/bearbeiten', methods=['GET', 'POST'])
def kunden_edit(id):
    db = get_db()
    c = db.execute('SELECT * FROM customers WHERE id = ?', (id,)).fetchone()
    if not c:
        db.close(); flash('Kunde nicht gefunden.', 'danger')
        return redirect(url_for('kunden_list'))
    if request.method == 'POST':
        f = request.form
        db.execute(
            'UPDATE customers SET name=?,email=?,phone=?,address=?,notes=? WHERE id=?',
            (f['name'], f.get('email', ''), f.get('phone', ''), f.get('address', ''), f.get('notes', ''), id)
        )
        db.commit(); db.close()
        flash('Kunde aktualisiert!', 'success')
        return redirect(url_for('kunden_detail', id=id))
    db.close()
    return render_template('kunden/form.html', customer=c, page_title='Kunde bearbeiten')


@app.route('/kunden/<int:id>/loeschen', methods=['POST'])
def kunden_delete(id):
    db = get_db()
    db.execute('DELETE FROM customers WHERE id = ?', (id,))
    db.commit(); db.close()
    flash('Kunde gelöscht.', 'info')
    return redirect(url_for('kunden_list'))


# ── Produkte ───────────────────────────────────────────────────────────────────

@app.route('/produkte')
def produkte_list():
    db = get_db()
    products = db.execute('SELECT * FROM products ORDER BY category, name').fetchall()
    db.close()
    return render_template('produkte/list.html', products=products)


@app.route('/produkte/neu', methods=['GET', 'POST'])
def produkte_neu():
    if request.method == 'POST':
        f = request.form
        db = get_db()
        db.execute(
            'INSERT INTO products (name,description,price,price_unit,material,category) VALUES (?,?,?,?,?,?)',
            (f['name'], f.get('description', ''), float(f.get('price', 0) or 0),
             f.get('price_unit', 'Stück'), f.get('material', ''), f.get('category', ''))
        )
        db.commit(); db.close()
        flash('Produkt/Dienst hinzugefügt!', 'success')
        return redirect(url_for('produkte_list'))
    return render_template('produkte/form.html', product=None, page_title='Neues Produkt')


@app.route('/produkte/<int:id>/bearbeiten', methods=['GET', 'POST'])
def produkte_edit(id):
    db = get_db()
    p = db.execute('SELECT * FROM products WHERE id = ?', (id,)).fetchone()
    if not p:
        db.close(); flash('Produkt nicht gefunden.', 'danger')
        return redirect(url_for('produkte_list'))
    if request.method == 'POST':
        f = request.form
        db.execute(
            'UPDATE products SET name=?,description=?,price=?,price_unit=?,material=?,category=?,active=? WHERE id=?',
            (f['name'], f.get('description', ''), float(f.get('price', 0) or 0),
             f.get('price_unit', 'Stück'), f.get('material', ''), f.get('category', ''),
             1 if f.get('active') else 0, id)
        )
        db.commit(); db.close()
        flash('Produkt aktualisiert!', 'success')
        return redirect(url_for('produkte_list'))
    db.close()
    return render_template('produkte/form.html', product=p, page_title='Produkt bearbeiten')


@app.route('/produkte/<int:id>/loeschen', methods=['POST'])
def produkte_delete(id):
    db = get_db()
    db.execute('DELETE FROM products WHERE id = ?', (id,))
    db.commit(); db.close()
    flash('Produkt gelöscht.', 'info')
    return redirect(url_for('produkte_list'))


# ── Aufträge ───────────────────────────────────────────────────────────────────

@app.route('/auftraege')
def auftraege_list():
    status_f = request.args.get('status', '')
    q = request.args.get('q', '')
    db = get_db()
    sql = ("SELECT o.*, c.name customer_name FROM orders o "
           "LEFT JOIN customers c ON o.customer_id = c.id WHERE 1=1")
    params = []
    if status_f:
        sql += ' AND o.status = ?'; params.append(status_f)
    if q:
        sql += ' AND (o.title LIKE ? OR o.order_number LIKE ? OR c.name LIKE ?)'
        params += [f'%{q}%', f'%{q}%', f'%{q}%']
    sql += ' ORDER BY o.created_at DESC'
    orders = db.execute(sql, params).fetchall()
    counts = {r['status']: r['cnt'] for r in db.execute(
        'SELECT status, COUNT(*) cnt FROM orders GROUP BY status'
    ).fetchall()}
    db.close()
    return render_template('auftraege/list.html', orders=orders, status_f=status_f, q=q, counts=counts)


@app.route('/auftraege/neu', methods=['GET', 'POST'])
def auftraege_neu():
    db = get_db()
    customers = db.execute('SELECT id, name FROM customers ORDER BY name').fetchall()
    if request.method == 'POST':
        f = request.form
        num = next_order_number()
        db.execute('''
            INSERT INTO orders
            (order_number,customer_id,title,description,status,material,color,
             layer_height,infill,supports,file_name,quantity,estimated_price,final_price,notes,due_date)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            num,
            f.get('customer_id') or None,
            f['title'], f.get('description', ''),
            f.get('status', 'anfrage'), f.get('material', ''), f.get('color', ''),
            f.get('layer_height', ''), f.get('infill', ''), f.get('supports', ''),
            f.get('file_name', ''), int(f.get('quantity', 1) or 1),
            float(f.get('estimated_price', 0) or 0),
            float(f.get('final_price', 0) or 0),
            f.get('notes', ''), f.get('due_date') or None
        ))
        db.commit()
        oid = db.execute('SELECT last_insert_rowid()').fetchone()[0]
        db.close()
        flash(f'Auftrag {num} erstellt!', 'success')
        return redirect(url_for('auftraege_detail', id=oid))
    db.close()
    return render_template('auftraege/form.html', order=None, customers=customers, page_title='Neuer Auftrag')


@app.route('/auftraege/<int:id>')
def auftraege_detail(id):
    db = get_db()
    o = db.execute('''
        SELECT o.*, c.name customer_name, c.email customer_email, c.phone customer_phone
        FROM orders o LEFT JOIN customers c ON o.customer_id = c.id WHERE o.id = ?
    ''', (id,)).fetchone()
    if not o:
        db.close(); flash('Auftrag nicht gefunden.', 'danger')
        return redirect(url_for('auftraege_list'))
    db.close()
    return render_template('auftraege/detail.html', order=o)


@app.route('/auftraege/<int:id>/bearbeiten', methods=['GET', 'POST'])
def auftraege_edit(id):
    db = get_db()
    o = db.execute('SELECT * FROM orders WHERE id = ?', (id,)).fetchone()
    customers = db.execute('SELECT id, name FROM customers ORDER BY name').fetchall()
    if not o:
        db.close(); flash('Auftrag nicht gefunden.', 'danger')
        return redirect(url_for('auftraege_list'))
    if request.method == 'POST':
        f = request.form
        db.execute('''
            UPDATE orders SET
            customer_id=?,title=?,description=?,status=?,material=?,color=?,
            layer_height=?,infill=?,supports=?,file_name=?,quantity=?,
            estimated_price=?,final_price=?,paid=?,notes=?,due_date=?,
            updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        ''', (
            f.get('customer_id') or None,
            f['title'], f.get('description', ''),
            f.get('status', 'anfrage'), f.get('material', ''), f.get('color', ''),
            f.get('layer_height', ''), f.get('infill', ''), f.get('supports', ''),
            f.get('file_name', ''), int(f.get('quantity', 1) or 1),
            float(f.get('estimated_price', 0) or 0),
            float(f.get('final_price', 0) or 0),
            1 if f.get('paid') else 0,
            f.get('notes', ''), f.get('due_date') or None, id
        ))
        db.commit(); db.close()
        flash('Auftrag aktualisiert!', 'success')
        return redirect(url_for('auftraege_detail', id=id))
    db.close()
    return render_template('auftraege/form.html', order=o, customers=customers, page_title='Auftrag bearbeiten')


@app.route('/auftraege/<int:id>/status', methods=['POST'])
def auftraege_status(id):
    ns = request.form.get('status')
    if ns in STATUSES:
        db = get_db()
        db.execute('UPDATE orders SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?', (ns, id))
        db.commit(); db.close()
        flash(f'Status auf "{STATUSES[ns]["label"]}" gesetzt.', 'success')
    return redirect(url_for('auftraege_detail', id=id))


@app.route('/auftraege/<int:id>/loeschen', methods=['POST'])
def auftraege_delete(id):
    db = get_db()
    db.execute('DELETE FROM orders WHERE id = ?', (id,))
    db.commit(); db.close()
    flash('Auftrag gelöscht.', 'info')
    return redirect(url_for('auftraege_list'))


if __name__ == '__main__':
    init_db()

    def _open_browser():
        import time; time.sleep(1.4)
        webbrowser.open('http://127.0.0.1:5000')

    threading.Thread(target=_open_browser, daemon=True).start()
    print('\n  ✦  Studforge läuft auf http://127.0.0.1:5000\n')
    app.run(host='127.0.0.1', port=5000, debug=False)
