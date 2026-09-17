import json
import socket
import webbrowser
from threading import Timer

from flask import Flask, Response, jsonify, request, send_from_directory

from meeting_service import MeetingService
from paths import FE_PATH, MEETING_FILE, TEMPLATE_STATE_FILE, TEMPLATES_FILE
from sse import SseBroker
from storage import JsonStore
from templates_service import TemplateService


PORT = 1914


def create_app():
    app = Flask(__name__, static_folder=FE_PATH, static_url_path="")
    sse_broker = SseBroker()
    template_service = TemplateService(
        templates_file=TEMPLATES_FILE,
        template_state_store=JsonStore(TEMPLATE_STATE_FILE),
    )
    meeting_service = MeetingService(
        meeting_store=JsonStore(MEETING_FILE),
        template_service=template_service,
    )

    @app.route("/")
    def client():
        return send_from_directory(FE_PATH, "client.html")

    @app.route("/admin")
    def admin():
        return send_from_directory(FE_PATH, "admin.html")

    @app.route("/api/templates", methods=["GET"])
    def get_templates():
        return jsonify(template_service.build_catalog())

    @app.route("/api/meeting/start", methods=["GET"])
    def get_start():
        print("[Server] Richiesta cambio template / reset: eseguo il refresh totale...")
        meeting = meeting_service.reset_to_default()
        sse_broker.broadcast(json.dumps(meeting))
        return jsonify(meeting)

    @app.route("/api/meeting", methods=["GET"])
    def get_meeting():
        response = jsonify(meeting_service.load_current())
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.route("/api/meeting", methods=["POST"])
    def post_meeting():
        meeting = request.get_json()
        refreshed = meeting_service.save(meeting)
        sse_broker.broadcast(json.dumps(refreshed))
        return jsonify(refreshed)

    @app.route("/stream")
    def stream():
        client_queue = sse_broker.subscribe()
        return Response(
            sse_broker.stream(client_queue),
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            },
        )

    @app.route("/api/network-info", methods=["GET"])
    def network_info():
        return jsonify({"ip": get_local_ip(), "port": PORT})

    @app.route("/<path:filename>")
    def static_files(filename):
        return send_from_directory(FE_PATH, filename)

    app.meeting_service = meeting_service
    return app


def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.connect(("8.8.8.8", 80))
            return udp_socket.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def open_browser_tabs():
    admin_url = f"http://127.0.0.1:{PORT}/admin"
    local_network_url = f"http://{get_local_ip()}:{PORT}/"

    print(f"\n[Browser] Lancio automatico del solo pannello Admin su: {admin_url}")
    print(f"[Rete Locale] Regia sul secondo schermo configurabile da remoto a: {local_network_url}\n")

    webbrowser.open(admin_url)


app = create_app()


if __name__ == "__main__":
    app.meeting_service.reset_to_default()
    Timer(1.5, open_browser_tabs).start()
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
