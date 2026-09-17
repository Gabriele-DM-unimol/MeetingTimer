import os
import sys


APP_NAME = "TimerSincronizzato"


def get_base_path():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def get_appdata_dir():
    if os.name == "nt":
        root = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(root, APP_NAME)
    return os.path.expanduser("~/.timersincronizzato")


BASE_PATH = get_base_path()
FE_PATH = os.path.join(BASE_PATH, "fe")
APPDATA_DIR = get_appdata_dir()
MEETING_FILE = os.path.join(APPDATA_DIR, "queue.json")
TEMPLATE_STATE_FILE = os.path.join(APPDATA_DIR, "templates_state.json")
TEMPLATES_FILE = os.path.join(BASE_PATH, "templates.json")
