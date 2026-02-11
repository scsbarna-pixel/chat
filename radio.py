import customtkinter as ctk
import keyboard
import threading
import os
import json
import time
import random

# INTENTO DE IMPORTAR VLC
try:
    import vlc
except ImportError:
    print("¡ALERTA! Necesitas instalar vlc: pip install python-vlc")

# --- CONFIGURACIÓN ---
DEFAULT_CONFIG = {
    "rutas": {
        "musica": "C:/RADIO_SISTEMA/MUSICA",
        "programas": "C:/RADIO_SISTEMA/PROGRAMAS",
        "botonera": "C:/RADIO_SISTEMA/BOTONERA"
    },
    "extensiones_validas": [".mp3", ".wav", ".mp2", ".ogg"]
}

class RadioAutomationApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # 1. CARGA DE CONFIGURACIÓN Y MOTORES
        self.config = self.load_config()
        self.init_audio_engines()
        
        # Estado
        self.playlist_musica = []
        self.current_song_index = 0
        self.is_auto_mode = True
        self.current_page_index = 0
        self.botonera_pages = []
        self.page_files = []

        # --- DISEÑO VISUAL V6 (3 NIVELES) ---
        ctk.set_appearance_mode("Light") 
        ctk.set_default_color_theme("blue")
        self.title("RADIO AUTOMATION - ESTRUCTURA FINAL")
        self.geometry("1280x900") # Un poco más alto para que quepa todo
        
        # MENÚ SUPERIOR (Visual)
        self.menu_bar = ctk.CTkFrame(self, height=25, fg_color="#cccccc", corner_radius=0)
        self.menu_bar.pack(side="top", fill="x")
        ctk.CTkLabel(self.menu_bar, text="ARCHIVO   HERRAMIENTAS   VER   AYUDA", text_color="black", anchor="w").pack(side="left", padx=10)

        # GRID PRINCIPAL (3 FILAS)
        self.main_container = ctk.CTkFrame(self, fg_color="#e0e0e0")
        self.main_container.pack(fill="both", expand=True)
        
        self.main_container.grid_rowconfigure(0, weight=2) # Nivel Superior (Máster)
        self.main_container.grid_rowconfigure(1, weight=2) # Nivel Medio (Players)
        self.main_container.grid_rowconfigure(2, weight=3) # Nivel Inferior (Listas)
        self.main_container.grid_columnconfigure(0, weight=1)

        # ==================================================
        # NIVEL 1: MÁSTER / AIRE (LO QUE SUENA)
        # ==================================================
        self.master_frame = ctk.CTkFrame(self.main_container, fg_color="#d9d9d9", border_width=1, border_color="gray")
        self.master_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        
        self.master_frame.grid_columnconfigure(0, weight=4) # Info Actual
        self.master_frame.grid_columnconfigure(1, weight=1) # Faders
        self.master_frame.grid_columnconfigure(2, weight=4) # Next / CUE

        # --- [1.A] AIRE IZQUIERDA (Canción + VU + Proceso) ---
        self.air_info_frame = ctk.CTkFrame(self.master_frame, fg_color="white")
        self.air_info_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        ctk.CTkLabel(self.air_info_frame, text="EN EL AIRE", font=("Arial", 10, "bold"), text_color="red").pack(anchor="w", padx=10, pady=(5,0))
        
        # Título Gigante
        self.lbl_master_track = ctk.CTkLabel(self.air_info_frame, text="ESPERANDO AUDIO...", font=("Arial", 24, "bold"), text_color="#1f538d")
        self.lbl_master_track.pack(pady=10)
        
        # Vúmetro General (Simulado)
        ctk.CTkLabel(self.air_info_frame, text="VU MASTER", font=("Arial", 8)).pack(anchor="w", padx=10)
        self.vu_master_l = ctk.CTkProgressBar(self.air_info_frame, height=12, progress_color="#00cc00")
        self.vu_master_l.pack(fill="x", padx=10, pady=2)
        self.vu_master_r = ctk.CTkProgressBar(self.air_info_frame, height=12, progress_color="#00cc00")
        self.vu_master_r.pack(fill="x", padx=10, pady=2)
        
        # Barra de Proceso
        ctk.CTkLabel(self.air_info_frame, text="PROCESO", font=("Arial", 8)).pack(anchor="w", padx=10, pady=(5,0))
        self.master_progress = ctk.CTkProgressBar(self.air_info_frame, height=20, progress_color="blue")
        self.master_progress.pack(fill="x", padx=10, pady=5)


        # --- [1.B] COLUMNA CENTRAL (FADERS) ---
        self.fader_frame = ctk.CTkFrame(self.master_frame, fg_color="#cccccc")
        self.fader_frame.grid(row=0, column=1, sticky="ns", padx=2, pady=5)
        
        # Vol
        self.vol_slider = ctk.CTkSlider(self.fader_frame, from_=0, to=100, orientation="vertical", height=120, width=20)
        self.vol_slider.pack(side="left", padx=10, pady=10)
        self.vol_slider.set(100)
        
        # Pitch
        self.pitch_slider = ctk.CTkSlider(self.fader_frame, from_=0, to=100, orientation="vertical", height=120, width=20, button_color="gray")
        self.pitch_slider.pack(side="right", padx=10, pady=10)
        self.pitch_slider.set(50)
        
        ctk.CTkLabel(self.fader_frame, text="VOL   PITCH", font=("Arial", 8)).pack(side="bottom", pady=5)


        # --- [1.C] AIRE DERECHA (PRÓXIMA + CUE) ---
        self.next_info_frame = ctk.CTkFrame(self.master_frame, fg_color="white")
        self.next_info_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        
        ctk.CTkLabel(self.next_info_frame, text="PRÓXIMA CANCIÓN", font=("Arial", 10, "bold"), text_color="gray").pack(anchor="w", padx=10, pady=(5,0))
        
        self.lbl_next_track = ctk.CTkLabel(self.next_info_frame, text="---", font=("Arial", 18), text_color="black")
        self.lbl_next_track.pack(pady=20)
        
        # Botón CUE Gigante
        self.btn_cue = ctk.CTkButton(self.next_info_frame, text="🎧 CUE / PRE-ESCUCHA", height=40, fg_color="orange", text_color="black", font=("Arial", 12, "bold"))
        self.btn_cue.pack(pady=10, padx=20, fill="x")


        # ==================================================
        # NIVEL 2: REPRODUCTORES MANUALES (PLAYERS 1 & 2)
        # ==================================================
        self.decks_frame = ctk.CTkFrame(self.main_container, fg_color="#e0e0e0")
        self.decks_frame.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        self.decks_frame.grid_columnconfigure(0, weight=1)
        self.decks_frame.grid_columnconfigure(1, weight=1)

        # PLAYER 1 (Abajo Izquierda)
        self.p1_frame = ctk.CTkFrame(self.decks_frame, fg_color="white", border_width=2, border_color="black")
        self.p1_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        ctk.CTkLabel(self.p1_frame, text="PLAYER 1 (MANUAL)", font=("Arial", 12, "bold")).pack(pady=2)
        self.lbl_p1_status = ctk.CTkLabel(self.p1_frame, text="LISTO", text_color="gray")
        self.lbl_p1_status.pack()
        
        # Controles P1
        self.p1_ctrl = ctk.CTkFrame(self.p1_frame, fg_color="transparent")
        self.p1_ctrl.pack(pady=10)
        ctk.CTkButton(self.p1_ctrl, text="▶", width=30, command=self.play_p1_next).pack(side="left", padx=2)
        ctk.CTkButton(self.p1_ctrl, text="⏹", width=30, fg_color="red", command=self.stop_p1).pack(side="left", padx=2)
        ctk.CTkButton(self.p1_ctrl, text="📂", width=30, fg_color="gray").pack(side="left", padx=2)


        # PLAYER 2 (Abajo Derecha)
        self.p2_frame = ctk.CTkFrame(self.decks_frame, fg_color="white", border_width=2, border_color="black")
        self.p2_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        ctk.CTkLabel(self.p2_frame, text="PLAYER 2 (MANUAL)", font=("Arial", 12, "bold")).pack(pady=2)
        self.lbl_p2_status = ctk.CTkLabel(self.p2_frame, text="LISTO", text_color="gray")
        self.lbl_p2_status.pack()
        
        # Controles P2
        self.p2_ctrl = ctk.CTkFrame(self.p2_frame, fg_color="transparent")
        self.p2_ctrl.pack(pady=10)
        ctk.CTkButton(self.p2_ctrl, text="▶", width=30, command=self.play_p2_aux).pack(side="left", padx=2)
        ctk.CTkButton(self.p2_ctrl, text="⏹", width=30, fg_color="red", command=self.stop_p2).pack(side="left", padx=2)
        ctk.CTkButton(self.p2_ctrl, text="📂", width=30, fg_color="gray").pack(side="left", padx=2)


        # ==================================================
        # NIVEL 3: EVENTOS Y BOTONERA
        # ==================================================
        self.lists_frame = ctk.CTkFrame(self.main_container, fg_color="#e0e0e0")
        self.lists_frame.grid(row=2, column=0, sticky="nsew", padx=2, pady=2)
        self.lists_frame.grid_columnconfigure(0, weight=1)
        self.lists_frame.grid_columnconfigure(1, weight=1)

        # EVENTOS
        self.events_box = ctk.CTkFrame(self.lists_frame, fg_color="white", border_width=1, border_color="gray")
        self.events_box.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        ctk.CTkLabel(self.events_box, text="EVENTOS PROGRAMADOS", font=("Arial", 11, "bold")).pack(pady=2)
        self.txt_events = ctk.CTkTextbox(self.events_box, font=("Courier", 12))
        self.txt_events.pack(fill="both", expand=True, padx=2, pady=2)
        self.txt_events.insert("0.0", "HORA     | TIPO   | NOMBRE\n" + "-"*35 + "\n09:00:00 | MIX    | SEÑALES\n")

        # BOTONERA
        self.keys_box = ctk.CTkFrame(self.lists_frame, fg_color="white", border_width=1, border_color="gray")
        self.keys_box.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.lbl_page_title = ctk.CTkLabel(self.keys_box, text="TECLAS RÁPIDAS - PÁGINA 1", font=("Arial", 11, "bold"))
        self.lbl_page_title.pack(pady=2)
        
        self.buttons_grid = ctk.CTkFrame(self.keys_box, fg_color="transparent")
        self.buttons_grid.pack(fill="both", expand=True)
        
        self.btn_objects = []
        for i in range(9):
            btn = ctk.CTkButton(self.buttons_grid, text=f"{i+1}", height=30, fg_color="#333333",
                                command=lambda x=i: self.play_botonera(x))
            btn.grid(row=i//3, column=i%3, padx=2, pady=2, sticky="nsew")
            self.btn_objects.append(btn)
        self.buttons_grid.grid_columnconfigure((0,1,2), weight=1)
        self.buttons_grid.grid_rowconfigure((0,1,2), weight=1)


        # 2. CARGAR Y ARRANCAR
        self.load_music_library()
        self.scan_botonera_folders()
        self.update_botonera_display()
        self.start_keyboard_listener()
        self.update_timers()

    # --- MOTORES VLC ---
    def init_audio_engines(self):
        self.vlc_instance = vlc.Instance()
        self.player_main = self.vlc_instance.media_player_new() # Master
        self.player_aux = self.vlc_instance.media_player_new()  # P2
        self.player_fx = self.vlc_instance.media_player_new()   # Botones
        self.events_manager = self.player_main.event_manager()
        self.events_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self.on_song_finished)

    def load_config(self):
        if not os.path.exists("config.json"):
            with open("config.json", "w") as f: json.dump(DEFAULT_CONFIG, f)
            return DEFAULT_CONFIG
        with open("config.json", "r") as f: return json.load(f)

    # --- FUNCIONES LÓGICAS ---
    def load_music_library(self):
        path = self.config["rutas"]["musica"]
        valid = tuple(self.config["extensiones_validas"])
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.lower().endswith(valid):
                        self.playlist_musica.append(os.path.join(root, file))
            random.shuffle(self.playlist_musica)
        self.update_next_display()

    def play_p1_next(self):
        # Reproduce en el MASTER (Arriba)
        if not self.playlist_musica: return
        song_path = self.playlist_musica[self.current_song_index]
        media = self.vlc_instance.media_new(song_path)
        self.player_main.set_media(media)
        self.player_main.play()
        
        self.lbl_master_track.configure(text=os.path.basename(song_path)[:30])
        self.current_song_index = (self.current_song_index + 1) % len(self.playlist_musica)
        self.update_next_display()

    def pause_p1(self): self.player_main.pause()
    
    def stop_p1(self):
        self.player_main.stop()
        self.lbl_master_track.configure(text="STOP")
        self.master_progress.set(0)
        self.vu_master_l.set(0)
        self.vu_master_r.set(0)

    def on_song_finished(self, event):
        if self.is_auto_mode: self.after(100, self.play_p1_next)

    def update_next_display(self):
        if self.playlist_musica:
            next_song = self.playlist_musica[self.current_song_index]
            self.lbl_next_track.configure(text=os.path.basename(next_song)[:20])

    def play_p2_aux(self):
        # Por ahora usa la lógica del auxiliar
        if self.playlist_musica:
            song_path = self.playlist_musica[self.current_song_index]
            media = self.vlc_instance.media_new(song_path)
            self.player_aux.set_media(media)
            self.player_aux.play()

    def stop_p2(self): self.player_aux.stop()

    def scan_botonera_folders(self):
        path = self.config["rutas"]["botonera"]
        if os.path.exists(path):
            self.botonera_pages = [f.name for f in os.scandir(path) if f.is_dir()]
            self.botonera_pages.sort()
        if not self.botonera_pages: self.botonera_pages = ["VACIO"]

    def update_botonera_display(self):
        current = self.botonera_pages[self.current_page_index]
        self.lbl_page_title.configure(text=f"PANTALLA {self.current_page_index+1} - {current.upper()}")
        folder = os.path.join(self.config["rutas"]["botonera"], current)
        valid = tuple(self.config["extensiones_validas"])
        if os.path.exists(folder):
            files = [f.name for f in os.scandir(folder) if f.name.lower().endswith(valid)]
            files.sort()
            self.page_files = files
        else: self.page_files = []

        for i, btn in enumerate(self.btn_objects):
            if i < len(self.page_files):
                name = os.path.splitext(self.page_files[i])[0]
                btn.configure(text=f"{i+1}. {name[:12]}", fg_color="#1f538d", state="normal")
            else: btn.configure(text="---", fg_color="#333333", state="disabled")

    def play_botonera(self, index):
        if index < len(self.page_files):
            file = self.page_files[index]
            folder = self.botonera_pages[self.current_page_index]
            path = os.path.join(self.config["rutas"]["botonera"], folder, file).replace("\\", "/")
            self.player_fx.stop()
            media = self.vlc_instance.media_new(path)
            self.player_fx.set_media(media)
            self.player_fx.play()

    def toggle_page(self):
        self.current_page_index = (self.current_page_index + 1) % len(self.botonera_pages)
        self.update_botonera_display()

    def start_keyboard_listener(self):
        def loop():
            keyboard.add_hotkey('7', lambda: self.after(0, self.play_p1_next))
            keyboard.add_hotkey('8', lambda: self.after(0, self.stop_p1))
            keyboard.add_hotkey('9', lambda: self.after(0, self.play_p2_aux))
            keyboard.add_hotkey('+', lambda: self.after(0, self.stop_p2))
            keyboard.add_hotkey('divide', lambda: self.after(0, lambda: self.player_main.audio_set_volume(30)))
            for i in range(1, 10): keyboard.add_hotkey(str(i), lambda x=i-1: self.after(0, lambda: self.play_botonera(x)))
            keyboard.add_hotkey('0', lambda: self.after(0, self.toggle_page))
        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def update_timers(self):
        if self.player_main.is_playing():
            length = self.player_main.get_length()
            current = self.player_main.get_time()
            if length > 0: self.master_progress.set(current / length)
            self.vu_master_l.set(random.uniform(0.3, 0.9)) # VU Simulado
            self.vu_master_r.set(random.uniform(0.3, 0.9))
        else:
            self.vu_master_l.set(0)
            self.vu_master_r.set(0)
        self.after(100, self.update_timers)

if __name__ == "__main__":
    app = RadioAutomationApp()
    app.mainloop()