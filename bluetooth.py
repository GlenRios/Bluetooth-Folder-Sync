import os
import socket
import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuración
peer_addr = "DC:F5:05:A6:3C:C0"
local_addr = "18:CC:18:B7:0B:2D"
port = 30
sync_folder = "./sync_folder"  # Ruta de la carpeta a sincronizar

if not os.path.exists(sync_folder):
    os.makedirs(sync_folder)

class SyncHandler(FileSystemEventHandler):
    def __init__(self, send_func):
        self.send_func = send_func

    def on_any_event(self, event):
        if event.is_directory:
            return
        if event.event_type in ["created", "modified"]:
            print(f"Detectado cambio: {event.src_path}")
            self.send_func(event.src_path, "sync")
        elif event.event_type == "deleted":
            print(f"Detectada eliminación: {event.src_path}")
            self.send_func(event.src_path, "delete")

def start_server(local_addr, port):
    """Servidor para recibir archivos y sincronización"""
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    sock.bind((local_addr, port))
    sock.listen(1)

    print("Servidor en ejecución...")

    while True:
        client_sock, address = sock.accept()
        data = client_sock.recv(1024).decode()
        command, filepath, content = data.split("::", 2)

        if command == "sync":
            file_path = os.path.join(sync_folder, filepath)
            with open(file_path, "wb") as f:
                f.write(content.encode())
            print(f"Archivo sincronizado: {file_path}")
        elif command == "delete":
            file_path = os.path.join(sync_folder, filepath)
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Archivo eliminado: {file_path}")
        client_sock.close()

def send_file(file_path, action):
    """Cliente para enviar archivos"""
    try:
        with socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM) as sock:
            sock.connect((peer_addr, port))

            if action == "sync":
                with open(file_path, "rb") as f:
                    content = f.read().decode()
                relative_path = os.path.relpath(file_path, sync_folder)
                message = f"sync::{relative_path}::{content}"
            elif action == "delete":
                relative_path = os.path.relpath(file_path, sync_folder)
                message = f"delete::{relative_path}::"

            sock.send(message.encode())
            print(f"Archivo enviado: {file_path} con acción {action}")
    except Exception as e:
        print(f"Error al enviar archivo: {e}")

# Configurar servidor
server = threading.Thread(target=start_server, args=(local_addr, port,))
server.daemon = True
server.start()

# Configurar observador
event_handler = SyncHandler(send_file)
observer = Observer()
observer.schedule(event_handler, sync_folder, recursive=True)
observer.start()

try:
    print("Sincronización iniciada. Presione Ctrl+C para salir.")
    while True:
        time.sleep(5)
except KeyboardInterrupt:
    observer.stop()
observer.join()
