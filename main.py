"""
Studforge Desktop App — Server & Client

Modi (config.json):
  server  — dieser PC hostet die Daten. Flask läuft lokal, ein Cloudflare-
            Tunnel macht ihn übers Internet erreichbar. Die öffentliche
            Adresse wird automatisch ins GitHub-Repo geschrieben.
  client  — verbindet sich mit dem Server (Adresse wird automatisch von
            GitHub geholt, Fallback: manuell eingeben).

Start ohne Argumente  → Fenster öffnen (Modus laut config.json)
Start mit --headless  → nur Server im Hintergrund (Windows-Autostart)
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_DIR)

PORT        = 5000
LOCAL_URL   = f'http://127.0.0.1:{PORT}'
CONFIG_PATH = os.path.join(APP_DIR, 'config.json')
LOG_PATH    = os.path.join(APP_DIR, 'server.log')
CF_EXE      = os.path.join(APP_DIR, 'cloudflared.exe')
URL_FILE    = os.path.join(APP_DIR, 'server_url.txt')

# Hier veröffentlicht der Server seine aktuelle Adresse (Repo muss public sein)
RAW_URL = 'https://raw.githubusercontent.com/AngeloVRD/studforge-app/main/server_url.txt'

CF_DOWNLOAD = ('https://github.com/cloudflare/cloudflared/releases/'
               'latest/download/cloudflared-windows-amd64.exe')

CREATE_NO_WINDOW = 0x08000000


# ── Hilfsfunktionen ──────────────────────────────────────────────────────────

def log(msg):
    """In Datei loggen — unter pythonw gibt es keine Konsole."""
    line = f'[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n'
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line)
    except Exception:
        pass


def load_config():
    try:
        with open(CONFIG_PATH, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def save_config(cfg):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def http_ok(url, timeout=2.5):
    """Prüft ob ein Studforge-Server unter url antwortet (401 zählt als ja)."""
    try:
        urllib.request.urlopen(url.rstrip('/') + '/api/version', timeout=timeout)
        return True
    except urllib.error.HTTPError:
        return True          # Server hat geantwortet (z.B. 401 = Login nötig)
    except Exception:
        return False


def run_flask():
    from app import app, init_db
    init_db()
    # 0.0.0.0 = auch im lokalen Netzwerk erreichbar; threaded = mehrere Clients
    app.run(host='0.0.0.0', port=PORT, debug=False,
            use_reloader=False, threaded=True)


def wait_for_server(url, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if http_ok(url, timeout=0.8):
            return True
        time.sleep(0.25)
    return False


# ── Cloudflare-Tunnel (Server-Modus) ─────────────────────────────────────────

def ensure_cloudflared():
    if os.path.exists(CF_EXE):
        return True
    log('cloudflared.exe wird heruntergeladen ...')
    try:
        urllib.request.urlretrieve(CF_DOWNLOAD, CF_EXE + '.tmp')
        os.replace(CF_EXE + '.tmp', CF_EXE)
        log('cloudflared.exe heruntergeladen.')
        return True
    except Exception as e:
        log(f'cloudflared Download fehlgeschlagen: {e}')
        return False


def find_git():
    """git.exe suchen — ist bei pythonw oft nicht im PATH."""
    import shutil
    g = shutil.which('git')
    if g:
        return g
    for p in (r'C:\Program Files\Git\cmd\git.exe',
              r'C:\Program Files (x86)\Git\cmd\git.exe',
              os.path.expandvars(r'%LOCALAPPDATA%\Programs\Git\cmd\git.exe')):
        if os.path.exists(p):
            return p
    return None


GIT_EXE = find_git()


def git(*args):
    """Git-Befehl im App-Ordner ausführen, Ergebnis zurückgeben."""
    if not GIT_EXE:
        raise FileNotFoundError('git.exe nicht gefunden')
    return subprocess.run(
        [GIT_EXE, '-C', APP_DIR] + list(args),
        capture_output=True, text=True, timeout=90,
        creationflags=CREATE_NO_WINDOW)


def publish_url(url):
    """Tunnel-Adresse in server_url.txt schreiben und zu GitHub pushen."""
    try:
        with open(URL_FILE, 'w', encoding='utf-8') as f:
            f.write(url + '\n')
    except Exception as e:
        log(f'server_url.txt schreiben fehlgeschlagen: {e}')
        return

    if not os.path.isdir(os.path.join(APP_DIR, '.git')):
        log('Kein Git-Repo — Adresse wird nicht veröffentlicht.')
        return

    try:
        git('add', 'server_url.txt')
        git('commit', '-m', 'Server-Adresse aktualisiert', '--', 'server_url.txt')
        r = git('push')
        if r.returncode != 0:
            git('pull', '--rebase')
            r = git('push')
        log('Adresse veröffentlicht.' if r.returncode == 0
            else f'Git push fehlgeschlagen: {r.stderr.strip()[:200]}')
    except Exception as e:
        log(f'Veröffentlichen fehlgeschlagen: {e}')


def tunnel_loop():
    """Cloudflare-Tunnel starten und am Leben halten; Adresse veröffentlichen."""
    if not ensure_cloudflared():
        return
    url_re = re.compile(r'https://[a-z0-9-]+\.trycloudflare\.com')
    last_published = None

    while True:
        log('Tunnel wird gestartet ...')
        try:
            proc = subprocess.Popen(
                [CF_EXE, 'tunnel', '--url', LOCAL_URL, '--no-autoupdate'],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=CREATE_NO_WINDOW)
        except Exception as e:
            log(f'Tunnel-Start fehlgeschlagen: {e}')
            time.sleep(30)
            continue

        for line in proc.stdout:
            m = url_re.search(line)
            if m and m.group(0) != last_published:
                last_published = m.group(0)
                log(f'Öffentliche Adresse: {last_published}')
                try:
                    publish_url(last_published)
                except Exception as e:
                    log(f'Publish-Fehler (Tunnel läuft weiter): {e}')

        proc.wait()
        log(f'Tunnel beendet (Code {proc.returncode}) — Neustart in 5s ...')
        time.sleep(5)


def start_server_stack():
    """Flask + Tunnel als Hintergrund-Threads starten."""
    threading.Thread(target=run_flask, daemon=True).start()
    wait_for_server(LOCAL_URL)
    threading.Thread(target=tunnel_loop, daemon=True).start()


# ── Server-Adresse finden (Client-Modus) ─────────────────────────────────────

def discover_server(cfg):
    """Aktuelle Server-Adresse von GitHub holen; Fallback: letzte bekannte."""
    try:
        req = urllib.request.Request(
            RAW_URL + f'?t={int(time.time())}',
            headers={'Cache-Control': 'no-cache'})
        with urllib.request.urlopen(req, timeout=6) as r:
            url = r.read().decode('utf-8').strip()
        if url.startswith('http') and http_ok(url, timeout=6):
            if cfg.get('last_url') != url:
                cfg['last_url'] = url
                save_config(cfg)
            return url
    except Exception as e:
        log(f'Adress-Abruf von GitHub fehlgeschlagen: {e}')

    last = cfg.get('last_url', '')
    if last and http_ok(last, timeout=6):
        return last
    return None


# ── Einrichtungs-Dialoge (tkinter, dunkles Design) ───────────────────────────

BG, BG2, BORDER = '#0a0a0a', '#161616', '#2a2a2a'
ORANGE, WHITE, GRAY = '#f97316', '#ffffff', '#9a9a9a'


def first_run_dialog():
    """Beim ersten Start fragen: Server oder Mitarbeiter-PC? → config dict."""
    import tkinter as tk

    result = {}
    root = tk.Tk()
    root.title('Studforge — Einrichtung')
    root.configure(bg=BG)
    root.resizable(False, False)
    w, h = 430, 360
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f'{w}x{h}+{x}+{y}')
    try:
        root.iconbitmap(os.path.join(APP_DIR, 'icon.ico'))
    except Exception:
        pass

    tk.Label(root, text='STUDFORGE', font=('Segoe UI', 19, 'bold'),
             bg=BG, fg=ORANGE).pack(pady=(30, 2))
    tk.Label(root, text='Wie soll dieser PC verwendet werden?',
             font=('Segoe UI', 10), bg=BG, fg=GRAY).pack(pady=(0, 24))

    def make_btn(parent, title, sub, cmd):
        f = tk.Frame(parent, bg=BG2, highlightbackground=BORDER,
                     highlightthickness=1, cursor='hand2')
        f.pack(fill='x', padx=36, pady=7, ipady=10)
        t = tk.Label(f, text=title, font=('Segoe UI', 11, 'bold'),
                     bg=BG2, fg=WHITE, cursor='hand2')
        t.pack(anchor='w', padx=16, pady=(4, 0))
        s = tk.Label(f, text=sub, font=('Segoe UI', 9),
                     bg=BG2, fg=GRAY, cursor='hand2')
        s.pack(anchor='w', padx=16, pady=(1, 4))
        for el in (f, t, s):
            el.bind('<Button-1>', lambda e: cmd())
            el.bind('<Enter>', lambda e: f.config(highlightbackground=ORANGE))
            el.bind('<Leave>', lambda e: f.config(highlightbackground=BORDER))

    def choose_server():
        result.update({'mode': 'server', 'password': 'studforge'})
        root.destroy()

    def choose_client():
        result.update({'mode': 'client'})
        root.destroy()

    make_btn(root, '🖥  Dieser PC ist der Server',
             'Daten werden hier gespeichert. Läuft im Hintergrund.',
             choose_server)
    make_btn(root, '👥  Als Mitarbeiter verbinden',
             'Verbindet sich automatisch mit dem Studforge-Server.',
             choose_client)

    tk.Label(root, text='Diese Auswahl kann in config.json geändert werden.',
             font=('Segoe UI', 8), bg=BG, fg='#555555').pack(side='bottom', pady=14)

    root.mainloop()
    if not result:
        sys.exit(0)
    return result


def manual_url_dialog(cfg):
    """Server nicht gefunden → Adresse manuell eingeben. Gibt URL oder None."""
    import tkinter as tk

    result = {'url': None}
    root = tk.Tk()
    root.title('Studforge — Server nicht erreichbar')
    root.configure(bg=BG)
    root.resizable(False, False)
    w, h = 430, 250
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f'{w}x{h}+{x}+{y}')
    try:
        root.iconbitmap(os.path.join(APP_DIR, 'icon.ico'))
    except Exception:
        pass

    tk.Label(root, text='Server nicht erreichbar', font=('Segoe UI', 13, 'bold'),
             bg=BG, fg=WHITE).pack(pady=(26, 4))
    tk.Label(root, text='Läuft der Server-PC? Du kannst die Adresse\n'
                        'auch manuell eingeben:',
             font=('Segoe UI', 9), bg=BG, fg=GRAY, justify='center').pack(pady=(0, 14))

    entry = tk.Entry(root, font=('Segoe UI', 10), bg=BG2, fg=WHITE,
                     insertbackground=WHITE, relief='flat',
                     highlightthickness=1, highlightbackground=BORDER,
                     highlightcolor=ORANGE)
    entry.pack(fill='x', padx=36, ipady=8)
    entry.insert(0, cfg.get('last_url', ''))

    status = tk.Label(root, text='', font=('Segoe UI', 9), bg=BG, fg='#ef4444')
    status.pack(pady=(6, 0))

    def connect():
        url = entry.get().strip().rstrip('/')
        if url and not url.startswith('http'):
            url = 'https://' + url
        if not url:
            url = discover_server(cfg)
            if url:
                result['url'] = url
                root.destroy()
                return
            status.config(text='Immer noch nicht erreichbar.')
            return
        status.config(text='Verbinde ...', fg=GRAY)
        root.update()
        if http_ok(url, timeout=6):
            cfg['last_url'] = url
            save_config(cfg)
            result['url'] = url
            root.destroy()
        else:
            status.config(text='Keine Verbindung zu dieser Adresse.', fg='#ef4444')

    btn = tk.Label(root, text='Verbinden', font=('Segoe UI', 10, 'bold'),
                   bg=ORANGE, fg='#111111', cursor='hand2', pady=8)
    btn.pack(fill='x', padx=36, pady=(14, 0))
    btn.bind('<Button-1>', lambda e: connect())
    entry.bind('<Return>', lambda e: connect())

    root.mainloop()
    return result['url']


# ── Start ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':

    # Hintergrund-Modus: nur Server, kein Fenster (Windows-Autostart)
    if '--headless' in sys.argv:
        if http_ok(LOCAL_URL, timeout=1.5):
            log('Server läuft bereits — zweiter Start übersprungen.')
            sys.exit(0)
        log('Headless-Server wird gestartet ...')
        threading.Thread(target=tunnel_loop, daemon=True).start()
        run_flask()                      # blockiert für immer
        sys.exit(0)

    cfg = load_config()
    if not cfg or cfg.get('mode') not in ('server', 'client'):
        cfg = first_run_dialog()
        save_config(cfg)

    import webview

    if cfg['mode'] == 'server':
        url = LOCAL_URL
        if not http_ok(url, timeout=1.5):
            start_server_stack()         # kein Headless-Prozess aktiv → selbst hosten
    else:
        url = discover_server(cfg)
        if not url:
            url = manual_url_dialog(cfg)
        if not url:
            sys.exit(0)

    webview.create_window(
        title='Studforge — 3D Manufaktur',
        url=url,
        width=1320,
        height=840,
        min_size=(980, 640),
        background_color='#080808',
        text_select=False,
        confirm_close=False,
    )
    # private_mode=False: Login-Cookies bleiben gespeichert
    webview.start(private_mode=False, debug=False)
