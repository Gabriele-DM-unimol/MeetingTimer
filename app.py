from queue import Empty, Queue
import random
from automatic_timing import estrai_programma_con_titoli
from flask import Flask, Response, request, jsonify, send_from_directory
import json
import os
import time
import socket
import webbrowser
from threading import Timer
import sys

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=os.path.join(base_path, "fe"))

if os.name == 'nt':
    appdata_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'TimerSincronizzato')
else:
    appdata_dir = os.path.expanduser('~/.timersincronizzato')

os.makedirs(appdata_dir, exist_ok=True)
MEETING_FILE = os.path.join(appdata_dir, "queue.json")

clients = []

def save_meeting(data):
    with open(MEETING_FILE, "w") as f:
        json.dump(data, f)

def load_meeting():
    """Legge lo stato corrente salvato su disco senza resettarlo."""
    if os.path.exists(MEETING_FILE):
        try:
            with open(MEETING_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Server] Errore lettura file, rigenero default: {e}")
    
    return get_clean_default_meeting()

def get_clean_default_meeting():
    """Genera il default pulito, calcola la timeline esatta e lo salva su disco."""
    raw_default = get_default_meeting()
    refreshed_default = refresh_meeting(raw_default)
    save_meeting(refreshed_default)
    return refreshed_default
    
def get_default_meeting():
    path_templates = os.path.join(base_path, "templates.json")
    with open(path_templates, "r") as f:
        templates = json.load(f)
        
    current_wday = time.localtime().tm_wday
    
    if current_wday < 5:
        data = next(x for x in templates if x["name"] == "infrasettimanale_std")
    else:
        data = next(x for x in templates if x["name"] == "fine_settimana_std")
    
    if "endMeetingMode" not in data:
        data["endMeetingMode"] = False

    if data["name"] == "infrasettimanale_std":
        try:
            timers_dinamici = estrai_programma_con_titoli()
            if timers_dinamici:
                timers_dinamici[0]['start'] = data['conferenceStart']
                data["timers"] = timers_dinamici
        except Exception as e:
            print(f"Fallback attivo. Errore automazione scraper: {e}")
            
    return data

@app.route("/")
def client():
    return send_from_directory(os.path.join(base_path, "fe"), "client.html")

@app.route("/admin")
def admin():
    return send_from_directory(os.path.join(base_path, "fe"), "admin.html")

@app.route("/api/templates", methods=["GET"])
def get_templates():
    path_templates = os.path.join(base_path, "templates.json")
    with open(path_templates, "r") as f:
        return jsonify(json.load(f))

@app.route("/api/meeting/start", methods=["GET"])
def get_start():
    # ESAGERAZIONE 2: A ogni richiesta di start/cambio template ricalcola tutto da zero
    print("[Server] Richiesta cambio template / reset: eseguo il refresh totale...")
    default_meeting = get_clean_default_meeting()
    broadcast_message(json.dumps(default_meeting))
    return jsonify(default_meeting)

@app.route("/api/meeting", methods=["GET"])
def get_meeting():
    res = jsonify(load_meeting())
    res.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    res.headers["Pragma"] = "no-cache"
    res.headers["Expires"] = "0"
    return res

@app.route("/api/meeting", methods=["POST"])
def post_meeting():
    data = request.get_json()
    refreshed = refresh_meeting(data)
    save_meeting(refreshed)
    broadcast_message(json.dumps(refreshed))  
    return jsonify({"status": "ok"})

def broadcast_message(message):
    for q in clients:
        q.put(message)

def refresh_meeting(data):
    def get_seconds(time_str):
        h, m, s = map(int, time_str.split(':'))
        return h * 3600 + m * 60 + s
    
    def format_time(seconds):
        h, m, s = int(seconds // 3600), int((seconds % 3600) // 60), int(seconds % 60)
        return f"{h:02}:{m:02}:{s:02}"
        
    conference_end = get_seconds(data['conferenceEnd'])
    conference_start = get_seconds(data['timers'][0]['start'])

    if "endMeetingMode" not in data:
        data["endMeetingMode"] = False

    for timer in data['timers']:
        if 'maxDuration' not in timer or 'duration' not in timer:
            try:
                durata_stimata = get_seconds(timer['end']) - get_seconds(timer['start'])
                if 'maxDuration' not in timer:
                    timer['maxDuration'] = durata_stimata
                if 'duration' not in timer:
                    timer['duration'] = durata_stimata
            except Exception:
                timer['maxDuration'] = 60
                timer['duration'] = 60
        
        if 'duration' not in timer:
            timer['duration'] = timer['maxDuration']

    active_index = next((i for i, t in enumerate(data['timers']) if t['active']), None)
    
    if active_index is None:
        current_time = conference_start
        for timer in data['timers']:
            timer['start'] = format_time(current_time)
            current_time += timer['duration']
            timer['end'] = format_time(current_time)
        return data
    
    total_duration = sum(t['duration'] for t in data['timers']) 
    actual_end = conference_start + total_duration
    
    if abs(actual_end - conference_end) <= 60:
        return data

    time_difference = conference_end - actual_end  
    adjustable_timers = [t for t in data['timers'][active_index:] if t['maxDuration'] > 300]
    
    if not adjustable_timers:
        return data
    
    total_adjustable_duration = sum(t['maxDuration'] for t in adjustable_timers)
    
    for timer in adjustable_timers:
        adjustment = (timer['maxDuration'] / total_adjustable_duration if total_adjustable_duration else 0) * time_difference
        new_duration = int(timer['maxDuration'] + adjustment)
        new_duration = min(timer['maxDuration'], max(300, new_duration))
        timer['duration'] = new_duration
    
    current_time = get_seconds(data['timers'][active_index]['start'])
    for timer in data['timers'][active_index:]:
        timer['start'] = format_time(current_time)
        current_time += timer['duration']
        timer['end'] = format_time(current_time)

    return data

@app.route("/stream")
def stream():
    def event_stream(q):
        try:
            while True:
                try: 
                    data = q.get(timeout=30)
                    yield f"data: {data}\n\n"
                except Empty:
                    yield ":\n\n" 
        finally:
            if q in clients:
                clients.remove(q)
    
    q = Queue()
    clients.append(q)
    return Response(event_stream(q), 
                    headers={"Cache-Control": "no-cache",
                             "Connection": "keep-alive",
                             "Content-Type": "text/event-stream"})

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(os.path.join(base_path, "fe"), filename)

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

def open_browser_tabs():
    port = 1914
    ip_pc = get_local_ip()
    url_admin_local = f"http://127.0.0.1:{port}/admin"
    
    print(f"\n[Browser] Lancio automatico del solo pannello Admin su: {url_admin_local}")
    print(f"[Rete Locale] Regia sul secondo schermo configurabile da remoto a: http://{ip_pc}:{port}/\n")
    
    webbrowser.open(url_admin_local)

if __name__ == "__main__":
    # FORZATURA: Al riavvio dell'eseguibile/script, resetta completamente lo stato al default di oggi
    current_meeting = get_clean_default_meeting()
    
    Timer(1.5, open_browser_tabs).start()
    app.run(host="0.0.0.0", port=1914, debug=False, threaded=True)