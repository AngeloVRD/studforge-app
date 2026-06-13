"""
Studforge App (Client)

Verbindet sich mit dem Studforge-Server:
  1. Läuft auf diesem PC der Server (Haupt-PC)? → direkt verbinden
  2. Sonst: aktuelle Server-Adresse automatisch von GitHub holen
  3. Fallback: Adresse manuell eingeben

Der Server selbst ist ein eigenes Programm (server.py) und läuft
ausschliesslich auf dem Haupt-PC — diese App hier ist nur das Fenster.
"""
import json
import os
import sys
import time
import urllib.request

APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_DIR)

LOCAL_URL   = 'http://127.0.0.1:5000'
CONFIG_PATH = os.path.join(APP_DIR, 'config.json')

# Hier veröffentlicht der Server seine aktuelle Adresse
RAW_URL = 'https://raw.githubusercontent.com/AngeloVRD/studforge-app/main/server_url.txt'


def load_config():
    try:
        with open(CONFIG_PATH, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg):
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def studforge_at(url, timeout=4):
    """Prüft ob unter url wirklich ein Studforge-Server antwortet."""
    try:
        with urllib.request.urlopen(url.rstrip('/') + '/api/version',
                                    timeout=timeout) as r:
            return b'"v"' in r.read(200)
    except urllib.error.HTTPError as e:
        return e.code == 401      # 401 = Login nötig → Studforge antwortet
    except Exception:
        return False


def discover_server(cfg):
    """Aktuelle Server-Adresse von GitHub holen; Fallback: letzte bekannte."""
    try:
        req = urllib.request.Request(
            RAW_URL + f'?t={int(time.time())}',
            headers={'Cache-Control': 'no-cache'})
        with urllib.request.urlopen(req, timeout=6) as r:
            url = r.read().decode('utf-8').strip()
        if url.startswith('http') and studforge_at(url, timeout=6):
            if cfg.get('last_url') != url:
                cfg['last_url'] = url
                save_config(cfg)
            return url
    except Exception:
        pass

    last = cfg.get('last_url', '')
    if last and studforge_at(last, timeout=6):
        return last
    return None


def fetch_published_url():
    """Nur die auf GitHub veröffentlichte Adresse holen (ohne Prüfung)."""
    try:
        req = urllib.request.Request(
            RAW_URL + f'?t={int(time.time())}',
            headers={'Cache-Control': 'no-cache'})
        with urllib.request.urlopen(req, timeout=6) as r:
            url = r.read().decode('utf-8').strip()
        return url if url.startswith('http') else None
    except Exception:
        return None


def discover_server_retry(cfg, attempts=5, delay=3):
    """Mehrere Versuche — überbrückt die Phase, in der der Server gerade neu startet."""
    for i in range(attempts):
        url = discover_server(cfg)
        if url:
            return url
        time.sleep(delay)
    return None


# ── Dialog: Server nicht erreichbar (dunkles Design) ─────────────────────────

BG, BG2, BORDER = '#0a0a0a', '#161616', '#2a2a2a'
ORANGE, WHITE, GRAY = '#f97316', '#ffffff', '#9a9a9a'


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
        status.config(text='Verbinde ...', fg=GRAY)
        root.update()
        if not url:
            url = discover_server(cfg)
            if url:
                result['url'] = url
                root.destroy()
                return
            status.config(text='Immer noch nicht erreichbar.', fg='#ef4444')
            return
        if studforge_at(url, timeout=6):
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


# ── Selbstheilender Watchdog ─────────────────────────────────────────────────
# Läuft im Hintergrund, solange das Fenster offen ist. Erkennt, wenn die
# Server-Adresse tot ist (Server neu gestartet → neue Cloudflare-Adresse) und
# lädt das Fenster automatisch auf die neue Adresse — ohne Zutun des Nutzers.

def make_watchdog(window, cfg, initial_url):
    state = {'url': initial_url}

    def is_local(u):
        return u.startswith('http://127.0.0.1') or u.startswith('http://localhost')

    def watchdog():
        time.sleep(8)                       # Seite erst mal laden lassen
        miss = 0
        while True:
            time.sleep(6)
            current = state['url']

            # Haupt-PC bleibt immer lokal — nichts umzuschalten
            if is_local(current) and studforge_at(LOCAL_URL, timeout=2):
                continue

            if studforge_at(current, timeout=6):
                miss = 0
                # Läuft noch — aber hat GitHub schon eine NEUERE Adresse?
                pub = fetch_published_url()
                if pub and pub != current and studforge_at(pub, timeout=6):
                    state['url'] = pub
                    cfg['last_url'] = pub
                    save_config(cfg)
                    try: window.load_url(pub)
                    except Exception: pass
                continue

            # Adresse antwortet nicht
            miss += 1
            if miss < 2:
                continue                    # kurzer Aussetzer → noch nicht reagieren

            # Neue Adresse suchen (mehrere Versuche, Server startet evtl. gerade neu)
            new = None
            for _ in range(20):             # bis ~2 Min lang versuchen
                # Haupt-PC: zuerst wieder lokal probieren
                if studforge_at(LOCAL_URL, timeout=2):
                    new = LOCAL_URL
                    break
                cand = discover_server(cfg)
                if cand and cand != current:
                    new = cand
                    break
                time.sleep(6)

            if new:
                state['url'] = new
                miss = 0
                try: window.load_url(new)
                except Exception: pass

    return watchdog


# ── Start ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    cfg = load_config()

    # Haupt-PC? Dann direkt mit dem lokalen Server verbinden (schnellster Weg)
    if studforge_at(LOCAL_URL, timeout=1.0):
        url = LOCAL_URL
    else:
        url = discover_server_retry(cfg)    # mehrere Versuche statt sofort aufgeben
        if not url:
            url = manual_url_dialog(cfg)
        if not url:
            sys.exit(0)

    import webview

    window = webview.create_window(
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
    # Watchdog wird gestartet, sobald die GUI läuft, und hält die Verbindung selbstständig aufrecht
    webview.start(make_watchdog(window, cfg, url),
                  private_mode=False, debug=False)
