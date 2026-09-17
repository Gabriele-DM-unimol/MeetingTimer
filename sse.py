from queue import Empty, Queue
from threading import Lock


class SseBroker:
    def __init__(self):
        self.clients = []
        self.clients_lock = Lock()

    def broadcast(self, message):
        with self.clients_lock:
            for client_queue in self.clients:
                client_queue.put(message)

    def subscribe(self):
        client_queue = Queue()
        with self.clients_lock:
            self.clients.append(client_queue)
        return client_queue

    def stream(self, client_queue):
        try:
            while True:
                try:
                    data = client_queue.get(timeout=30)
                    yield f"data: {data}\n\n"
                except Empty:
                    yield ":\n\n"
        finally:
            with self.clients_lock:
                if client_queue in self.clients:
                    self.clients.remove(client_queue)
