"""
Studforge Server — läuft NUR auf dem Haupt-PC.

Dieses Programm hostet die Datenbank und macht sie über einen
Cloudflare-Tunnel im Internet erreichbar. Die aktuelle Adresse wird
automatisch ins GitHub-Repo geschrieben, wo die Client-Apps sie finden.

Schutz: startet nur, wenn die Datei server.key daneben liegt.
Die Datei ist gitignored und existiert ausschliesslich auf dem Haupt-PC —
auf jedem anderen Rechner verweigert der Server den Start.

Wird über den Windows-Autostart (Registry "StudforgeServer") gestartet.
"""
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

PORT      = 5000
LOCAL_URL = f'http://127.0.0.1:{PORT}'
KEY_PATH  = os.path.join(APP_DIR, 'server.key')
LOG_PATH  = os.path.join(APP_DIR, 'server.log')
CF_EXE    = os.path.join(APP_DIR, 'cloudflared.exe')
URL_FILE  = os.path.join(APP_DIR, 'server_url.txt')

CF_DOWNLOAD = ('https://github.com/cloudflare/cloudflared/releases/'
               'latest/download/cloudflared-windows-amd64.exe')

CREATE_NO_WINDOW = 0x08000000


def log(msg):
    line = f'[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n'
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line)
    except Exception:
        pass


def http_ok(url, timeout=2.5):
    try:
        urllib.request.urlopen(url.rstrip('/') + '/api/version', timeout=timeout)
        return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def run_flask():
    from app import app, init_db
    init_db()
    app.run(host='0.0.0.0', port=PORT, debug=False,
            use_reloader=False, threaded=True)


# ── Tunnel & Veröffentlichung ────────────────────────────────────────────────

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


def public_reachable(url, timeout=10):
    """Antwortet die ÖFFENTLICHE Adresse wirklich (von aussen geroutet)?"""
    try:
        urllib.request.urlopen(url.rstrip('/') + '/api/version', timeout=timeout)
        return True
    except urllib.error.HTTPError:
        return True          # 401 etc. = Server antwortet, Tunnel lebt
    except Exception:
        return False


def tunnel_loop():
    if not ensure_cloudflared():
        return
    url_re = re.compile(r'https://[a-z0-9-]+\.trycloudflare\.com')
    state = {'url': None}

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

        state['url'] = None

        # Adresse aus der Tunnel-Ausgabe lesen & veröffentlichen (eigener Thread,
        # damit der Health-Check unten parallel laufen kann)
        def read_output():
            for line in proc.stdout:
                m = url_re.search(line)
                if m and m.group(0) != state['url']:
                    state['url'] = m.group(0)
                    log(f'Öffentliche Adresse: {state["url"]}')
                    try:
                        publish_url(state['url'])
                    except Exception as e:
                        log(f'Publish-Fehler (Tunnel läuft weiter): {e}')
        threading.Thread(target=read_output, daemon=True).start()

        # Health-Check: erkennt auch einen STILL gestorbenen Tunnel
        # (Prozess lebt, routet aber nichts mehr) und erzwingt Neustart.
        strikes = 0
        while proc.poll() is None:
            time.sleep(15)
            if not state['url']:
                continue                      # Adresse noch nicht da → warten
            if public_reachable(state['url']):
                strikes = 0
            else:
                strikes += 1
                log(f'Tunnel antwortet nicht ({strikes}/3): {state["url"]}')
                if strikes >= 3:
                    log('Tunnel ist tot — wird neu gestartet (neue Adresse folgt).')
                    break

        try:
            proc.kill()
        except Exception:
            pass
        log('Tunnel wird neu aufgebaut in 4s ...')
        time.sleep(4)


# ── Start ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':

    # Schutz: ohne server.key startet der Server nicht (nur Haupt-PC hat sie)
    if not os.path.exists(KEY_PATH):
        log('server.key fehlt — Start verweigert (das ist nicht der Haupt-PC).')
        try:
            import tkinter as tk
            from tkinter import messagebox
            r = tk.Tk(); r.withdraw()
            messagebox.showerror(
                'Studforge Server',
                'Der Studforge-Server kann nur auf dem Haupt-PC laufen.\n\n'
                'Auf diesem Computer bitte die normale Studforge-App benutzen.')
        except Exception:
            pass
        sys.exit(1)

    if http_ok(LOCAL_URL, timeout=1.5):
        log('Server läuft bereits — zweiter Start übersprungen.')
        sys.exit(0)

    log('Studforge-Server wird gestartet ...')
    threading.Thread(target=tunnel_loop, daemon=True).start()
    run_flask()   # blockiert für immer
