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
        if not time_str: return 0
        h, m, s = map(int, time_str.split(':'))
        return h * 3600 + m * 60 + s
    
    def format_time(seconds):
        h, m, s = int(seconds // 3600), int((seconds % 3600) // 60), int(seconds % 60)
        return f"{h:02}:{m:02}:{s:02}"
        
    conference_start = get_seconds(data['timers'][0]['start'])
    
    # Il limite massimo invalicabile: Inizio Effettivo + 105 minuti (6300 secondi)
    MAX_TOTAL_DURATION = 105 * 60 
    max_conference_end = conference_start + MAX_TOTAL_DURATION

    active_index = next((i for i, t in enumerate(data['timers']) if t['active']), None)
    
    # Se nessun timer è attivo, timeline lineare standard
    if active_index is None:
        current_time = conference_start
        for timer in data['timers']:
            timer['start'] = format_time(current_time)
            current_time += timer.get('duration', timer.get('maxDuration', 60))
            timer['end'] = format_time(current_time)
        return data
    
    # 1. Congeliamo i timer passati con la loro durata REALE consumata
    current_time = conference_start
    for i in range(active_index):
        t = data['timers'][i]
        t['start'] = format_time(current_time)
        current_time += t['duration']
        t['end'] = format_time(current_time)

    # 2. Impostiamo lo start del timer attivo corrente
    data['timers'][active_index]['start'] = format_time(current_time)
    
    # Calcoliamo il tempo che rimarrebbe alla fine della parte attiva corrente
    time_after_active = current_time + data['timers'][active_index]['duration']
    
    # 3. COMPENSAZIONE PROPORZIONALE: Scatta solo sulle parti STRETTAMENTE FUTURE
    future_index = active_index + 1
    if future_index < len(data['timers']):
        # Quanto tempo teorico ci rimarrebbe prima di sforare i 105 minuti?
        remaining_budget = max_conference_end - time_after_active
        
        # Somma delle maxDuration di tutti i timer futuri configurati
        total_future_max_duration = sum(t['maxDuration'] for t in data['timers'][future_index:])
        
        # Se stiamo sforando il budget totale (o se il tempo rimasto differisce dal nominale richiesto)
        if remaining_budget < total_future_max_duration:
            # Identifichiamo solo i timer futuri che durano più di 5 minuti (300 secondi)
            adjustable_timers = [t for t in data['timers'][future_index:] if t['maxDuration'] > 300]
            
            if adjustable_timers:
                # Calcoliamo quanta durata nominale totale hanno i timer sacrificabili
                total_adjustable_max = sum(t['maxDuration'] for t in adjustable_timers)
                # Durata totale dei timer che NON possiamo toccare (quelli già sotto i 5 minuti)
                non_adjustable_max = total_future_max_duration - total_adjustable_max
                
                # Il budget effettivo da spartire tra i timer modificabili
                budget_for_adjustable = remaining_budget - non_adjustable_max
                
                # Distribuzione proporzionale del budget rimasto
                for timer in adjustable_timers:
                    if total_adjustable_max > 0:
                        # Quota proporzionale basata sul peso del timer rispetto agli altri modificabili
                        proportion = timer['maxDuration'] / total_adjustable_max
                        nuova_durata = int(budget_for_adjustable * proportion)
                        
                        # Garantiamo comunque un minimo invalicabile di 300 secondi (5 min) come da specifica
                        timer['duration'] = max(300, nuova_durata)
            else:
                # Se non ci sono timer > 300s da sacrificare, mantengono la maxDuration
                for t in data['timers'][future_index:]:
                    t['duration'] = t['maxDuration']
        else:
            # Se siamo larghi coi tempi e non stiamo sforando i 105 minuti, i futuri tornano/restano standard
            for t in data['timers'][future_index:]:
                t['duration'] = t['maxDuration']
    
    # 4. Rigeneriamo i timestamp grafici di start/end per la parte attiva e future
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