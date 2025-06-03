import tkinter as tk
from tkinter.colorchooser import askcolor
import asyncio
import websockets
import json
import threading
import queue
import websockets.exceptions

# Variables globales para WebSocket
ws_server = None
connected_clients = set()

# Cola para mensajes de dibujo
message_queue = queue.Queue()
draw_history = []  # Lista para guardar el historial de trazos

# Cola para trazos recibidos desde WebSocket para dibujar en Tkinter
incoming_draw_queue = queue.Queue()

def draw_from_ws(data):
    # Dibuja en el canvas de Tkinter desde el hilo principal
    canvas.create_line(
        data["x1"], data["y1"], data["x2"], data["y2"],
        fill=data["color"], width=data["width"], capstyle=tk.ROUND, smooth=True
    )

def process_incoming_draws():
    while not incoming_draw_queue.empty():
        data = incoming_draw_queue.get()
        draw_from_ws(data)
    root.after(20, process_incoming_draws)

async def websocket_handler(websocket, path):
    connected_clients.add(websocket)
    try:
        # Enviar historial de trazos al nuevo cliente
        for trazo in draw_history:
            await websocket.send(trazo)
        async for message in websocket:
            # Procesar mensajes entrantes
            data = json.loads(message)
            if data["type"] == "draw":
                draw_history.append(message)
                await broadcast_message(message)
                # Si el mensaje no viene de la app de Python, dibujar en Tkinter
                if not data.get("from_python"):
                    incoming_draw_queue.put(data)
            elif data["type"] == "clear":
                draw_history.clear()
                await broadcast_message(message)
                incoming_draw_queue.put({"type": "clear"})
    except websockets.exceptions.ConnectionClosedOK:
        print("[WebSocket] Cliente desconectado correctamente.")
    except Exception as e:
        print(f"[WebSocket] Error inesperado: {e}")
    finally:
        connected_clients.remove(websocket)

async def start_websocket_server():
    global ws_server
    ws_server = await websockets.serve(websocket_handler, "0.0.0.0", 8765)
    print("Servidor WebSocket iniciado en ws://0.0.0.0:8765")
    while True:
        if not message_queue.empty() and connected_clients:
            message = message_queue.get()
            await broadcast_message(message)
        await asyncio.sleep(0.01)

def start_websocket_server_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_websocket_server())

def send_drawing_data(x1, y1, x2, y2, color, width):
    data = {
        "type": "draw",
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "color": color,
        "width": width,
        "from_python": True  # Marca que el trazo viene de la app de Python
    }
    json_data = json.dumps(data)
    draw_history.append(json_data)
    message_queue.put(json_data)

async def broadcast_message(message):
    if connected_clients:
        await asyncio.gather(
            *[client.send(message) for client in connected_clients]
        )

def start_drawing(event):
    global is_drawing, prev_x, prev_y
    is_drawing = True
    prev_x, prev_y = event.x, event.y

def draw(event):
    global is_drawing, prev_x, prev_y, drawing_color
    if is_drawing:
        current_x, current_y = event.x, event.y
        color_to_use = drawing_color
        # Si el color es rojo, cambiar a naranja
        if color_to_use.lower() == "red" or color_to_use == "#ff0000":
            color_to_use = "orange"
        canvas.create_line(prev_x, prev_y, current_x, current_y, fill=color_to_use, width=line_width, capstyle=tk.ROUND, smooth=True)
        # Enviar datos a través de WebSocket
        send_drawing_data(prev_x, prev_y, current_x, current_y, color_to_use, line_width)
        prev_x, prev_y = current_x, current_y

def stop_drawing(event):
    global is_drawing
    is_drawing = False

def change_pen_color():
    global drawing_color
    color = askcolor()[1]
    if color:
        drawing_color = color

def change_line_width(value):
    global line_width
    line_width = int(value)

def clear_canvas():
    canvas.delete("all")
    # Enviar mensaje de limpiar a los clientes
    data = {"type": "clear", "from_python": True}
    message_queue.put(json.dumps(data))
    draw_history.clear()

eraser_mode = False
prev_color = None
prev_width = None

status_label = None

def toggle_eraser():
    global eraser_mode, drawing_color, line_width, prev_color, prev_width
    if not eraser_mode:
        eraser_mode = True
        prev_color = drawing_color
        prev_width = line_width
        drawing_color = "white"
        line_width = 20
        eraser_button.config(bg="orange", text="Borrador (Activo)")
        if status_label:
            status_label.config(text="Modo borrador ACTIVADO", fg="orange")
    else:
        eraser_mode = False
        drawing_color = prev_color if prev_color else "black"
        line_width = prev_width if prev_width else 2
        eraser_button.config(bg=root.cget('bg'), text="Borrador")
        if status_label:
            status_label.config(text="Modo borrador desactivado", fg="black")

if __name__ == "__main__":
    # Iniciar servidor WebSocket en un hilo separado
    websocket_thread = threading.Thread(target=start_websocket_server_thread, daemon=True)
    websocket_thread.start()

    root = tk.Tk()
    root.title("Whiteboard")
    # Configurar pantalla completa
    root.attributes('-fullscreen', True)
    # Agregar tecla de escape para salir de pantalla completa
    root.bind('<Escape>', lambda e: root.attributes('-fullscreen', False))
    canvas = tk.Canvas(root, bg="white")
    canvas.pack(fill="both", expand=True)

    is_drawing = False
    drawing_color = "black"
    line_width = 2

    root.geometry("800x600")
    controls_frame = tk.Frame(root)
    controls_frame.pack(side="top", fill="x")
    color_button = tk.Button(controls_frame, text="Cambiar Color", command=change_pen_color)
    clear_button = tk.Button(controls_frame, text="Limpiar Canvas", command=clear_canvas)
    eraser_button = tk.Button(controls_frame, text="Borrador", command=toggle_eraser)

    color_button.pack(side="left", padx=5, pady=5)
    clear_button.pack(side="left", padx=5, pady=5)
    eraser_button.pack(side="left", padx=5, pady=5)

    line_width_label = tk.Label(controls_frame, text="Ancho de Linea:")
    line_width_label.pack(side="left", padx=5, pady=5)

    line_width_slider = tk.Scale(controls_frame, from_=1, to=10, orient="horizontal", command=lambda val: change_line_width(val))
    line_width_slider.set(line_width)
    line_width_slider.pack(side="left", padx=5, pady=5)
    
    canvas.bind("<Button-1>", start_drawing)
    canvas.bind("<B1-Motion>", draw)
    canvas.bind("<ButtonRelease-1>", stop_drawing)

    status_label = tk.Label(root, text="Modo borrador desactivado", anchor="w")
    status_label.pack(side="bottom", fill="x")

    # Iniciar el procesamiento de trazos entrantes
    root.after(20, process_incoming_draws)

    root.mainloop()