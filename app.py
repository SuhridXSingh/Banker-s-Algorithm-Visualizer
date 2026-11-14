"""
Banker's Algorithm Visualizer — Desktop GUI
============================================
Modern dark-themed Python desktop application for step-by-step visualization
of the Banker's Algorithm (Deadlock Avoidance).

Run:  python app.py
Dependencies: None (built-in tkinter only)
"""

import tkinter as tk
from tkinter import ttk, messagebox
import banker_engine as engine
from banker_engine import BankerState, StepSnapshot

# ═══════════════════════════════════════════════════════════════════════════════
#  THEME — Dark mode color palette
# ═══════════════════════════════════════════════════════════════════════════════

C = {
    "bg":           "#1a1a2e",    # deepest background
    "panel":        "#16213e",    # panel/section background
    "card":         "#0f3460",    # card background
    "input_bg":     "#1e293b",    # entry cell background
    "border":       "#334155",    # subtle borders
    "primary":      "#3b82f6",    # royal blue accent
    "primary_h":    "#2563eb",    # hover
    "success":      "#10b981",    # green
    "success_d":    "#064e3b",    # dark green bg
    "warning":      "#f59e0b",    # amber
    "warning_d":    "#78350f",    # dark amber bg
    "danger":       "#ef4444",    # red
    "danger_d":     "#7f1d1d",    # dark red bg
    "text":         "#f8fafc",    # primary text
    "text_dim":     "#94a3b8",    # secondary text
    "header":       "#4338ca",    # table header indigo
    "white":        "#ffffff",
    "wait_bg":      "#334155",
    "wait_bd":      "#475569",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🏦 Banker's Algorithm Visualizer")
        self.configure(bg=C["bg"])
        self.geometry("1340x820")
        self.minsize(1100, 700)

        # ── State ──
        self.banker_state = None       # current BankerState
        self.steps = []                # list[StepSnapshot] from last run
        self.current_step_idx = -1
        self.playing = False
        self.play_speed_ms = 800
        self._after_id = None

        # ── Widget references ──
        self.alloc_entries = []         # 2-D list of tk.Entry
        self.max_entries = []           # 2-D list of tk.Entry
        self.need_labels = []           # 2-D list of tk.Label
        self.total_entries = []         # list of tk.Entry
        self.avail_labels = []          # list of tk.Label
        self.proc_name_entries = []     # list of tk.Entry (one per process)
        self.res_name_entries = []      # list of tk.Entry (one per resource)
        self.process_cards = []         # list of dict {frame, name_lbl, status_lbl, icon_lbl}
        self.sequence_labels = []       # list of tk.Label

        # ── Build UI ──
        self._setup_styles()
        self._build_ui()
        self._load_preset("📚 Classic Textbook")

        # ── Keyboard shortcuts ──
        self.bind("<space>", lambda e: self._play_pause())
        self.bind("<Right>", lambda e: self._step_forward())
        self.bind("<Left>", lambda e: self._step_backward())
        self.bind("r", lambda e: self._reset_stepper())
        self.bind("R", lambda e: self._reset_stepper())

    # ───────────────────────────────────────────────────────────────────────────
    #  STYLES
    # ───────────────────────────────────────────────────────────────────────────

    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("clam")

        # Frames
        s.configure("Dark.TFrame", background=C["bg"])
        s.configure("Panel.TFrame", background=C["panel"])
        s.configure("Card.TFrame", background=C["card"])

        # Labels
        for name, bg, fg, font in [
            ("Title.TLabel",    C["bg"],    C["text"],     ("Segoe UI", 16, "bold")),
            ("Panel.TLabel",    C["panel"], C["text"],     ("Segoe UI", 10)),
            ("PanelBold.TLabel",C["panel"], C["text"],     ("Segoe UI", 10, "bold")),
            ("Dim.TLabel",      C["panel"], C["text_dim"], ("Segoe UI", 9)),
            ("SectionH.TLabel", C["panel"], C["warning"],  ("Segoe UI", 11, "bold")),
            ("Dark.TLabel",     C["bg"],    C["text"],     ("Segoe UI", 10)),
            ("Card.TLabel",     C["card"],  C["text"],     ("Segoe UI", 10)),
            ("CardBold.TLabel", C["card"],  C["text"],     ("Segoe UI", 10, "bold")),
        ]:
            s.configure(name, background=bg, foreground=fg, font=font)

        # Buttons
        for name, bg, bg_active in [
            ("Run.TButton",     C["success"],  "#059669"),
            ("Primary.TButton", C["primary"],  C["primary_h"]),
            ("Danger.TButton",  C["danger"],   "#dc2626"),
            ("Ctrl.TButton",    C["card"],     C["primary"]),
        ]:
            s.configure(name, background=bg, foreground=C["text"],
                        font=("Segoe UI", 10, "bold"), padding=(10, 5))
            s.map(name, background=[("active", bg_active), ("disabled", C["border"])])

        # Scales
        s.configure("Speed.Horizontal.TScale",
                    background=C["panel"], troughcolor=C["input_bg"])

    # ───────────────────────────────────────────────────────────────────────────
    #  MAIN LAYOUT
    # ───────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = ttk.Frame(self, style="Dark.TFrame")
        root.pack(fill="both", expand=True, padx=6, pady=6)

        # Title bar
        ttk.Label(root, text="🏦  Banker's Algorithm Visualizer",
                  style="Title.TLabel").pack(anchor="w", pady=(0, 6))

        # Config bar
        self._build_config_bar(root)

        # Content: left = matrices, right = visualizer
        self.content = ttk.PanedWindow(root, orient="horizontal")
        self.content.pack(fill="both", expand=True, pady=(6, 0))

        # Left panel (matrices) — inside a canvas for scrolling
        left_outer = ttk.Frame(self.content, style="Panel.TFrame")
        self.content.add(left_outer, weight=55)

        self.left_canvas = tk.Canvas(left_outer, bg=C["panel"],
                                     highlightthickness=0, bd=0)
        left_sb = ttk.Scrollbar(left_outer, orient="vertical",
                                command=self.left_canvas.yview)
        self.left_canvas.configure(yscrollcommand=left_sb.set)
        left_sb.pack(side="right", fill="y")
        self.left_canvas.pack(side="left", fill="both", expand=True)

        self.matrix_frame = ttk.Frame(self.left_canvas, style="Panel.TFrame")
        self._canvas_win = self.left_canvas.create_window(
            (0, 0), window=self.matrix_frame, anchor="nw")
        self.matrix_frame.bind("<Configure>", self._on_matrix_configure)
        self.left_canvas.bind("<Configure>", self._on_canvas_resize)

        # Mousewheel scroll
        self.left_canvas.bind("<Enter>",
            lambda e: self.left_canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.left_canvas.bind("<Leave>",
            lambda e: self.left_canvas.unbind_all("<MouseWheel>"))

        # Right panel (visualizer)
        self.viz_frame = ttk.Frame(self.content, style="Panel.TFrame")
        self.content.add(self.viz_frame, weight=45)
        self._build_visualizer_panel()

    def _on_matrix_configure(self, e):
        self.left_canvas.configure(scrollregion=self.left_canvas.bbox("all"))

    def _on_canvas_resize(self, e):
        self.left_canvas.itemconfig(self._canvas_win, width=e.width)

    def _on_mousewheel(self, e):
        self.left_canvas.yview_scroll(-int(e.delta / 120), "units")

    # ───────────────────────────────────────────────────────────────────────────
    #  CONFIG BAR
    # ───────────────────────────────────────────────────────────────────────────

    def _build_config_bar(self, parent):
        bar = ttk.Frame(parent, style="Panel.TFrame")
        bar.pack(fill="x")
        inner = ttk.Frame(bar, style="Panel.TFrame")
        inner.pack(fill="x", padx=10, pady=7)

        # Processes
        ttk.Label(inner, text="Processes:", style="Panel.TLabel").pack(side="left")
        self.n_proc_var = tk.IntVar(value=5)
        tk.Spinbox(inner, from_=1, to=15, width=3, textvariable=self.n_proc_var,
                   bg=C["input_bg"], fg=C["text"], font=("Consolas", 11),
                   buttonbackground=C["card"], insertbackground=C["text"],
                   relief="solid", bd=1).pack(side="left", padx=(4, 14))

        # Resources
        ttk.Label(inner, text="Resources:", style="Panel.TLabel").pack(side="left")
        self.n_res_var = tk.IntVar(value=3)
        tk.Spinbox(inner, from_=1, to=8, width=3, textvariable=self.n_res_var,
                   bg=C["input_bg"], fg=C["text"], font=("Consolas", 11),
                   buttonbackground=C["card"], insertbackground=C["text"],
                   relief="solid", bd=1).pack(side="left", padx=(4, 14))

        # Apply
        ttk.Button(inner, text="📐 Apply", style="Primary.TButton",
                   command=self._apply_dimensions).pack(side="left", padx=(0, 6))

        # Preset dropdown
        ttk.Label(inner, text="  Preset:", style="Panel.TLabel").pack(side="left")
        self.preset_var = tk.StringVar()
        presets = list(engine.get_presets().keys())
        combo = ttk.Combobox(inner, textvariable=self.preset_var,
                             values=presets, width=26, state="readonly",
                             font=("Segoe UI", 10))
        combo.pack(side="left", padx=(4, 14))
        combo.bind("<<ComboboxSelected>>",
                   lambda e: self._load_preset(self.preset_var.get()))

        # Action buttons (right side)
        ttk.Button(inner, text="📋 Export", style="Primary.TButton",
                   command=self._export_summary).pack(side="right", padx=(6, 0))
        ttk.Button(inner, text="🔄 Clear", style="Danger.TButton",
                   command=self._clear_all).pack(side="right", padx=(6, 0))

    # ───────────────────────────────────────────────────────────────────────────
    #  MATRIX PANEL (LEFT)
    # ───────────────────────────────────────────────────────────────────────────

    def _build_matrix_panel(self, state: BankerState):
        """Destroy and rebuild all matrix grids from the given state."""
        for w in self.matrix_frame.winfo_children():
            w.destroy()
        self.alloc_entries = []
        self.max_entries = []
        self.need_labels = []
        self.total_entries = []
        self.avail_labels = []
        self.proc_name_entries = []
        self.res_name_entries = []

        n = state.n_processes
        m = state.n_resources
        PAD = 3
        ENTRY_W = max(5, min(8, 14 - m))  # narrower when many resources

        parent = self.matrix_frame

        # ── Helper: create a matrix section ──
        def _make_header(text, row_offset):
            ttk.Label(parent, text=text, style="SectionH.TLabel").grid(
                row=row_offset, column=0, columnspan=m + 2, sticky="w",
                padx=8, pady=(10, 2))

        def _make_entry(r, c, val="0", width=ENTRY_W, readonly=False):
            e = tk.Entry(parent, width=width, justify="center",
                         bg=C["input_bg"], fg=C["text"], font=("Consolas", 11),
                         insertbackground=C["text"], relief="solid", bd=1,
                         highlightthickness=1, highlightbackground=C["border"],
                         highlightcolor=C["primary"],
                         disabledbackground=C["input_bg"],
                         disabledforeground=C["success"])
            e.insert(0, str(val))
            if readonly:
                e.configure(state="disabled", disabledforeground=C["success"])
            e.grid(row=r, column=c, padx=PAD, pady=PAD, sticky="ew")
            return e

        def _make_label(r, c, val="0", fg=C["success"], width=ENTRY_W):
            lbl = tk.Label(parent, text=str(val), width=width, anchor="center",
                           bg=C["input_bg"], fg=fg, font=("Consolas", 11),
                           relief="solid", bd=1)
            lbl.grid(row=r, column=c, padx=PAD, pady=PAD, sticky="ew")
            return lbl

        def _make_res_header_row(row):
            tk.Label(parent, text="", bg=C["panel"], width=12).grid(
                row=row, column=0, padx=PAD, pady=PAD)
            for j in range(m):
                e = tk.Entry(parent, width=ENTRY_W, justify="center",
                             bg=C["header"], fg=C["white"], font=("Segoe UI", 9, "bold"),
                             insertbackground=C["white"], relief="flat", bd=0)
                e.insert(0, state.resource_names[j])
                e.grid(row=row, column=j + 1, padx=PAD, pady=PAD, sticky="ew")
                self.res_name_entries.append(e)

        cur_row = 0

        # ── Total Resources ──
        _make_header("📦 Total Resources", cur_row)
        cur_row += 1
        _make_res_header_row(cur_row)
        cur_row += 1
        tk.Label(parent, text="Total", bg=C["panel"], fg=C["text_dim"],
                 font=("Segoe UI", 9, "bold"), anchor="e", width=12).grid(
            row=cur_row, column=0, padx=PAD, pady=PAD, sticky="e")
        for j in range(m):
            e = _make_entry(cur_row, j + 1, val=state.total_resources[j])
            self.total_entries.append(e)
            e.bind("<KeyRelease>", lambda ev: self._on_data_change())
        cur_row += 1

        # ── Available Resources ──
        tk.Label(parent, text="Available", bg=C["panel"], fg=C["warning"],
                 font=("Segoe UI", 9, "bold"), anchor="e", width=12).grid(
            row=cur_row, column=0, padx=PAD, pady=PAD, sticky="e")
        avail = state.compute_available()
        for j in range(m):
            lbl = _make_label(cur_row, j + 1, val=avail[j], fg=C["warning"])
            self.avail_labels.append(lbl)
        cur_row += 1

        # ── Allocation Matrix ──
        _make_header("📊 Allocation Matrix (currently held)", cur_row)
        cur_row += 1
        # Column headers
        tk.Label(parent, text="Process ▼", bg=C["panel"], fg=C["text_dim"],
                 font=("Segoe UI", 9), anchor="e", width=12).grid(
            row=cur_row, column=0, padx=PAD, pady=PAD, sticky="e")
        for j in range(m):
            tk.Label(parent, text=state.resource_names[j], bg=C["header"],
                     fg=C["white"], font=("Segoe UI", 9, "bold"),
                     width=ENTRY_W, anchor="center").grid(
                row=cur_row, column=j + 1, padx=PAD, pady=PAD, sticky="ew")
        cur_row += 1

        for i in range(n):
            # Process name (editable)
            pn_entry = tk.Entry(parent, width=14, justify="right",
                                bg=C["card"], fg=C["text"],
                                font=("Segoe UI", 9, "bold"),
                                insertbackground=C["text"], relief="flat", bd=0)
            pn_entry.insert(0, state.process_names[i])
            pn_entry.grid(row=cur_row, column=0, padx=PAD, pady=PAD, sticky="e")
            self.proc_name_entries.append(pn_entry)

            row_entries = []
            for j in range(m):
                e = _make_entry(cur_row, j + 1, val=state.allocation[i][j])
                e.bind("<KeyRelease>", lambda ev: self._on_data_change())
                row_entries.append(e)
            self.alloc_entries.append(row_entries)
            cur_row += 1

        # ── Max Matrix ──
        _make_header("📈 Maximum Need Matrix", cur_row)
        cur_row += 1
        tk.Label(parent, text="Process ▼", bg=C["panel"], fg=C["text_dim"],
                 font=("Segoe UI", 9), anchor="e", width=12).grid(
            row=cur_row, column=0, padx=PAD, pady=PAD, sticky="e")
        for j in range(m):
            tk.Label(parent, text=state.resource_names[j], bg=C["header"],
                     fg=C["white"], font=("Segoe UI", 9, "bold"),
                     width=ENTRY_W, anchor="center").grid(
                row=cur_row, column=j + 1, padx=PAD, pady=PAD, sticky="ew")
        cur_row += 1

        for i in range(n):
            tk.Label(parent, text=state.process_names[i], bg=C["card"],
                     fg=C["text"], font=("Segoe UI", 9, "bold"),
                     anchor="e", width=14).grid(
                row=cur_row, column=0, padx=PAD, pady=PAD, sticky="e")
            row_entries = []
            for j in range(m):
                e = _make_entry(cur_row, j + 1, val=state.max_matrix[i][j])
                e.bind("<KeyRelease>", lambda ev: self._on_data_change())
                row_entries.append(e)
            self.max_entries.append(row_entries)
            cur_row += 1

        # ── Need Matrix (auto-computed, read-only) ──
        _make_header("🔢 Need Matrix  (auto:  Max − Allocation)", cur_row)
        cur_row += 1
        tk.Label(parent, text="Process ▼", bg=C["panel"], fg=C["text_dim"],
                 font=("Segoe UI", 9), anchor="e", width=12).grid(
            row=cur_row, column=0, padx=PAD, pady=PAD, sticky="e")
        for j in range(m):
            tk.Label(parent, text=state.resource_names[j], bg=C["header"],
                     fg=C["white"], font=("Segoe UI", 9, "bold"),
                     width=ENTRY_W, anchor="center").grid(
                row=cur_row, column=j + 1, padx=PAD, pady=PAD, sticky="ew")
        cur_row += 1

        need = state.compute_need()
        for i in range(n):
            tk.Label(parent, text=state.process_names[i], bg=C["card"],
                     fg=C["text"], font=("Segoe UI", 9, "bold"),
                     anchor="e", width=14).grid(
                row=cur_row, column=0, padx=PAD, pady=PAD, sticky="e")
            row_labels = []
            for j in range(m):
                val = need[i][j]
                fg = C["danger"] if val < 0 else C["success"]
                lbl = _make_label(cur_row, j + 1, val=val, fg=fg)
                row_labels.append(lbl)
            self.need_labels.append(row_labels)
            cur_row += 1

        # ── Action Buttons ──
        btn_frame = ttk.Frame(parent, style="Panel.TFrame")
        btn_frame.grid(row=cur_row, column=0, columnspan=m + 2,
                       sticky="ew", padx=8, pady=(14, 8))

        ttk.Button(btn_frame, text="▶  Run Safety Check", style="Run.TButton",
                   command=self._run_safety_check).pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="🔍 Test Resource Request", style="Primary.TButton",
                   command=self._show_request_dialog).pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="🌳 All Safe Sequences", style="Primary.TButton",
                   command=self._show_all_sequences_dialog).pack(side="left")

    # ───────────────────────────────────────────────────────────────────────────
    #  VISUALIZER PANEL (RIGHT)
    # ───────────────────────────────────────────────────────────────────────────

    def _build_visualizer_panel(self):
        p = self.viz_frame

        # ── Result banner ──
        self.banner_var = tk.StringVar(value="Run the safety check to see the result")
        self.banner_label = tk.Label(
            p, textvariable=self.banner_var, bg=C["card"], fg=C["text_dim"],
            font=("Segoe UI", 12, "bold"), anchor="center", pady=8)
        self.banner_label.pack(fill="x", padx=8, pady=(8, 4))

        # ── Work vector ──
        work_frame = ttk.Frame(p, style="Panel.TFrame")
        work_frame.pack(fill="x", padx=8, pady=4)
        ttk.Label(work_frame, text="Work Vector:", style="PanelBold.TLabel").pack(
            side="left", padx=(4, 6))
        self.work_display = tk.Label(work_frame, text="—", bg=C["panel"],
                                     fg=C["warning"], font=("Consolas", 11))
        self.work_display.pack(side="left")

        # ── Process cards container ──
        ttk.Label(p, text="Process Status:", style="PanelBold.TLabel").pack(
            anchor="w", padx=12, pady=(6, 2))
        self.cards_frame = ttk.Frame(p, style="Panel.TFrame")
        self.cards_frame.pack(fill="x", padx=8, pady=2)

        # ── Safe sequence display ──
        ttk.Label(p, text="Safe Sequence:", style="PanelBold.TLabel").pack(
            anchor="w", padx=12, pady=(6, 2))
        self.seq_frame = ttk.Frame(p, style="Panel.TFrame")
        self.seq_frame.pack(fill="x", padx=8, pady=2)
        self.seq_placeholder = tk.Label(self.seq_frame, text="—", bg=C["panel"],
                                        fg=C["text_dim"], font=("Segoe UI", 10))
        self.seq_placeholder.pack(anchor="w", padx=4)

        # ── Stepper controls ──
        ctrl = ttk.Frame(p, style="Panel.TFrame")
        ctrl.pack(fill="x", padx=8, pady=(8, 4))

        for text, cmd in [
            ("⏮",  self._reset_stepper),
            ("◀",   self._step_backward),
            ("▶ / ⏸", self._play_pause),
            ("▶",   self._step_forward),
            ("⏩",  self._jump_to_end),
        ]:
            ttk.Button(ctrl, text=text, style="Ctrl.TButton",
                       command=cmd, width=5).pack(side="left", padx=2)

        # Speed slider
        ttk.Label(ctrl, text="  Speed:", style="Panel.TLabel").pack(side="left", padx=(10, 2))
        self.speed_var = tk.IntVar(value=800)
        speed_scale = ttk.Scale(ctrl, from_=100, to=2000, orient="horizontal",
                                variable=self.speed_var, style="Speed.Horizontal.TScale",
                                command=self._on_speed_change)
        speed_scale.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.speed_label = ttk.Label(ctrl, text="0.8s", style="Dim.TLabel")
        self.speed_label.pack(side="left")

        # Step counter
        self.step_counter_var = tk.StringVar(value="Step: — / —")
        ttk.Label(ctrl, textvariable=self.step_counter_var,
                  style="Dim.TLabel").pack(side="right", padx=(8, 4))

        # ── Step explanation log ──
        ttk.Label(p, text="Step-by-Step Explanation Log:",
                  style="PanelBold.TLabel").pack(anchor="w", padx=12, pady=(8, 2))
        log_frame = ttk.Frame(p, style="Panel.TFrame")
        log_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.log_text = tk.Text(
            log_frame, wrap="word", bg=C["input_bg"], fg=C["text"],
            font=("Consolas", 10), relief="solid", bd=1,
            insertbackground=C["text"], highlightthickness=0,
            padx=8, pady=6, state="disabled")
        log_sb = ttk.Scrollbar(log_frame, orient="vertical",
                               command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_sb.set)
        log_sb.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

        # Text tags for coloring
        self.log_text.tag_configure("safe", foreground=C["success"])
        self.log_text.tag_configure("unsafe", foreground=C["danger"])
        self.log_text.tag_configure("testing", foreground=C["warning"])
        self.log_text.tag_configure("granted", foreground=C["success"])
        self.log_text.tag_configure("blocked", foreground=C["danger"])
        self.log_text.tag_configure("info", foreground=C["text_dim"])
        self.log_text.tag_configure("header", foreground=C["primary"],
                                    font=("Consolas", 10, "bold"))

    # ───────────────────────────────────────────────────────────────────────────
    #  PROCESS CARDS
    # ───────────────────────────────────────────────────────────────────────────

    def _build_process_cards(self, state: BankerState):
        """Create/recreate the process status cards grid."""
        for w in self.cards_frame.winfo_children():
            w.destroy()
        self.process_cards = []

        cols = min(5, state.n_processes)
        for i in range(state.n_processes):
            r, c = divmod(i, cols)
            frame = tk.Frame(self.cards_frame, bg=C["wait_bg"], bd=2,
                             relief="solid", highlightbackground=C["wait_bd"],
                             highlightthickness=2, padx=8, pady=6)
            frame.grid(row=r, column=c, padx=4, pady=4, sticky="nsew")
            self.cards_frame.columnconfigure(c, weight=1)

            icon = tk.Label(frame, text="⚪", bg=C["wait_bg"],
                            font=("Segoe UI", 14))
            icon.pack()
            name = tk.Label(frame, text=state.process_names[i], bg=C["wait_bg"],
                            fg=C["text"], font=("Segoe UI", 9, "bold"))
            name.pack()
            status = tk.Label(frame, text="Waiting", bg=C["wait_bg"],
                              fg=C["text_dim"], font=("Segoe UI", 8))
            status.pack()

            self.process_cards.append({
                "frame": frame, "icon": icon,
                "name": name, "status": status,
            })

    def _set_card_state(self, idx, state_name):
        """Update a process card's visual state."""
        card = self.process_cards[idx]
        configs = {
            "waiting":  ("⚪", "Waiting",   C["wait_bg"],    C["wait_bd"]),
            "testing":  ("🟡", "Testing…",  C["warning_d"],  C["warning"]),
            "granted":  ("🟢", "Executed ✓", C["success_d"], C["success"]),
            "blocked":  ("🔴", "Blocked ✗",  C["danger_d"],  C["danger"]),
        }
        icon, text, bg, bd = configs.get(state_name, configs["waiting"])
        card["frame"].configure(bg=bg, highlightbackground=bd)
        card["icon"].configure(text=icon, bg=bg)
        card["name"].configure(bg=bg)
        card["status"].configure(text=text, bg=bg)

    # ───────────────────────────────────────────────────────────────────────────
    #  DATA FLOW: collecting, loading, updating
    # ───────────────────────────────────────────────────────────────────────────

    def _safe_int(self, entry_widget, default=0) -> int:
        """Read an int from an Entry widget, return default on failure."""
        try:
            return int(entry_widget.get().strip())
        except (ValueError, tk.TclError):
            return default

    def _collect_state(self) -> BankerState:
        """Read all matrix entries and return a BankerState."""
        n = len(self.alloc_entries)
        m = len(self.total_entries)

        proc_names = [e.get().strip() or f"P{i}" for i, e in enumerate(self.proc_name_entries)]
        # Resource names come from the first set of res_name_entries (there are 3 sets — one per header row).
        # We only store the first m entries.
        res_names = [self.res_name_entries[j].get().strip() or chr(65 + j) for j in range(m)]

        alloc = [[self._safe_int(self.alloc_entries[i][j]) for j in range(m)] for i in range(n)]
        maxm = [[self._safe_int(self.max_entries[i][j]) for j in range(m)] for i in range(n)]
        total = [self._safe_int(self.total_entries[j]) for j in range(m)]

        return BankerState(n, m, proc_names, res_names, alloc, maxm, total)

    def _on_data_change(self):
        """Called on every keystroke in allocation/max/total entries. Updates Need & Available."""
        try:
            state = self._collect_state()
            need = state.compute_need()
            avail = state.compute_available()

            for i in range(state.n_processes):
                for j in range(state.n_resources):
                    val = need[i][j]
                    fg = C["danger"] if val < 0 else C["success"]
                    self.need_labels[i][j].configure(text=str(val), fg=fg)

            for j in range(state.n_resources):
                val = avail[j]
                fg = C["danger"] if val < 0 else C["warning"]
                self.avail_labels[j].configure(text=str(val), fg=fg)
        except (IndexError, AttributeError):
            pass  # dimensions mismatch during rebuild

    def _load_preset(self, name: str):
        """Load a preset scenario by name."""
        presets = engine.get_presets()
        if name not in presets:
            return
        state = presets[name]
        self.preset_var.set(name)
        self.n_proc_var.set(state.n_processes)
        self.n_res_var.set(state.n_resources)
        self.banker_state = state
        self._build_matrix_panel(state)
        self._build_process_cards(state)
        self._reset_stepper()

    def _apply_dimensions(self):
        """Create a blank state with the specified dimensions."""
        n = self.n_proc_var.get()
        m = self.n_res_var.get()
        state = BankerState(n, m)
        self.banker_state = state
        self._build_matrix_panel(state)
        self._build_process_cards(state)
        self._reset_stepper()

    def _clear_all(self):
        """Reset to blank with current dimensions."""
        self._apply_dimensions()

    # ───────────────────────────────────────────────────────────────────────────
    #  SAFETY CHECK EXECUTION
    # ───────────────────────────────────────────────────────────────────────────

    def _run_safety_check(self):
        """Collect current state, validate, run safety check, populate stepper."""
        state = self._collect_state()
        errors = state.validate()
        if errors:
            messagebox.showerror("Validation Error",
                                 "Please fix the following:\n\n• " + "\n• ".join(errors))
            return

        self.banker_state = state
        self.steps = engine.safety_check(state)
        self.current_step_idx = -1
        self.playing = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None

        # Rebuild cards for current process names
        self._build_process_cards(state)

        # Clear log
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

        # Clear sequence display
        for w in self.seq_frame.winfo_children():
            w.destroy()
        self.seq_placeholder = tk.Label(self.seq_frame, text="—", bg=C["panel"],
                                        fg=C["text_dim"], font=("Segoe UI", 10))
        self.seq_placeholder.pack(anchor="w", padx=4)

        # Set banner to "running"
        self.banner_var.set("⏳ Safety check ready — use stepper or Play")
        self.banner_label.configure(bg=C["card"], fg=C["text_dim"])

        # Update step counter
        self.step_counter_var.set(f"Step: 0 / {len(self.steps)}")

        # Auto-step to first
        self._step_forward()

    # ───────────────────────────────────────────────────────────────────────────
    #  STEPPER CONTROLS
    # ───────────────────────────────────────────────────────────────────────────

    def _reset_stepper(self):
        self.playing = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self.current_step_idx = -1
        self.steps = []

        # Reset cards
        for i in range(len(self.process_cards)):
            self._set_card_state(i, "waiting")

        # Reset banner
        self.banner_var.set("Run the safety check to see the result")
        self.banner_label.configure(bg=C["card"], fg=C["text_dim"])

        # Reset work display
        self.work_display.configure(text="—")

        # Reset sequence
        for w in self.seq_frame.winfo_children():
            w.destroy()
        tk.Label(self.seq_frame, text="—", bg=C["panel"],
                 fg=C["text_dim"], font=("Segoe UI", 10)).pack(anchor="w", padx=4)

        # Clear log
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

        self.step_counter_var.set("Step: — / —")

    def _step_forward(self):
        if not self.steps:
            return
        if self.current_step_idx < len(self.steps) - 1:
            self.current_step_idx += 1
            self._display_step(self.current_step_idx)

    def _step_backward(self):
        if not self.steps or self.current_step_idx <= 0:
            return
        self.current_step_idx -= 1
        # Rebuild visualization from scratch up to current step
        self._rebuild_up_to(self.current_step_idx)

    def _jump_to_end(self):
        if not self.steps:
            return
        self.playing = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        # Show all steps
        while self.current_step_idx < len(self.steps) - 1:
            self.current_step_idx += 1
            self._display_step(self.current_step_idx, log_only=(
                self.current_step_idx < len(self.steps) - 1))

    def _play_pause(self):
        if not self.steps:
            return
        self.playing = not self.playing
        if self.playing:
            self._animate()
        else:
            if self._after_id:
                self.after_cancel(self._after_id)
                self._after_id = None

    def _animate(self):
        if not self.playing:
            return
        if self.current_step_idx < len(self.steps) - 1:
            self._step_forward()
            self._after_id = self.after(self.play_speed_ms, self._animate)
        else:
            self.playing = False

    def _on_speed_change(self, val):
        self.play_speed_ms = int(float(val))
        secs = self.play_speed_ms / 1000
        self.speed_label.configure(text=f"{secs:.1f}s")

    # ───────────────────────────────────────────────────────────────────────────
    #  DISPLAY A STEP
    # ───────────────────────────────────────────────────────────────────────────

    def _display_step(self, idx, log_only=False):
        """Update the visualization for the given step index."""
        step = self.steps[idx]

        # Update step counter
        self.step_counter_var.set(f"Step: {idx + 1} / {len(self.steps)}")

        # ── Append to log ──
        tag = {
            "start": "info", "pass_start": "header",
            "testing": "testing", "granted": "granted",
            "blocked": "blocked", "safe": "safe", "unsafe": "unsafe",
        }.get(step.action, "info")

        self.log_text.configure(state="normal")
        self.log_text.insert("end", step.explanation + "\n\n", tag)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

        if log_only:
            return

        # ── Update work vector display ──
        if self.banker_state:
            rn = self.banker_state.resource_names
            parts = [f"{n}: {v}" for n, v in zip(rn, step.work_vector)]
            self.work_display.configure(text="  ".join(parts))

        # ── Update process cards ──
        # First, reset all cards to reflect finish state
        for i in range(len(self.process_cards)):
            if step.finish[i]:
                self._set_card_state(i, "granted")
            else:
                self._set_card_state(i, "waiting")

        # Then highlight the current process
        if step.current_process is not None:
            if step.action == "testing":
                self._set_card_state(step.current_process, "testing")
            elif step.action == "granted":
                self._set_card_state(step.current_process, "granted")
            elif step.action == "blocked":
                self._set_card_state(step.current_process, "blocked")

        # On final unsafe, mark all unfinished as blocked
        if step.action == "unsafe":
            for i in range(len(self.process_cards)):
                if not step.finish[i]:
                    self._set_card_state(i, "blocked")

        # ── Update safe sequence display ──
        if step.sequence_so_far and self.banker_state:
            for w in self.seq_frame.winfo_children():
                w.destroy()
            pn = self.banker_state.process_names
            for seq_idx, proc_i in enumerate(step.sequence_so_far):
                if seq_idx > 0:
                    tk.Label(self.seq_frame, text="→", bg=C["panel"],
                             fg=C["text_dim"], font=("Segoe UI", 11)).pack(
                        side="left", padx=2)
                badge = tk.Label(self.seq_frame, text=f" {pn[proc_i]} ",
                                 bg=C["success_d"], fg=C["success"],
                                 font=("Segoe UI", 10, "bold"),
                                 relief="solid", bd=1, padx=6, pady=2)
                badge.pack(side="left", padx=2)

        # ── Update banner on final step ──
        if step.action == "safe":
            self.banner_var.set("🟢  SAFE STATE — No deadlock risk!")
            self.banner_label.configure(bg=C["success_d"], fg=C["success"])
        elif step.action == "unsafe":
            self.banner_var.set("🔴  UNSAFE STATE — Deadlock risk!")
            self.banner_label.configure(bg=C["danger_d"], fg=C["danger"])

    def _rebuild_up_to(self, target_idx):
        """Rebuild the visual state from step 0 to target_idx (for stepping backward)."""
        # Reset cards
        for i in range(len(self.process_cards)):
            self._set_card_state(i, "waiting")

        # Reset banner
        self.banner_var.set("⏳ Stepping…")
        self.banner_label.configure(bg=C["card"], fg=C["text_dim"])

        # Clear sequence display
        for w in self.seq_frame.winfo_children():
            w.destroy()
        tk.Label(self.seq_frame, text="—", bg=C["panel"],
                 fg=C["text_dim"], font=("Segoe UI", 10)).pack(anchor="w", padx=4)

        # Clear and replay log
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

        for i in range(target_idx + 1):
            is_last = (i == target_idx)
            self._display_step(i, log_only=not is_last)
        # Show final visuals for the target step
        if target_idx >= 0:
            self._display_step(target_idx, log_only=False)

    # ───────────────────────────────────────────────────────────────────────────
    #  RESOURCE REQUEST DIALOG
    # ───────────────────────────────────────────────────────────────────────────

    def _show_request_dialog(self):
        state = self._collect_state()
        errors = state.validate()
        if errors:
            messagebox.showerror("Validation Error",
                                 "Fix input errors first:\n\n• " + "\n• ".join(errors))
            return

        dialog = tk.Toplevel(self)
        dialog.title("🔍 Test Resource Request")
        dialog.configure(bg=C["bg"])
        dialog.geometry("520x480")
        dialog.transient(self)
        dialog.grab_set()

        # Header
        tk.Label(dialog, text="Simulate a Resource Request",
                 bg=C["bg"], fg=C["text"], font=("Segoe UI", 14, "bold")).pack(
            pady=(12, 8))
        tk.Label(dialog, text="Select a process and enter the resources it requests.",
                 bg=C["bg"], fg=C["text_dim"], font=("Segoe UI", 10)).pack(pady=(0, 10))

        # Process selector
        sel_frame = tk.Frame(dialog, bg=C["bg"])
        sel_frame.pack(fill="x", padx=20, pady=4)
        tk.Label(sel_frame, text="Process:", bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 10)).pack(side="left")
        proc_var = tk.StringVar(value=state.process_names[0])
        proc_combo = ttk.Combobox(sel_frame, textvariable=proc_var,
                                  values=state.process_names, state="readonly",
                                  width=20, font=("Segoe UI", 10))
        proc_combo.pack(side="left", padx=(8, 0))

        # Request vector entries
        tk.Label(dialog, text="Request Vector:", bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=20, pady=(10, 4))

        req_frame = tk.Frame(dialog, bg=C["bg"])
        req_frame.pack(fill="x", padx=20, pady=4)
        req_entries = []
        for j in range(state.n_resources):
            tk.Label(req_frame, text=state.resource_names[j] + ":", bg=C["bg"],
                     fg=C["text_dim"], font=("Segoe UI", 9)).grid(
                row=0, column=j * 2, padx=(0, 4))
            e = tk.Entry(req_frame, width=5, justify="center", bg=C["input_bg"],
                         fg=C["text"], font=("Consolas", 11), insertbackground=C["text"],
                         relief="solid", bd=1)
            e.insert(0, "0")
            e.grid(row=0, column=j * 2 + 1, padx=(0, 10))
            req_entries.append(e)

        # Result display
        result_text = tk.Text(dialog, wrap="word", bg=C["input_bg"], fg=C["text"],
                              font=("Consolas", 10), relief="solid", bd=1,
                              height=10, padx=8, pady=6, highlightthickness=0)
        result_text.pack(fill="both", expand=True, padx=20, pady=(10, 8))
        result_text.tag_configure("granted", foreground=C["success"])
        result_text.tag_configure("denied", foreground=C["danger"])

        def _submit():
            pid = state.process_names.index(proc_var.get())
            try:
                req_vec = [int(e.get().strip()) for e in req_entries]
            except ValueError:
                messagebox.showerror("Error", "All request values must be integers.",
                                     parent=dialog)
                return

            result = engine.request_resources(state, pid, req_vec)
            result_text.configure(state="normal")
            result_text.delete("1.0", "end")
            tag = "granted" if result.granted else "denied"
            result_text.insert("end", result.reason, tag)
            result_text.configure(state="disabled")

        ttk.Button(dialog, text="🧪 Test Request", style="Run.TButton",
                   command=_submit).pack(pady=(0, 12))

    # ───────────────────────────────────────────────────────────────────────────
    #  ALL SAFE SEQUENCES DIALOG
    # ───────────────────────────────────────────────────────────────────────────

    def _show_all_sequences_dialog(self):
        state = self._collect_state()
        errors = state.validate()
        if errors:
            messagebox.showerror("Validation Error",
                                 "Fix input errors first:\n\n• " + "\n• ".join(errors))
            return

        # Compute
        seqs = engine.find_all_sequences(state, max_results=500)

        dialog = tk.Toplevel(self)
        dialog.title("🌳 All Safe Sequences")
        dialog.configure(bg=C["bg"])
        dialog.geometry("560x480")
        dialog.transient(self)
        dialog.grab_set()

        count = len(seqs)
        capped = count >= 500

        tk.Label(dialog, text="All Possible Safe Sequences",
                 bg=C["bg"], fg=C["text"], font=("Segoe UI", 14, "bold")).pack(
            pady=(12, 4))

        count_text = f"Found: {count} safe sequence{'s' if count != 1 else ''}"
        if capped:
            count_text += " (capped at 500)"
        if count == 0:
            count_text = "No safe sequences found — system is UNSAFE"
        fg = C["success"] if count > 0 else C["danger"]
        tk.Label(dialog, text=count_text, bg=C["bg"], fg=fg,
                 font=("Segoe UI", 11, "bold")).pack(pady=(0, 10))

        # List
        list_text = tk.Text(dialog, wrap="word", bg=C["input_bg"], fg=C["text"],
                            font=("Consolas", 10), relief="solid", bd=1,
                            padx=8, pady=6, highlightthickness=0)
        sb = ttk.Scrollbar(dialog, orient="vertical", command=list_text.yview)
        list_text.configure(yscrollcommand=sb.set)

        frame = tk.Frame(dialog, bg=C["bg"])
        frame.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        sb.pack(in_=frame, side="right", fill="y")
        list_text.pack(in_=frame, side="left", fill="both", expand=True)

        for idx, seq in enumerate(seqs):
            seq_str = "  →  ".join(state.process_names[i] for i in seq)
            list_text.insert("end", f"{idx + 1:>3}.  {seq_str}\n")

        if count == 0:
            list_text.insert("end", "The system is in an UNSAFE state.\n"
                             "No execution ordering can satisfy all processes.\n")

        list_text.configure(state="disabled")

    # ───────────────────────────────────────────────────────────────────────────
    #  EXPORT SUMMARY
    # ───────────────────────────────────────────────────────────────────────────

    def _export_summary(self):
        state = self._collect_state()
        errors = state.validate()
        if errors:
            messagebox.showerror("Validation Error",
                                 "Fix input errors first:\n\n• " + "\n• ".join(errors))
            return

        need = state.compute_need()
        avail = state.compute_available()
        steps = engine.safety_check(state)
        final = steps[-1] if steps else None

        lines = []
        lines.append("=" * 60)
        lines.append("  BANKER'S ALGORITHM — LAB SUMMARY")
        lines.append("=" * 60)
        lines.append("")

        # Dimensions
        lines.append(f"Processes: {state.n_processes}    Resources: {state.n_resources}")
        lines.append(f"Resource Names: {', '.join(state.resource_names)}")
        lines.append(f"Process Names:  {', '.join(state.process_names)}")
        lines.append("")

        # Total & Available
        lines.append(f"Total Resources:     {state.total_resources}")
        lines.append(f"Available Resources: {avail}")
        lines.append("")

        # Matrices
        hdr = "".ljust(16) + "  ".join(f"{r:>6}" for r in state.resource_names)
        for title, matrix in [("Allocation", state.allocation),
                              ("Max", state.max_matrix),
                              ("Need", need)]:
            lines.append(f"── {title} Matrix ──")
            lines.append(hdr)
            for i in range(state.n_processes):
                row = "  ".join(f"{v:>6}" for v in matrix[i])
                lines.append(f"{state.process_names[i]:>16}{row}")
            lines.append("")

        # Result
        if final:
            lines.append("── Result ──")
            lines.append(final.explanation)
            lines.append("")

        # Step log
        lines.append("── Step-by-Step Log ──")
        for s in steps:
            lines.append(s.explanation)
        lines.append("")
        lines.append("=" * 60)

        summary = "\n".join(lines)

        # Copy to clipboard
        self.clipboard_clear()
        self.clipboard_append(summary)

        # Also save to file
        try:
            with open("lab_summary.txt", "w", encoding="utf-8") as f:
                f.write(summary)
            messagebox.showinfo(
                "Exported",
                "Summary copied to clipboard and saved to 'lab_summary.txt'!")
        except OSError:
            messagebox.showinfo("Exported", "Summary copied to clipboard!")


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = App()
    app.mainloop()

