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

# --- CONFIGURAZIONE PERCORSI PER PYINSTALLER ---
if getattr(sys, 'frozen', False):
    # Se il programma viene eseguito come file .exe compilato
    base_path = sys._MEIPASS
else:
    # Se viene eseguito normalmente come script Python (.py)
    base_path = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=os.path.join(base_path, "fe"))
MEETING_FILE = "queue.json"  # Rimane locale nella cartella di esecuzione per salvare lo stato
clients = []


def save_meeting(data):
    with open(MEETING_FILE, "w") as f:
        json.dump(data, f)


def load_meeting():
    current_wday = time.localtime().tm_wday
    # Capiamo quale tipo di adunanza dovrebbe esserci oggi
    expected_template = "infrasettimanale_std" if current_wday < 5 else "fine_settimana_std"
    
    try:
        with open(MEETING_FILE, "r") as f:
            data = json.load(f)
            # CONTROLLO CRUCIALE: Se il file esiste ma contiene l'adunanza sbagliata per oggi, forza il reset
            if data.get("name") != expected_template:
                print(f"Rilevato cambio adunanza (attesa: {expected_template}). Rigenero...")
                return get_default_meeting()
            return data
    except Exception as e:
        print(f"Impossibile leggere {MEETING_FILE} ({e}), genero il default...")
        return get_default_meeting()
    
def get_default_meeting():
    path_templates = os.path.join(base_path, "templates.json")
    with open(path_templates, "r") as f:
        templates = json.load(f)
        
    current_wday = time.localtime().tm_wday
    
    if current_wday < 5:
        data = next(x for x in templates if x["name"] == "infrasettimanale_std")
    else:
        data = next(x for x in templates if x["name"] == "fine_settimana_std")
    
    if data["name"] == "infrasettimanale_std":
        try:
            # Chiamata allo scraper
            timers_dinamici = estrai_programma_con_titoli()
            if timers_dinamici:
                # Sincronizza l'inizio del primo timer con il conferenceStart del template
                timers_dinamici[0]['start'] = data['conferenceStart']
                
                # Iniettiamo i timer estratti
                data["timers"] = timers_dinamici
                
                # Calcola a cascata tutti i campi 'start' ed 'end' corretti
                data = refresh_meeting(data)
        except Exception as e:
            print(f"Fallback attivo. Errore automazione scraper: {e}")
            
    return data

# chiamate pagine html


@app.route("/")
def client():
    return send_from_directory(os.path.join(base_path, "fe"), "client.html")


@app.route("/admin")
def admin():
    return send_from_directory(os.path.join(base_path, "fe"), "admin.html")

# chiamate timer
@app.route("/api/templates", methods=["GET"])
def get_templates():
    path_templates = os.path.join(base_path, "templates.json")
    with open(path_templates, "r") as f:
        return jsonify(json.load(f))


@app.route("/api/meeting/start", methods=["GET"])
def get_start():
    # 1. Generiamo il meeting di default (eseguendo lo scraper se infrasettimanale)
    default_meeting = get_default_meeting()
    
    # 2. Aggiorniamo subito il file di stato corrente del server
    save_meeting(default_meeting)
    
    # 3. Mandiamo il broadcast SSE ai client connessi per aggiornare i display in tempo reale
    broadcast_message(json.dumps(default_meeting))
    
    # 4. Rispondiamo al chiamante
    return jsonify(default_meeting)

@app.route("/api/meeting", methods=["GET"])
def get_meeting():
    return jsonify(load_meeting())


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

    for timer in data['timers']:
        if 'duration' not in timer:
            timer['duration'] = timer['maxDuration']

    active_index = next((i for i, t in enumerate(data['timers']) if t['active']), None)
    
    # --- FIX CRUCIALE PER IL BOOTSTRAP/RESET ---
    # Se NON ci sono timer attivi, calcoliamo comunque la timeline iniziale 
    # partendo da 0 (il primo timer) e distribuendo gli orari linearmente.
    if active_index is None:
        current_time = conference_start
        for timer in data['timers']:
            timer['start'] = format_time(current_time)
            current_time += timer['duration']
            timer['end'] = format_time(current_time)
        return data
    # --------------------------------------------
    
    max_id = max(t['id'] for t in data['timers']) 
    for i, timer in enumerate(data['timers']):
        timer['id'] = (max_id if max_id else 0) + i + 1
    
    total_duration = sum(t['duration'] for t in data['timers']) 
    actual_end = conference_start + total_duration
    
    if abs(actual_end - conference_end) <= 60:
        return data  # Già in orario con tolleranza

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
    """Recupera dinamicamente l'IP locale del PC"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


def open_browser_tabs():
    """Apre in sequenza le schede del client e dell'admin"""
    port = 1914
    ip_pc = get_local_ip()
    
    url_client = f"http://{ip_pc}:{port}/"
    url_admin = f"http://{ip_pc}:{port}/admin"
    
    print(f"\n[Browser] Lancio automatico client: {url_client}")
    print(f"[Browser] Lancio automatico admin: {url_admin}\n")
    
    webbrowser.open(url_client)
    time.sleep(0.4)
    webbrowser.open(url_admin)


if __name__ == "__main__":
    save_meeting(get_default_meeting())
    
    # Pianifica l'apertura delle schede poco dopo l'avvio del server
    Timer(1.5, open_browser_tabs).start()
    
    # debug=False per evitare doppi avvii e doppi link aperti dal reloader di Flask
    app.run(host="0.0.0.0", port=1914, debug=False, threaded=True)