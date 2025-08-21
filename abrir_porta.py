import tkinter as tk
import requests
import ssl
import urllib3
import threading
import time
from datetime import datetime

# Desabilitar avisos de SSL para desenvolvimento
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configurações
API_BASE = "http://localhost:5000"  # IP do servidor principal

class PortaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Abrir Porta - Sistema Facial")
        self.root.geometry("380x180")
        self.root.resizable(False, False)
        self.root.overrideredirect(True)  # Remove barra de título padrão
        self.center_window(380, 180)
        self.root.attributes("-topmost", True)
        try:
            self.root.iconbitmap('static/logo.ico')
        except:
            pass

        # Barra superior customizada
        self.topbar = tk.Frame(root, bg="#222", height=28)
        self.topbar.pack(fill="x", side="top")
        self.topbar.pack_propagate(False)

        self.title_label = tk.Label(self.topbar, text="Sistema Facial", bg="#222", fg="white", font=("Segoe UI", 10, "bold"))
        self.title_label.pack(side="left", padx=10)

        # Botões minimizar e fechar
        self.btn_min = tk.Button(self.topbar, text="_", bg="#222", fg="white", border=0, font=("Segoe UI", 10), command=self.minimize)
        self.btn_min.pack(side="right", padx=(0,2))
        self.btn_close = tk.Button(self.topbar, text="✕", bg="#222", fg="white", border=0, font=("Segoe UI", 10), command=self.close)
        self.btn_close.pack(side="right")

        # Permitir arrastar a janela pela barra superior
        self.topbar.bind('<Button-1>', self.start_move)
        self.topbar.bind('<B1-Motion>', self.do_move)
        self._offsetx = 0
        self._offsety = 0

        # Frame principal
        self.main = tk.Frame(root, bg="white")
        self.main.pack(fill="both", expand=True)

        # Status
        self.status_label = tk.Label(self.main, text="Verificando...", font=("Segoe UI", 14, "bold"), bg="white")
        self.status_label.pack(pady=(18,4))

        # Relógio
        self.clock_label = tk.Label(self.main, text="", font=("Segoe UI", 11), bg="white", fg="#555")
        self.clock_label.pack(pady=(0,8))

        # Botão abrir porta
        self.btn_abrir = tk.Button(self.main, text="🔓 Abrir Porta", font=("Segoe UI", 15, "bold"), bg="#4CAF50", fg="white", relief="raised", bd=2, padx=30, pady=8, command=self.abrir_porta, state="disabled")
        self.btn_abrir.pack(pady=(0,10))

        # Iniciar threads
        self.running = True
        threading.Thread(target=self.atualizar_status, daemon=True).start()
        threading.Thread(target=self.atualizar_relogio, daemon=True).start()

        # Forçar foco e levantar janela
        self.root.after(100, self.force_focus)

    def center_window(self, w, h):
        self.root.update_idletasks()
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')

    def force_focus(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def minimize(self):
        self.root.overrideredirect(False)
        self.root.iconify()
        self.root.after(200, self.restore_overrideredirect)

    def restore_overrideredirect(self):
        if self.root.state() == 'normal':
            self.root.overrideredirect(True)
        else:
            self.root.after(200, self.restore_overrideredirect)

    def close(self):
        self.running = False
        self.root.destroy()

    def start_move(self, event):
        self._offsetx = event.x
        self._offsety = event.y

    def do_move(self, event):
        x = self.root.winfo_pointerx() - self._offsetx
        y = self.root.winfo_pointery() - self._offsety
        self.root.geometry(f'+{x}+{y}')

    def atualizar_status(self):
        while self.running:
            try:
                resp = requests.get(f"{API_BASE}/api/licenca_status", timeout=2, verify=False)
                data = resp.json()
                if data.get("status") == "ok":
                    self.status_label.config(text="Sistema ONLINE", fg="#1ec700", bg="white")
                    self.btn_abrir.config(state="normal", bg="#4CAF50")
                else:
                    self.status_label.config(text="Sistema BLOQUEADO", fg="#c70000", bg="white")
                    self.btn_abrir.config(state="disabled", bg="#888")
            except Exception as e:
                self.status_label.config(text="Erro de conexão", fg="#c70000", bg="white")
                self.btn_abrir.config(state="disabled", bg="#888")
            time.sleep(1)

    def atualizar_relogio(self):
        while self.running:
            agora = datetime.now().strftime("%H:%M:%S")
            self.clock_label.config(text=f"🕒 {agora}")
            time.sleep(1)

    def abrir_porta(self):
        try:
            resp = requests.post(f"{API_BASE}/api/porta/abrir", timeout=3, verify=False)
            data = resp.json()
            if "message" in data:
                self.status_label.config(text=data["message"], fg="#1ec700")
            else:
                self.status_label.config(text=data.get("error", "Erro ao abrir porta"), fg="#c70000")
        except Exception as e:
            self.status_label.config(text="Erro de conexão", fg="#c70000")

if __name__ == "__main__":
    root = tk.Tk()
    app = PortaApp(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop() 