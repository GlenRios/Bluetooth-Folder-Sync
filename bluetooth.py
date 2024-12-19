import os
import socket
import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import hashlib
import base64

# Configuración
local_addr = "DC:F5:05:A6:3C:C0"
peer_addr = "18:CC:18:B7:0B:2D"
port = 30
sync_folder = "./sync_folder"  # Ruta de la carpeta a sincronizar

if not os.path.exists(sync_folder):
    os.makedirs(sync_folder)

def calculate_hash(file_path):
    """Calcula un hash para identificar únicamente el contenido de un archivo."""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except FileNotFoundError:
        return None

class SyncHandler(FileSystemEventHandler):
    def __init__(self, send_func):
        self.send_func = send_func

    def on_any_event(self, event):
        if event.event_type == "created" and event.is_directory:
            print(f"Detectada creación de carpeta: {event.src_path}")
            self.send_func(event.src_path, "mkdir")
        if event.event_type in ["created", "modified"] and not event.is_directory:
            file_extension = os.path.splitext(event.src_path)[1].lower()
            if file_extension in [".jpg", ".jpeg", ".png", ".gif", ".bmp"]:  # Extensiones de imagen
                print(f"Detectada imagen: {event.src_path}")
                self.send_func(event.src_path, "image")
            else:
                print(f"Detectado cambio: {event.src_path}")
                self.send_func(event.src_path, "sync")
        if event.event_type == "deleted" and not event.is_directory:
            print(f"Detectada eliminación: {event.src_path}")
            self.send_func(event.src_path, "delete")
        if event.event_type == "deleted" and event.is_directory:
            print(f"Detectada eliminación de carpeta: {event.src_path}")
            self.send_func(event.src_path, "rmdir")

    def on_moved(self, event):
        if event.is_directory:
            print(f"Detectado cambio de nombre de carpeta: {event.src_path} -> {event.dest_path}")
        else:
            print(f"Detectado cambio de nombre de archivo: {event.src_path} -> {event.dest_path}")
        self.send_func((event.src_path, event.dest_path), "rename")

def start_server(local_addr, port):
    """Servidor para recibir archivos y sincronización"""
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    sock.bind((local_addr, port))
    sock.listen(1)

    print("Servidor en ejecución...")

    while True:
        try:
            client_sock, address = sock.accept()
            data = client_sock.recv(1024).decode()
            parts = data.split("::")

            if len(parts) == 4:
                command, filepath, content, file_hash = parts
            elif len(parts) == 3:
                command, filepath, content = parts
                file_hash = None
            elif len(parts) == 2 and parts[0] == "rename":
                command, paths = parts
                src_path, dest_path = paths.split("|")
                file_path_src = os.path.join(sync_folder, src_path)
                file_path_dest = os.path.join(sync_folder, dest_path)

                if os.path.exists(file_path_src):
                    os.rename(file_path_src, file_path_dest)
                    print(f"Renombrado: {file_path_src} -> {file_path_dest}")
                else:
                    print(f"Archivo o carpeta no encontrada para renombrar: {file_path_src}")
                client_sock.close()
                continue
            else:
                print(f"Formato de mensaje inválido: {data}")
                client_sock.close()
                continue

            file_path = os.path.join(sync_folder, filepath)

            if command == "sync":
                current_hash = calculate_hash(file_path)
                if current_hash != file_hash:
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, "wb") as f:
                        f.write(content.encode())
                    print(f"Archivo sincronizado: {file_path}")
                else:
                    print(f"Archivo {file_path} ya está actualizado.")

            elif command == "delete":
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Archivo eliminado: {file_path}")
                else:
                    print(f"Archivo no encontrado para eliminar: {file_path}")

            elif command == "mkdir":
                os.makedirs(file_path, exist_ok=True)
                print(f"Carpeta creada: {file_path}")

            elif command == "rmdir":
                if os.path.exists(file_path) and os.path.isdir(file_path):
                    os.rmdir(file_path)
                    print(f"Carpeta eliminada: {file_path}")
                else:
                    print(f"Carpeta no encontrada o no vacía para eliminar: {file_path}")

            elif command == "image":
                try:
                    # Crear ruta si no existe
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)

                    # Leer tamaño de datos codificados
                    total_size = int(parts[3])
                    received_data = ""

                    # Recibir datos base64 en bloques
                    while len(received_data) < total_size:
                        chunk = client_sock.recv(4096).decode("utf-8")
                        received_data += chunk

                    # Decodificar contenido base64 a binario
                    binary_content = base64.b64decode(received_data)

                    # Escribir contenido en el archivo
                    with open(file_path, "wb") as f:
                        f.write(binary_content)

                    # Confirmar recepción
                    client_sock.send("OK".encode("utf-8"))
                    print(f"Imagen recibida y guardada correctamente: {file_path}")
                except Exception as e:
                    print(f"Error al procesar imagen: {e}")
                    client_sock.send("ERROR".encode("utf-8"))

        
            client_sock.close()
        except Exception as e:
            print(f"Error en el servidor: {e}")

def send_file(file_path, action):
    """Cliente para enviar archivos"""
    try:
        with socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM) as sock:
            sock.connect((peer_addr, port))

            if action == "rename":
                src_path, dest_path = file_path
                relative_src = os.path.relpath(src_path, sync_folder)
                relative_dest = os.path.relpath(dest_path, sync_folder)
                message = f"rename::{relative_src}|{relative_dest}"
            else:
                relative_path = os.path.relpath(file_path, sync_folder)
                if action == "sync":
                    with open(file_path, "rb") as f:
                        content = f.read().decode()
                    file_hash = calculate_hash(file_path)
                    message = f"sync::{relative_path}::{content}::{file_hash}"
                elif action == "delete":
                    message = f"delete::{relative_path}::"
                elif action == "mkdir":
                    message = f"mkdir::{relative_path}::"
                elif action == "rmdir":
                    message = f"rmdir::{relative_path}::"
                elif action == "image":
                    # Leer archivo en binario y codificar en base64
                    with open(file_path, "rb") as f:
                        binary_content = f.read()
                    base64_content = base64.b64encode(binary_content).decode("utf-8")

                    # Calcular hash y construir encabezado
                    file_hash = calculate_hash(file_path)
                    relative_path = os.path.relpath(file_path, sync_folder)
                    header = f"image::{relative_path}::{file_hash}::{len(base64_content)}".encode("utf-8")

                    # Enviar encabezado
                    sock.send(header.ljust(1024))  # Aseguramos tamaño fijo de encabezado

                    # Enviar contenido en bloques
                    chunk_size = 4096
                    for i in range(0, len(base64_content), chunk_size):
                        chunk = base64_content[i:i + chunk_size].encode("utf-8")
                        sock.send(chunk)

                    # Esperar confirmación
                    confirmation = sock.recv(1024).decode("utf-8")
                    if confirmation == "OK":
                        print(f"Imagen enviada correctamente: {file_path}")
                    else:
                        print(f"Error en la confirmación del servidor al enviar la imagen: {file_path}")
             

            sock.send(message.encode())
            print(f"Archivo enviado: {file_path} con acción {action}")
    except ConnectionResetError:
        print(f"Error: Conexión reiniciada por el servidor mientras se enviaba {file_path}")
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