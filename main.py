"""
Studforge Desktop App
Starts Flask in the background and opens a native OS desktop window.
"""
import threading
import time
import os
import sys

# Ensure working directory is the script's folder
os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))

HOST = '127.0.0.1'
PORT = 5000
URL  = f'http://{HOST}:{PORT}'


def run_server():
    from app import app, init_db
    init_db()
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)


def wait_for_server(timeout=12):
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(URL, timeout=0.5)
            return True
        except Exception:
            time.sleep(0.25)
    return False


if __name__ == '__main__':
    import webview

    # Start Flask in background thread
    threading.Thread(target=run_server, daemon=True).start()

    if not wait_for_server():
        import tkinter.messagebox as mb
        mb.showerror('Studforge', 'Server konnte nicht gestartet werden.')
        sys.exit(1)

    # Open native desktop window
    webview.create_window(
        title='Studforge — 3D Manufaktur',
        url=URL,
        width=1320,
        height=840,
        min_size=(980, 640),
        background_color='#080808',
        text_select=False,
        confirm_close=False,
    )
    webview.start(debug=False)
