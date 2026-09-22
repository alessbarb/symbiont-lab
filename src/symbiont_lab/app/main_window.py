from __future__ import annotations
import tkinter as tk
from tkinter import messagebox, ttk
from .discovery import discover_experiments, find_experiments_root
from .models import ExperimentEntry
from .run_controller import RunController

class SymbiontLabWindow:
    POLL_MS = 150
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Symbiont Lab")
        root.geometry("1500x900")
        root.minsize(1100,700)
        self.controller = RunController()
        self.entries: dict[str, ExperimentEntry] = {}
        self.selected: ExperimentEntry | None = None
        self.physics_tab = None
        self._physics_cleanup = None
        self.status_var = tk.StringVar(value="READY")
        self.run_var = tk.StringVar(value="No active run")
        self.detail_var = tk.StringVar(value="Select an experiment or launch Physics3D.")
        self._configure_style()
        self._build_menu()
        self._build_toolbar()
        self._build_workspace()
        self._build_statusbar()
        self.refresh_experiments()
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(self.POLL_MS, self._poll_runs)

    def _configure_style(self) -> None:
        style=ttk.Style(self.root)
        try: style.theme_use("clam")
        except tk.TclError: pass
        style.configure("Toolbar.TFrame",padding=(8,6))
        style.configure("Title.TLabel",font=("TkDefaultFont",13,"bold"))
        style.configure("Section.TLabel",font=("TkDefaultFont",9,"bold"))

    def _build_menu(self) -> None:
        menu=tk.Menu(self.root)
        file_menu=tk.Menu(menu,tearoff=False)
        file_menu.add_command(label="Refresh experiments",command=self.refresh_experiments)
        file_menu.add_separator(); file_menu.add_command(label="Exit",command=self.close)
        menu.add_cascade(label="File",menu=file_menu)
        run_menu=tk.Menu(menu,tearoff=False)
        run_menu.add_command(label="Run selected experiment",command=self.run_selected)
        run_menu.add_command(label="Launch Physics3D",command=self.launch_physics3d)
        run_menu.add_separator(); run_menu.add_command(label="Stop active run",command=self.stop_run)
        menu.add_cascade(label="Run",menu=run_menu)
        view_menu=tk.Menu(menu,tearoff=False)
        view_menu.add_command(label="Experiments",command=lambda:self.notebook.select(self.experiment_tab))
        view_menu.add_command(label="Output",command=lambda:self.notebook.select(self.output_tab))
        menu.add_cascade(label="View",menu=view_menu)
        help_menu=tk.Menu(menu,tearoff=False)
        help_menu.add_command(label="About",command=lambda:messagebox.showinfo(
            "Symbiont Lab","Symbiont Lab scientific workbench\nExperiments and Physics3D"))
        menu.add_cascade(label="Help",menu=help_menu)
        self.root.configure(menu=menu)

    def _build_toolbar(self) -> None:
        bar=ttk.Frame(self.root,style="Toolbar.TFrame"); bar.pack(fill="x")
        ttk.Label(bar,text="SYMBIONT LAB",style="Title.TLabel").pack(side="left",padx=(0,18))
        ttk.Button(bar,text="▶ Run experiment",command=self.run_selected).pack(side="left",padx=3)
        ttk.Button(bar,text="3D Physics",command=self.launch_physics3d).pack(side="left",padx=3)
        ttk.Button(bar,text="■ Stop",command=self.stop_run).pack(side="left",padx=3)
        ttk.Separator(bar,orient="vertical").pack(side="left",fill="y",padx=8)
        ttk.Button(bar,text="↻ Refresh",command=self.refresh_experiments).pack(side="left",padx=3)
        ttk.Label(bar,textvariable=self.run_var).pack(side="right",padx=8)

    def _build_workspace(self) -> None:
        outer=ttk.Panedwindow(self.root,orient="horizontal"); outer.pack(fill="both",expand=True)
        left=ttk.Frame(outer,padding=8); outer.add(left,weight=1)
        ttk.Label(left,text="EXPERIMENTS",style="Section.TLabel").pack(fill="x",pady=(0,6))
        self.tree=ttk.Treeview(left,show="tree",selectmode="browse"); self.tree.pack(fill="both",expand=True)
        self.tree.bind("<<TreeviewSelect>>",self._on_select)
        ttk.Label(left,text="Declarative experiment.toml catalogue").pack(fill="x",pady=(6,0))

        center=ttk.Frame(outer); outer.add(center,weight=4)
        self.notebook=ttk.Notebook(center); self.notebook.pack(fill="both",expand=True)
        self.experiment_tab=ttk.Frame(self.notebook,padding=16)
        self.output_tab=ttk.Frame(self.notebook,padding=10)
        self.notebook.add(self.experiment_tab,text="Experiment"); self.notebook.add(self.output_tab,text="Output")
        self.title_var=tk.StringVar(value="Symbiont Lab")
        self.protocol_var=tk.StringVar(value="Select an experiment from the explorer.")
        self.path_var=tk.StringVar(); self.hypothesis_var=tk.StringVar(); self.criteria_var=tk.StringVar(); self.design_var=tk.StringVar()
        ttk.Label(self.experiment_tab,textvariable=self.title_var,style="Title.TLabel").pack(anchor="w")
        ttk.Label(self.experiment_tab,textvariable=self.protocol_var).pack(anchor="w",pady=(4,12))
        ttk.Separator(self.experiment_tab).pack(fill="x",pady=(0,12))
        self._detail_row("Design",self.design_var); self._detail_row("Hypothesis",self.hypothesis_var)
        self._detail_row("Success criteria",self.criteria_var); self._detail_row("Spec",self.path_var)
        actions=ttk.Frame(self.experiment_tab); actions.pack(fill="x",pady=18)
        ttk.Button(actions,text="▶ Run this experiment",command=self.run_selected).pack(side="left")
        ttk.Button(actions,text="Launch canonical Physics3D",command=self.launch_physics3d).pack(side="left",padx=8)
        ttk.Label(self.output_tab,text="RUN OUTPUT",style="Section.TLabel").pack(anchor="w")
        self.output=tk.Text(self.output_tab,wrap="word",height=20); self.output.pack(fill="both",expand=True,pady=(6,0))
        self.output.configure(state="disabled")

        right=ttk.Frame(outer,padding=10); outer.add(right,weight=1)
        ttk.Label(right,text="INSPECTOR",style="Section.TLabel").pack(fill="x")
        ttk.Separator(right).pack(fill="x",pady=6)
        for title,var in (("Run",self.run_var),("Status",self.status_var),("Detail",self.detail_var)):
            ttk.Label(right,text=title).pack(anchor="w")
            ttk.Label(right,textvariable=var,wraplength=250).pack(anchor="w",pady=(2,10))

    def _detail_row(self,title: str,variable: tk.StringVar) -> None:
        frame=ttk.Frame(self.experiment_tab); frame.pack(fill="x",pady=7)
        ttk.Label(frame,text=title,style="Section.TLabel",width=18).pack(side="left",anchor="n")
        ttk.Label(frame,textvariable=variable,wraplength=760,justify="left").pack(side="left",fill="x",expand=True)

    def _build_statusbar(self) -> None:
        bar=ttk.Frame(self.root,padding=(8,4)); bar.pack(fill="x")
        ttk.Label(bar,textvariable=self.status_var).pack(side="left")
        ttk.Label(bar,textvariable=self.detail_var).pack(side="right")

    def refresh_experiments(self) -> None:
        self.tree.delete(*self.tree.get_children()); self.entries.clear()
        root=find_experiments_root(); entries=discover_experiments(root); categories={}
        for entry in entries:
            parent=categories.get(entry.category)
            if parent is None:
                parent=self.tree.insert("","end",text=entry.category,open=False); categories[entry.category]=parent
            iid=self.tree.insert(parent,"end",text=entry.title or entry.experiment_id); self.entries[iid]=entry
        self.detail_var.set(f"{len(entries)} experiments · {root if root else 'not found'}")

    def _on_select(self,_event=None) -> None:
        selection=self.tree.selection()
        if not selection: return
        entry=self.entries.get(selection[0])
        if entry is None: return
        self.selected=entry
        self.title_var.set(entry.title or entry.experiment_id)
        self.protocol_var.set(f"{entry.protocol} · protocol v{entry.protocol_version}")
        self.path_var.set(str(entry.path)); self.hypothesis_var.set(entry.hypothesis or "—")
        self.criteria_var.set(entry.success_criteria or "—")
        self.design_var.set(f"{entry.steps:,} steps/ticks · seeds: {', '.join(map(str,entry.seeds)) or '—'}")
        self.detail_var.set(entry.experiment_id)

    def run_selected(self) -> None:
        if self.selected is None:
            messagebox.showinfo("Run experiment","Select an experiment first."); return
        try: descriptor=self.controller.launch_experiment(self.selected.path)
        except RuntimeError as exc: messagebox.showwarning("Run active",str(exc)); return
        self._apply_descriptor(descriptor); self._append_output(f"START experiment · {self.selected.path}\n")
        self.notebook.select(self.output_tab)

    def launch_physics3d(self) -> None:
        try:
            descriptor=self.controller.launch_physics3d()
        except RuntimeError as exc:
            messagebox.showwarning("Run active",str(exc))
            return
        self._apply_descriptor(descriptor)
        self._append_output("START Physics3D · canonical embodiment\n")
        self._mount_physics_workspace()

    def _mount_physics_workspace(self) -> None:
        import tkinter as tk
        from .physics3d_monitor import mount_embedded_viewer

        if self.physics_tab is not None:
            try:
                self.notebook.forget(self.physics_tab)
                self.physics_tab.destroy()
            except tk.TclError:
                pass
        self.physics_tab = tk.Frame(self.notebook, bg="#0d1117")
        self.notebook.add(self.physics_tab, text="3D Body")
        self.notebook.select(self.physics_tab)
        try:
            self._physics_cleanup = mount_embedded_viewer(
                self.physics_tab,
                self.controller.physics_frame_queue,
                self.controller.physics_command_queue,
            )
        except Exception as exc:
            self.controller.stop()
            self._append_output(f"3D WORKSPACE ERROR · {type(exc).__name__}: {exc}\n")
            for child in self.physics_tab.winfo_children():
                child.destroy()
            tk.Label(
                self.physics_tab,
                text=f"No se pudo montar Physics3D\n{type(exc).__name__}: {exc}",
                bg="#0d1117",
                fg="#f87171",
                font=("TkFixedFont", 10),
            ).pack(fill="both", expand=True)

    def stop_run(self) -> None:
        self.controller.stop()
        if self.controller.current is not None: self._apply_descriptor(self.controller.current)

    def _apply_descriptor(self,descriptor) -> None:
        self.run_var.set(f"{descriptor.kind.value}: {descriptor.label}")
        self.status_var.set(descriptor.status.value.upper()); self.detail_var.set(descriptor.detail)

    def _append_output(self,text: str) -> None:
        self.output.configure(state="normal"); self.output.insert("end",text); self.output.see("end"); self.output.configure(state="disabled")

    def _poll_runs(self) -> None:
        for event in self.controller.poll():
            self._append_output(f"{event.get('type','event').upper()} · {event.get('detail','')}\n")
            if event.get("traceback"): self._append_output(str(event["traceback"])+"\n")
        if self.controller.current is not None: self._apply_descriptor(self.controller.current)
        self.root.after(self.POLL_MS,self._poll_runs)

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
