# Bluetooth Folder Synchronization

## Contexto del Problema
En la era de la conectividad, compartir y sincronizar archivos entre dispositivos es una necesidad común. Aunque existen múltiples soluciones basadas en internet, algunas situaciones requieren métodos de transferencia sin red, como Bluetooth. Este proyecto aborda el problema de sincronizar carpetas entre dos computadoras utilizando Bluetooth, permitiendo que cualquier cambio en una carpeta se refleje automáticamente en la otra.

## Solución
La solución implementa un servicio de sincronización basado en:

1. **Monitoreo de Carpetas**: Utilizando la biblioteca `watchdog`, el programa detecta en tiempo real cualquier cambio en los archivos de la carpeta seleccionada (creación, modificación o eliminación).
2. **Comunicación Bluetooth**: Se emplean sockets Bluetooth con el protocolo RFCOMM para transferir archivos y comandos entre dispositivos emparejados.
3. **Sincronización Bidireccional**: Los cambios en un dispositivo se reflejan automáticamente en el otro.
4. **Simetría**: Cada computadora actúa como cliente y servidor, permitiendo sincronización simultánea.

## Requisitos del Sistema
- Python 3.7 o superior.
- Dispositivos con Bluetooth habilitado y emparejados.
- Bibliotecas adicionales especificadas en el archivo `requirements.txt`.

## Ejecución
1. Asegúrese de que los dispositivos estén emparejados a nivel de sistema operativo.
2. En cada dispositivo, configure la dirección MAC local y del par remoto en el código.
3. Instale las dependencias desde `requirements.txt`.
4. Ejecute el programa en ambos dispositivos.
5. Especifique una carpeta para sincronizar en cada dispositivo.

Cualquier cambio en la carpeta será detectado y sincronizado automáticamente con el dispositivo remoto.

