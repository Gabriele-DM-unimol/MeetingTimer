from queue import Empty, Queue
import random
from automatic_timing import estrai_programma_con_titoli
from flask import Flask, Response, request, jsonify, send_from_directory
import json
import os
import time

app = Flask(__name__, static_folder="fe")
MEETING_FILE = "queue.json"
clients = []


def save_meeting(data):
    with open(MEETING_FILE, "w") as f:
        json.dump(data, f)


def load_meeting():
    with open(MEETING_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return get_default_meeting()
    
def get_default_meeting():
    with open("templates.json", "r") as f:
        templates = json.load(f)
        
    if time.localtime().tm_wday < 5:
        data = next(x for x in templates if x["name"] == "infrasettimanale_std")
    else:
        data = next(x for x in templates if x["name"] == "fine_settimana_std")
    
    if data["name"] == "infrasettimanale_std":
        try:
            # Chiamata allo scraper
            timers_dinamici = estrai_programma_con_titoli()
            if timers_dinamici:
                # Sincronizza l'inizio del primo timer con il conferenceStart del template (19:00:00)
                timers_dinamici[0]['start'] = data['conferenceStart']
                
                # Iniettiamo i timer estratti
                data["timers"] = timers_dinamici
                
                # Calcola a cascata tutti i campi 'start' ed 'end' corretti per ogni riga
                data = refresh_meeting(data)
        except Exception as e:
            print(f"Fallback attivo. Errore automazione scraper: {e}")
            
    return data
# chiamate pagine html


@app.route("/")
def client():
    return send_from_directory("fe", "client.html")


@app.route("/admin")
def admin():
    return send_from_directory("fe", "admin.html")

# chiamate timer
@app.route("/api/templates", methods=["GET"])
def get_templates():
    with open("templates.json", "r") as f:
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
    return send_from_directory("fe", filename)


if __name__ == "__main__":
    save_meeting(get_default_meeting())
    app.run(host="0.0.0.0", port=1914, debug=True, threaded=True)