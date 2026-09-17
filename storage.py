import json
import os


class JsonStore:
    def __init__(self, path, default_factory=dict):
        self.path = path
        self.default_factory = default_factory
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def load(self):
        if not os.path.exists(self.path):
            return self.default_factory()

        try:
            with open(self.path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception as error:
            print(f"[Server] Errore lettura {self.path}: {error}")
            return self.default_factory()

    def save(self, data):
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(data, file)
