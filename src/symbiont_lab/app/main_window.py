from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .discovery import discover_experiments, find_experiments_root
from .models import ExperimentEntry
from .run_controller import RunController


class SymbiontLabWindow:
    POLL_MS = 150

    BG = "#0b0f14"
    SURFACE = "#111821"
    SURFACE_2 = "#161f2a"
    BORDER = "#25303d"
    FG = "#e6edf3"
    MUTED = "#8b98a5"
    ACCENT = "#4aa8ff"
    GREEN = "#3fb950"
    RED = "#f85149"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Symbiont Lab")
        root.geometry("1560x940")
        root.minsize(1180, 760)
        root.configure(bg=self.BG)

        self.controller = RunController()
        self.entries: dict[str, ExperimentEntry] = {}
        self.selected: ExperimentEntry | None = None
        self.physics_tab = None
        self._physics_cleanup = None
        self._physics_paused = False
        self._focused_workspace = None

        self.status_var = tk.StringVar(value="Ready")
        self.run_var = tk.StringVar(value="No active run")
        self.detail_var = tk.StringVar(value="Select an experiment or launch Physics3D.")

        self._configure_style()
        self._build_menu()
        self._build_topbar()
        self._build_body()
        self._build_statusbar()
        self.refresh_experiments()

        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(self.POLL_MS, self._poll_runs)

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(".", background=self.BG, foreground=self.FG)
        style.configure("App.TFrame", background=self.BG)
        style.configure("Surface.TFrame", background=self.SURFACE)
        style.configure("Surface2.TFrame", background=self.SURFACE_2)
        style.configure(
            "Title.TLabel",
            background=self.BG,
            foreground=self.FG,
            font=("TkDefaultFont", 15, "bold"),
        )
        style.configure(
            "Section.TLabel",
            background=self.SURFACE,
            foreground=self.MUTED,
            font=("TkDefaultFont", 9, "bold"),
        )
        style.configure(
            "CardTitle.TLabel",
            background=self.SURFACE_2,
            foreground=self.FG,
            font=("TkDefaultFont", 10, "bold"),
        )
        style.configure(
            "Muted.TLabel",
            background=self.SURFACE,
            foreground=self.MUTED,
        )
        style.configure(
            "TButton",
            background=self.SURFACE_2,
            foreground=self.FG,
            bordercolor=self.BORDER,
            focusthickness=0,
            padding=(10, 6),
        )
        style.map(
            "TButton",
            background=[("active", "#1e2a36"), ("pressed", "#263645")],
            foreground=[("disabled", "#687481")],
        )
        style.configure(
            "Accent.TButton",
            background=self.ACCENT,
            foreground="#081018",
            bordercolor=self.ACCENT,
            font=("TkDefaultFont", 9, "bold"),
        )
        style.map("Accent.TButton", background=[("active", "#6bb8ff")])
        style.configure(
            "Treeview",
            background=self.SURFACE,
            fieldbackground=self.SURFACE,
            foreground=self.FG,
            bordercolor=self.BORDER,
            rowheight=27,
        )
        style.map(
            "Treeview",
            background=[("selected", "#17324a")],
            foreground=[("selected", "#ffffff")],
        )
        style.configure(
            "TNotebook",
            background=self.BG,
            borderwidth=0,
            tabmargins=(0, 0, 0, 0),
        )
        style.configure(
            "TNotebook.Tab",
            background=self.BG,
            foreground=self.MUTED,
            padding=(14, 8),
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.SURFACE)],
            foreground=[("selected", self.FG), ("active", self.FG)],
        )
        style.configure("TPanedwindow", background=self.BORDER)
        style.configure(
            "TCombobox",
            fieldbackground=self.SURFACE_2,
            background=self.SURFACE_2,
            foreground=self.FG,
            arrowcolor=self.FG,
        )

    def _build_menu(self) -> None:
        menu = tk.Menu(
            self.root,
            bg=self.SURFACE,
            fg=self.FG,
            activebackground="#1e2a36",
            activeforeground=self.FG,
            relief="flat",
        )
        file_menu = tk.Menu(menu, tearoff=False, bg=self.SURFACE, fg=self.FG)
        file_menu.add_command(label="Refresh experiments", command=self.refresh_experiments)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.close)
        menu.add_cascade(label="File", menu=file_menu)

        run_menu = tk.Menu(menu, tearoff=False, bg=self.SURFACE, fg=self.FG)
        run_menu.add_command(label="Run selected experiment", command=self.run_selected)
        run_menu.add_command(label="Launch Physics3D", command=self.launch_physics3d)
        run_menu.add_separator()
        run_menu.add_command(label="Stop active run", command=self.stop_run)
        menu.add_cascade(label="Run", menu=run_menu)

        view_menu = tk.Menu(menu, tearoff=False, bg=self.SURFACE, fg=self.FG)
        view_menu.add_command(label="Lab", command=lambda: self.notebook.select(self.experiment_tab))
        view_menu.add_command(label="Output", command=lambda: self.notebook.select(self.output_tab))
        menu.add_cascade(label="View", menu=view_menu)

        help_menu = tk.Menu(menu, tearoff=False, bg=self.SURFACE, fg=self.FG)
        help_menu.add_command(
            label="About",
            command=lambda: messagebox.showinfo(
                "Symbiont Lab",
                "Symbiont Lab scientific workbench",
            ),
        )
        menu.add_cascade(label="Help", menu=help_menu)
        self.root.configure(menu=menu)

    def _build_topbar(self) -> None:
        self.topbar = tk.Frame(
            self.root,
            bg=self.BG,
            height=58,
            padx=14,
            pady=9,
        )
        self.topbar.pack(fill="x")
        self.topbar.pack_propagate(False)

        brand = tk.Frame(self.topbar, bg=self.BG)
        brand.pack(side="left")
        tk.Label(
            brand,
            text="SYMBIONT",
            bg=self.BG,
            fg=self.FG,
            font=("TkDefaultFont", 13, "bold"),
        ).pack(side="left")
        tk.Label(
            brand,
            text=" LAB",
            bg=self.BG,
            fg=self.ACCENT,
            font=("TkDefaultFont", 13, "bold"),
        ).pack(side="left")

        self.workspace_title = tk.StringVar(value="Lab")
        tk.Label(
            self.topbar,
            textvariable=self.workspace_title,
            bg=self.BG,
            fg=self.MUTED,
            font=("TkDefaultFont", 10),
            padx=18,
        ).pack(side="left")

        self.primary_actions = tk.Frame(self.topbar, bg=self.BG)
        self.primary_actions.pack(side="left", padx=(10, 0))

        self.run_button = ttk.Button(
            self.primary_actions,
            text="Run experiment",
            command=self.run_selected,
            style="Accent.TButton",
        )
        self.run_button.pack(side="left", padx=3)

        self.physics_button = ttk.Button(
            self.primary_actions,
            text="Launch 3D",
            command=self.launch_physics3d,
        )
        self.physics_button.pack(side="left", padx=3)

        self.stop_button = ttk.Button(
            self.primary_actions,
            text="Stop",
            command=self.stop_run,
        )
        self.stop_button.pack(side="left", padx=3)

        self.physics_controls = tk.Frame(self.topbar, bg=self.BG)
        self.pause_button = ttk.Button(
            self.physics_controls,
            text="Pause",
            command=self.toggle_physics_pause,
        )
        self.pause_button.pack(side="left", padx=2)
        ttk.Button(
            self.physics_controls,
            text="+1 tick",
            command=self.step_physics,
        ).pack(side="left", padx=2)
        tk.Label(
            self.physics_controls,
            text="Speed",
            bg=self.BG,
            fg=self.MUTED,
            padx=8,
        ).pack(side="left")
        self.physics_speed = tk.StringVar(value="1x")
        speed = ttk.Combobox(
            self.physics_controls,
            textvariable=self.physics_speed,
            values=("0.5x", "1x", "2x", "10x"),
            width=5,
            state="readonly",
        )
        speed.pack(side="left", padx=2)
        speed.bind("<<ComboboxSelected>>", self._on_physics_speed)

        status = tk.Frame(self.topbar, bg=self.BG)
        status.pack(side="right")
        self.live_dot = tk.Label(
            status,
            text="●",
            bg=self.BG,
            fg=self.MUTED,
            font=("TkDefaultFont", 10),
        )
        self.live_dot.pack(side="left", padx=(0, 5))
        tk.Label(
            status,
            textvariable=self.run_var,
            bg=self.BG,
            fg=self.MUTED,
            font=("TkDefaultFont", 9),
        ).pack(side="left")

    def _build_body(self) -> None:
        shell = tk.Frame(self.root, bg=self.BG)
        shell.pack(fill="both", expand=True)

        self.nav_rail = tk.Frame(shell, bg="#0d131b", width=72)
        self.nav_rail.pack(side="left", fill="y")
        self.nav_rail.pack_propagate(False)

        def nav_button(text: str, label: str, command):
            btn = tk.Button(
                self.nav_rail,
                text=f"{text}\n{label}",
                command=command,
                bg="#0d131b",
                fg=self.MUTED,
                activebackground="#17212c",
                activeforeground=self.FG,
                relief="flat",
                bd=0,
                font=("TkDefaultFont", 8, "bold"),
                padx=4,
                pady=12,
                cursor="hand2",
            )
            btn.pack(fill="x", pady=2)
            return btn

        self.lab_nav = nav_button("LAB", "Experiments", lambda: self.notebook.select(self.experiment_tab))
        self.body_nav = nav_button("3D", "Body", self._select_or_launch_physics)
        self.log_nav = nav_button("LOG", "Output", lambda: self.notebook.select(self.output_tab))

        self.outer = ttk.Panedwindow(shell, orient="horizontal")
        self.outer.pack(side="left", fill="both", expand=True)

        self.left_sidebar = ttk.Frame(self.outer, style="Surface.TFrame", padding=12)
        self.outer.add(self.left_sidebar, weight=1)
        ttk.Label(
            self.left_sidebar,
            text="EXPERIMENTS",
            style="Section.TLabel",
        ).pack(fill="x", pady=(0, 8))

        self.tree = ttk.Treeview(self.left_sidebar, show="tree", selectmode="browse")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.center_workspace = ttk.Frame(self.outer, style="App.TFrame")
        self.outer.add(self.center_workspace, weight=5)

        self.notebook = ttk.Notebook(self.center_workspace)
        self.notebook.pack(fill="both", expand=True)
        self.experiment_tab = ttk.Frame(self.notebook, style="Surface.TFrame", padding=22)
        self.output_tab = ttk.Frame(self.notebook, style="Surface.TFrame", padding=12)
        self.notebook.add(self.experiment_tab, text="Lab")
        self.notebook.add(self.output_tab, text="Output")
        self.notebook.bind("<<NotebookTabChanged>>", self._on_workspace_changed)

        self._build_lab_view()
        self._build_output_view()

        self.right_sidebar = ttk.Frame(self.outer, style="Surface.TFrame", padding=14)
        self.outer.add(self.right_sidebar, weight=1)
        self._build_inspector()

    def _build_lab_view(self) -> None:
        self.title_var = tk.StringVar(value="Experiment workspace")
        self.protocol_var = tk.StringVar(value="Select an experiment from the explorer.")
        self.path_var = tk.StringVar(value="")
        self.hypothesis_var = tk.StringVar(value="")
        self.criteria_var = tk.StringVar(value="")
        self.design_var = tk.StringVar(value="")

        ttk.Label(
            self.experiment_tab,
            textvariable=self.title_var,
            style="Title.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            self.experiment_tab,
            textvariable=self.protocol_var,
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 18))

        cards = tk.Frame(self.experiment_tab, bg=self.SURFACE)
        cards.pack(fill="x")

        self._card(cards, "Design", self.design_var)
        self._card(cards, "Hypothesis", self.hypothesis_var)
        self._card(cards, "Success criteria", self.criteria_var)
        self._card(cards, "Specification", self.path_var)

        actions = tk.Frame(self.experiment_tab, bg=self.SURFACE)
        actions.pack(fill="x", pady=(20, 0))
        ttk.Button(
            actions,
            text="Run experiment",
            command=self.run_selected,
            style="Accent.TButton",
        ).pack(side="left")
        ttk.Button(
            actions,
            text="Open in Physics3D",
            command=self.launch_physics3d,
        ).pack(side="left", padx=8)

    def _card(self, parent, title: str, variable: tk.StringVar) -> None:
        card = tk.Frame(
            parent,
            bg=self.SURFACE_2,
            highlightthickness=1,
            highlightbackground=self.BORDER,
            padx=14,
            pady=12,
        )
        card.pack(fill="x", pady=5)
        tk.Label(
            card,
            text=title,
            bg=self.SURFACE_2,
            fg=self.MUTED,
            font=("TkDefaultFont", 8, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            card,
            textvariable=variable,
            bg=self.SURFACE_2,
            fg=self.FG,
            font=("TkDefaultFont", 10),
            anchor="w",
            justify="left",
            wraplength=820,
            pady=4,
        ).pack(fill="x")

    def _build_output_view(self) -> None:
        ttk.Label(
            self.output_tab,
            text="Run output",
            style="Title.TLabel",
        ).pack(anchor="w", pady=(0, 8))
        self.output = tk.Text(
            self.output_tab,
            wrap="word",
            bg="#090d12",
            fg="#c9d1d9",
            insertbackground=self.FG,
            selectbackground="#214d73",
            relief="flat",
            bd=0,
            font=("TkFixedFont", 9),
            padx=12,
            pady=10,
        )
        self.output.pack(fill="both", expand=True)
        self.output.configure(state="disabled")

    def _build_inspector(self) -> None:
        ttk.Label(
            self.right_sidebar,
            text="INSPECTOR",
            style="Section.TLabel",
        ).pack(fill="x", pady=(0, 10))

        for title, var in (
            ("Run", self.run_var),
            ("Status", self.status_var),
            ("Detail", self.detail_var),
        ):
            box = tk.Frame(
                self.right_sidebar,
                bg=self.SURFACE_2,
                highlightthickness=1,
                highlightbackground=self.BORDER,
                padx=10,
                pady=9,
            )
            box.pack(fill="x", pady=4)
            tk.Label(
                box,
                text=title,
                bg=self.SURFACE_2,
                fg=self.MUTED,
                font=("TkDefaultFont", 8, "bold"),
            ).pack(anchor="w")
            tk.Label(
                box,
                textvariable=var,
                bg=self.SURFACE_2,
                fg=self.FG,
                justify="left",
                wraplength=250,
            ).pack(anchor="w", pady=(3, 0))

    def _build_statusbar(self) -> None:
        bar = tk.Frame(
            self.root,
            bg="#090d12",
            height=28,
            padx=10,
        )
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Label(
            bar,
            textvariable=self.status_var,
            bg="#090d12",
            fg=self.MUTED,
            font=("TkDefaultFont", 8),
        ).pack(side="left")
        tk.Label(
            bar,
            textvariable=self.detail_var,
            bg="#090d12",
            fg=self.MUTED,
            font=("TkDefaultFont", 8),
        ).pack(side="right")

    def _select_or_launch_physics(self) -> None:
        if self.physics_tab is not None:
            self.notebook.select(self.physics_tab)
        else:
            self.launch_physics3d()

    def _on_workspace_changed(self, _event=None) -> None:
        selected = self.notebook.select()
        is_physics = self.physics_tab is not None and selected == str(self.physics_tab)
        self._set_physics_focus(is_physics)
        if is_physics:
            self.workspace_title.set("Body")
        elif selected == str(self.output_tab):
            self.workspace_title.set("Output")
        else:
            self.workspace_title.set("Lab")

    def _set_physics_focus(self, enabled: bool) -> None:
        if enabled and self._focused_workspace != "physics":
            try:
                self.outer.forget(self.left_sidebar)
            except tk.TclError:
                pass
            try:
                self.outer.forget(self.right_sidebar)
            except tk.TclError:
                pass
            self.primary_actions.pack_forget()
            self.physics_controls.pack(side="left", padx=(10, 0))
            self._focused_workspace = "physics"
            return

        if not enabled and self._focused_workspace == "physics":
            self.physics_controls.pack_forget()
            panes = {str(pane) for pane in self.outer.panes()}
            if str(self.left_sidebar) not in panes:
                self.outer.insert(0, self.left_sidebar, weight=1)
            if str(self.right_sidebar) not in panes:
                self.outer.add(self.right_sidebar, weight=1)
            self.primary_actions.pack(side="left", padx=(10, 0))
            self._focused_workspace = None

    def toggle_physics_pause(self) -> None:
        self._physics_paused = not self._physics_paused
        self.controller.send_physics_command({
            "type": "pause",
            "paused": self._physics_paused,
        })
        self.pause_button.configure(
            text="Resume" if self._physics_paused else "Pause"
        )

    def step_physics(self) -> None:
        self.controller.send_physics_command({"type": "step"})

    def _on_physics_speed(self, _event=None) -> None:
        raw = self.physics_speed.get().rstrip("x")
        try:
            speed = float(raw)
        except ValueError:
            speed = 1.0
        self.controller.send_physics_command({"type": "speed", "speed": speed})

    def refresh_experiments(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.entries.clear()
        root = find_experiments_root()
        entries = discover_experiments(root)
        categories: dict[str, str] = {}

        for entry in entries:
            parent = categories.get(entry.category)
            if parent is None:
                parent = self.tree.insert(
                    "",
                    "end",
                    text=entry.category.title(),
                    open=False,
                )
                categories[entry.category] = parent
            iid = self.tree.insert(
                parent,
                "end",
                text=entry.title or entry.experiment_id,
            )
            self.entries[iid] = entry

        self.detail_var.set(
            f"{len(entries)} experiments · {root if root else 'not found'}"
        )

    def _on_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        entry = self.entries.get(selection[0])
        if entry is None:
            return

        self.selected = entry
        self.title_var.set(entry.title or entry.experiment_id)
        self.protocol_var.set(f"{entry.protocol} · protocol v{entry.protocol_version}")
        self.path_var.set(str(entry.path))
        self.hypothesis_var.set(entry.hypothesis or "—")
        self.criteria_var.set(entry.success_criteria or "—")
        seeds = ", ".join(map(str, entry.seeds)) or "—"
        self.design_var.set(f"{entry.steps:,} ticks · seeds {seeds}")
        self.detail_var.set(entry.experiment_id)

    def run_selected(self) -> None:
        if self.selected is None:
            messagebox.showinfo("Run experiment", "Select an experiment first.")
            return
        try:
            descriptor = self.controller.launch_experiment(self.selected.path)
        except RuntimeError as exc:
            messagebox.showwarning("Run active", str(exc))
            return

        self._apply_descriptor(descriptor)
        self._append_output(f"START · {self.selected.path}\n")
        self.notebook.select(self.output_tab)

    def launch_physics3d(self) -> None:
        try:
            descriptor = self.controller.launch_physics3d()
        except RuntimeError as exc:
            messagebox.showwarning("Run active", str(exc))
            return

        self._apply_descriptor(descriptor)
        self._append_output("START · Physics3D canonical embodiment\n")
        self._mount_physics_workspace()

    def _mount_physics_workspace(self) -> None:
        from .physics3d_monitor import mount_embedded_viewer

        if self.physics_tab is not None:
            try:
                self.notebook.forget(self.physics_tab)
                self.physics_tab.destroy()
            except tk.TclError:
                pass

        self.physics_tab = tk.Frame(self.notebook, bg="#0d1117")
        self.notebook.add(self.physics_tab, text="Body")
        self.notebook.select(self.physics_tab)
        self._set_physics_focus(True)

        try:
            self._physics_cleanup = mount_embedded_viewer(
                self.physics_tab,
                self.controller.physics_frame_queue,
                self.controller.physics_command_queue,
            )
        except Exception as exc:
            self.controller.stop()
            self._append_output(
                f"3D WORKSPACE ERROR · {type(exc).__name__}: {exc}\n"
            )
            for child in self.physics_tab.winfo_children():
                child.destroy()
            tk.Label(
                self.physics_tab,
                text=f"Physics3D unavailable\n{type(exc).__name__}: {exc}",
                bg="#0d1117",
                fg=self.RED,
                font=("TkFixedFont", 10),
            ).pack(fill="both", expand=True)

    def stop_run(self) -> None:
        self.controller.stop()
        self._physics_paused = False
        self.pause_button.configure(text="Pause")
        if self.controller.current is not None:
            self._apply_descriptor(self.controller.current)

    def _apply_descriptor(self, descriptor) -> None:
        self.run_var.set(f"{descriptor.kind.value}: {descriptor.label}")
        self.status_var.set(descriptor.status.value.title())
        self.detail_var.set(descriptor.detail)
        running = descriptor.status.value in {"starting", "running"}
        self.live_dot.configure(fg=self.GREEN if running else self.MUTED)

    def _append_output(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.insert("end", text)
        self.output.see("end")
        self.output.configure(state="disabled")

    def _poll_runs(self) -> None:
        for event in self.controller.poll():
            kind = event.get("type", "event").upper()
            detail = event.get("detail", "")
            self._append_output(f"{kind} · {detail}\n")
            if event.get("traceback"):
                self._append_output(str(event["traceback"]) + "\n")

        if self.controller.current is not None:
            self._apply_descriptor(self.controller.current)
        self.root.after(self.POLL_MS, self._poll_runs)

    def close(self) -> None:
        if self.controller.busy:
            if not messagebox.askyesno(
                "Active run",
                "A scientific run is active. Stop it and exit?",
            ):
                return
            if self._physics_cleanup is not None:
                try:
                    self._physics_cleanup()
                except Exception:
                    pass
            self.controller.stop()
        elif self._physics_cleanup is not None:
            try:
                self._physics_cleanup()
            except Exception:
                pass
        self.root.destroy()
