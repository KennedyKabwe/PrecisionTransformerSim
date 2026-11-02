"""
gui.py - main application window.

Author  : KABWE KENNEDY
Project : Transformer Simulator

Layout (follows the GUI Design Specification):

    +--------------------------------------------------------------+
    |  Toolbar:  New | Load | Save | Help                           |
    +----------------+---------------------------------------------+
    |  Mode panel    |  Mode description + LED status strip        |
    |  Input fields  |  Tabs: Results | Phasor | Flux & Heat-Map    |
    |  (scrollable)  |                                             |
    +----------------+---------------------------------------------+
    |  Footer:  Run | Pause | Reset     status     Efficiency | PF  |
    +--------------------------------------------------------------+

This file builds the window and reacts to the user. It never does electrical
maths (C++ does that) and never draws plots (scenes.py / visualiser.py do).
The visualiser plugs in through register_listener() and
register_pause_listener().
"""

from __future__ import annotations

import json
import math
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from bridge import Engine, EngineError, Params, Results
from theme import (ACCENT, ACCENT_HOVER, BG, BORDER, ERR, FG, FIELD, FONT,
                   FONT_BIG, FONT_BOLD, FONT_FAMILY, LED_OFF, MUTED, OK,
                   PANEL, WARN)

# ---------------------------------------------------------------------------
# Application identity
# ---------------------------------------------------------------------------

APP_NAME = "Transformer Simulator"
APP_VERSION = "1.0.0"
AUTHOR = "KABWE KENNEDY"
WINDOW_TITLE = f"{APP_NAME} v{APP_VERSION}  |  Developed by {AUTHOR}"

SIDEBAR_WIDTH = 300


# ---------------------------------------------------------------------------
# Parameter table - ONE place that describes every input field
# ---------------------------------------------------------------------------
# Adding a new input later means adding one line here. The GUI builds the
# field, the tooltip, the validation and the mode enable/disable from it.

@dataclass(frozen=True)
class ParamSpec:
    key: str            # must match the field name in bridge.Params
    label: str
    unit: str
    default: float
    min_mode: int       # field is active from this mode upward
    tip: str
    is_int: bool = False
    positive: bool = True   # True: value must be > 0.  False: >= 0 allowed.


PARAM_SPECS: list[ParamSpec] = [
    ParamSpec("V1", "Primary voltage V\u2081", "V", 230.0, 1,
              "RMS voltage applied to the primary winding."),
    ParamSpec("f", "Frequency f", "Hz", 50.0, 1,
              "Supply frequency. For a fixed voltage, higher frequency means "
              "lower core flux (\u03a6 = V / 4.44fN)."),
    ParamSpec("N1", "Primary turns N\u2081", "", 200, 1,
              "Number of turns on the primary winding.", is_int=True),
    ParamSpec("N2", "Secondary turns N\u2082", "", 100, 1,
              "Number of turns on the secondary winding. "
              "Turns ratio a = N\u2081 / N\u2082.", is_int=True),
    ParamSpec("RL", "Load resistance RL", "\u03a9", 10.0, 1,
              "Resistive load on the secondary. A smaller resistance draws "
              "more current from the transformer."),
    ParamSpec("Rc", "Core loss resistance Rc", "\u03a9", 500.0, 2,
              "Models iron losses (hysteresis + eddy currents). A smaller "
              "Rc means MORE core loss. Enter 0 to remove the branch.",
              positive=False),
    ParamSpec("Xm", "Magnetising reactance Xm", "\u03a9", 200.0, 2,
              "Models the magnetising current that establishes the mutual "
              "flux. Enter 0 to remove the branch.", positive=False),
    ParamSpec("R1", "Primary resistance R\u2081", "\u03a9", 0.5, 3,
              "Copper resistance of the primary winding (I\u00b2R loss).",
              positive=False),
    ParamSpec("R2", "Secondary resistance R\u2082", "\u03a9", 0.3, 3,
              "Copper resistance of the secondary winding (I\u00b2R loss).",
              positive=False),
    ParamSpec("X1", "Primary leakage X\u2081", "\u03a9", 1.2, 4,
              "Reactance from primary flux that does NOT link the secondary.",
              positive=False),
    ParamSpec("X2", "Secondary leakage X\u2082", "\u03a9", 0.8, 4,
              "Reactance from secondary flux that does NOT link the primary.",
              positive=False),
]

MODES: dict[int, tuple[str, str]] = {
    1: ("Ideal Transformer",
        "Mode 1 - no losses and perfect magnetic coupling."),
    2: ("Core Losses",
        "Mode 2 - adds hysteresis and eddy-current loss (Rc) and the "
        "magnetising branch (Xm)."),
    3: ("Core + Copper Losses",
        "Mode 3 - adds winding resistance R\u2081 and R\u2082."),
    4: ("Practical Transformer",
        "Mode 4 - adds leakage reactance X\u2081 and X\u2082. The full model."),
}


class InputError(ValueError):
    """A field contains something invalid. Remembers WHICH field."""

    def __init__(self, key: str, message: str) -> None:
        super().__init__(message)
        self.key = key


def _fmt(x: float) -> str:
    """230.0 -> '230',  0.5 -> '0.5'"""
    return f"{x:g}"


# ---------------------------------------------------------------------------
# Small reusable widgets
# ---------------------------------------------------------------------------

class Tooltip:
    """Pop-up help text shown while the mouse is over a widget."""

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _event: tk.Event | None = None) -> None:
        if self.tip is not None:
            return
        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text, justify="left", wraplength=300,
                 bg="#fff8dc", fg="#222222", relief="solid", borderwidth=1,
                 padx=8, pady=5, font=(FONT_FAMILY, 9)).pack()

    def _hide(self, _event: tk.Event | None = None) -> None:
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


class Led(tk.Canvas):
    """LED-style indicator: a coloured circle that is lit or dark."""

    def __init__(self, parent: tk.Widget, colour_on: str) -> None:
        super().__init__(parent, width=18, height=18, bg=PANEL,
                         highlightthickness=0)
        self._colour_on = colour_on
        self._dot = self.create_oval(2, 2, 16, 16, fill=LED_OFF, outline="")

    def set(self, lit: bool) -> None:
        self.itemconfigure(self._dot, fill=self._colour_on if lit else LED_OFF)


class ScrollFrame(ttk.Frame):
    """
    A frame whose content scrolls vertically when it is taller than the window.
    Put your widgets in  .body  (not in the ScrollFrame itself).
    The scrollbar only does something when the content does not fit.
    """

    def __init__(self, parent: tk.Widget, width: int) -> None:
        super().__init__(parent)
        self._canvas = tk.Canvas(self, bg=PANEL, highlightthickness=0,
                                 borderwidth=0, width=width)
        self._bar = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._bar.set)
        self._bar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self.body = ttk.Frame(self._canvas, padding=(2, 2, 6, 2))
        self._window = self._canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", self._on_body_resize)
        self._canvas.bind("<Configure>", self._on_canvas_resize)
        self.bind_all("<MouseWheel>", self._on_wheel, add="+")

    def _on_body_resize(self, _event: tk.Event) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_resize(self, event: tk.Event) -> None:
        self._canvas.itemconfigure(self._window, width=event.width)

    def _on_wheel(self, event: tk.Event) -> None:
        under = self.winfo_containing(event.x_root, event.y_root)
        if under is None or not str(under).startswith(str(self)):
            return                                  # pointer is elsewhere
        if self._canvas.yview() == (0.0, 1.0):
            return                                  # everything already fits
        self._canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")


# ---------------------------------------------------------------------------
# The application window
# ---------------------------------------------------------------------------

class App(tk.Tk):

    def __init__(self) -> None:
        super().__init__()
        self.title(WINDOW_TITLE)
        self._fit_to_screen()
        self.configure(bg=BG)

        self.engine = Engine()
        self.mode_var = tk.IntVar(value=1)
        self.vars: dict[str, tk.StringVar] = {
            s.key: tk.StringVar(value=_fmt(s.default)) for s in PARAM_SPECS
        }
        self.entries: dict[str, ttk.Entry] = {}
        self.last_results: Results | None = None
        self.paused = False

        # The visualiser registers functions here.
        self._listeners: list[Callable[[Params, Results], None]] = []
        self._pause_listeners: list[Callable[[bool], None]] = []

        self._build_style()
        self._build_toolbar()
        self._build_footer()      # packed before the body so it always keeps its space
        self._build_body()

        self._on_mode_change(run=False)
        self.after(150, self.run_simulation)   # show real numbers at start-up

    def _fit_to_screen(self) -> None:
        """Never make the window taller or wider than the screen (laptops!)."""
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = min(1260, sw - 30), min(800, sh - 100)
        self.geometry(f"{w}x{h}+{max((sw - w) // 2, 0)}+8")
        self.minsize(min(980, w), min(600, h))

    # -- public hooks for the visualiser ---------------------------------------

    def register_listener(self, fn: Callable[[Params, Results], None]) -> None:
        """fn(params, results) is called after every successful run."""
        self._listeners.append(fn)

    def register_pause_listener(self, fn: Callable[[bool], None]) -> None:
        """fn(paused) is called when the user presses Pause or Resume."""
        self._pause_listeners.append(fn)

    # -- styling -------------------------------------------------------------

    def _build_style(self) -> None:
        s = ttk.Style(self)
        s.theme_use("clam")

        s.configure(".", background=PANEL, foreground=FG, font=FONT,
                    bordercolor=BORDER, lightcolor=PANEL, darkcolor=PANEL)
        s.configure("TLabelframe", background=PANEL, bordercolor=BORDER)
        s.configure("TLabelframe.Label", background=PANEL, foreground=ACCENT,
                    font=FONT_BOLD)
        s.configure("Muted.TLabel", foreground=MUTED)
        s.configure("Unit.TLabel", foreground=MUTED, font=(FONT_FAMILY, 9))

        s.configure("TEntry", fieldbackground=FIELD, foreground=FG,
                    insertcolor=FG, padding=3)
        s.map("TEntry",
              fieldbackground=[("disabled", BG)],
              foreground=[("disabled", MUTED)])

        s.configure("TButton", background=FIELD, foreground=FG, padding=(12, 6))
        s.map("TButton", background=[("active", BORDER)])

        s.configure("Run.TButton", background=ACCENT, foreground="white",
                    font=FONT_BOLD, padding=(22, 9))
        s.map("Run.TButton", background=[("active", ACCENT_HOVER)])

        s.configure("Mode.Toolbutton", background=FIELD, foreground=FG,
                    padding=(12, 6), anchor="w")
        s.map("Mode.Toolbutton",
              background=[("selected", ACCENT), ("active", BORDER)],
              foreground=[("selected", "white")])

        s.configure("TCheckbutton", background=PANEL, foreground=FG,
                    indicatorbackground=FIELD, indicatorforeground="white")
        s.map("TCheckbutton",
              background=[("active", PANEL)],
              indicatorbackground=[("selected", ACCENT), ("active", BORDER)])

        s.configure("TNotebook", background=PANEL, borderwidth=0)
        s.configure("TNotebook.Tab", background=FIELD, foreground=MUTED,
                    padding=(16, 8))
        s.map("TNotebook.Tab",
              background=[("selected", PANEL)],
              foreground=[("selected", FG)])

        s.configure("Treeview", background=PANEL, fieldbackground=PANEL,
                    foreground=FG, rowheight=27, borderwidth=0)
        s.configure("Treeview.Heading", background=FIELD, foreground=FG,
                    font=FONT_BOLD, padding=6)
        s.map("Treeview", background=[("selected", FIELD)])

        s.configure("Vertical.TScrollbar", background=FIELD, troughcolor=PANEL,
                    bordercolor=PANEL, arrowcolor=FG)
        s.map("Vertical.TScrollbar", background=[("active", BORDER)])

    # -- toolbar ---------------------------------------------------------------

    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self, padding=(10, 8))
        bar.pack(side="top", fill="x")
        for text, command in (("New", self.reset), ("Load", self.load_file),
                              ("Save", self.save_file), ("Help", self.show_about)):
            ttk.Button(bar, text=text, command=command).pack(side="left", padx=(0, 6))
        ttk.Label(bar, text=f"{APP_NAME}  \u00b7  {AUTHOR}",
                  style="Muted.TLabel").pack(side="right")

    # -- body: sidebar + centre ---------------------------------------------------

    def _build_body(self) -> None:
        body = tk.Frame(self, bg=BG)
        body.pack(side="top", fill="both", expand=True, padx=8, pady=8)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        sidebar = ScrollFrame(body, width=SIDEBAR_WIDTH)
        sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 8))
        self._build_mode_panel(sidebar.body)
        self._build_input_panel(sidebar.body)

        centre = tk.Frame(body, bg=BG)
        centre.grid(row=0, column=1, sticky="nsew")
        centre.columnconfigure(0, weight=1)
        centre.rowconfigure(1, weight=1)
        self._build_status_strip(centre)
        self._build_tabs(centre)

    def _build_mode_panel(self, parent: ttk.Frame) -> None:
        box = ttk.LabelFrame(parent, text="Simulation Mode", padding=8)
        box.pack(fill="x")
        for number, (name, _desc) in MODES.items():
            ttk.Radiobutton(box, text=f"{number}   {name}",
                            variable=self.mode_var, value=number,
                            style="Mode.Toolbutton",
                            command=self._on_mode_change
                            ).pack(fill="x", pady=2)

    def _build_input_panel(self, parent: ttk.Frame) -> None:
        box = ttk.LabelFrame(parent, text="Input Parameters", padding=8)
        box.pack(fill="x", pady=(10, 0))
        box.columnconfigure(1, weight=1)

        for row, spec in enumerate(PARAM_SPECS):
            label = ttk.Label(box, text=spec.label)
            label.grid(row=row, column=0, sticky="w", pady=2)
            entry = ttk.Entry(box, textvariable=self.vars[spec.key], width=8,
                              justify="right")
            entry.grid(row=row, column=1, sticky="e", padx=6, pady=2)
            entry.bind("<Return>", lambda _e: self.run_simulation())
            ttk.Label(box, text=spec.unit, style="Unit.TLabel", width=3
                      ).grid(row=row, column=2, sticky="w")
            Tooltip(label, spec.tip)
            Tooltip(entry, spec.tip)
            self.entries[spec.key] = entry

    def _build_status_strip(self, parent: tk.Frame) -> None:
        """Mode description and the three LED indicators, always visible."""
        box = ttk.LabelFrame(parent, text="Model Assumptions", padding=(10, 4, 10, 6))
        box.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.mode_desc = ttk.Label(box, text="", style="Muted.TLabel")
        self.mode_desc.pack(anchor="w", pady=(0, 4))

        row = ttk.Frame(box)
        row.pack(anchor="w")
        self.led_core = Led(row, WARN)
        self.led_copper = Led(row, ERR)
        self.led_leak = Led(row, ACCENT)
        for led, text in ((self.led_core, "Core losses"),
                          (self.led_copper, "Copper losses"),
                          (self.led_leak, "Leakage reactance")):
            led.pack(side="left")
            ttk.Label(row, text=text).pack(side="left", padx=(6, 24))

    def _build_tabs(self, parent: tk.Frame) -> None:
        self.tabs = ttk.Notebook(parent)
        self.tabs.grid(row=1, column=0, sticky="nsew")

        # Tab 1 - numeric results
        results_tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(results_tab, text="Results")
        self.table = ttk.Treeview(results_tab, columns=("quantity", "value"),
                                  show="headings", selectmode="none")
        self.table.heading("quantity", text="Quantity", anchor="w")
        self.table.heading("value", text="Value", anchor="w")
        self.table.column("quantity", width=260, anchor="w")
        self.table.column("value", width=360, anchor="w")
        self.table.pack(fill="both", expand=True)

        # Tabs 2 and 3 - empty frames. visualiser.attach() fills them.
        self.phasor_tab = ttk.Frame(self.tabs, padding=6)
        self.flux_tab = ttk.Frame(self.tabs, padding=6)
        self.tabs.add(self.phasor_tab, text="Phasor Diagram")
        self.tabs.add(self.flux_tab, text="Flux & Heat-Map")

    # -- footer ----------------------------------------------------------------

    def _build_footer(self) -> None:
        foot = ttk.Frame(self, padding=(12, 10))
        foot.pack(side="bottom", fill="x")

        ttk.Button(foot, text="\u25b6  Run", style="Run.TButton",
                   command=self.run_simulation).pack(side="left")
        self.pause_btn = ttk.Button(foot, text="Pause", command=self.toggle_pause)
        self.pause_btn.pack(side="left", padx=(10, 0))
        ttk.Button(foot, text="Reset", command=self.reset
                   ).pack(side="left", padx=10)

        self.status = ttk.Label(foot, text="Ready", style="Muted.TLabel")
        self.status.pack(side="left", padx=16)

        pf_box = ttk.Frame(foot)
        pf_box.pack(side="right", padx=(24, 0))
        ttk.Label(pf_box, text="POWER FACTOR", style="Muted.TLabel").pack(anchor="e")
        self.pf_label = ttk.Label(pf_box, text="\u2014", font=FONT_BIG)
        self.pf_label.pack(anchor="e")

        eff_box = ttk.Frame(foot)
        eff_box.pack(side="right")
        ttk.Label(eff_box, text="EFFICIENCY", style="Muted.TLabel").pack(anchor="e")
        self.eff_label = ttk.Label(eff_box, text="\u2014", font=FONT_BIG)
        self.eff_label.pack(anchor="e")

    # -- pause -----------------------------------------------------------------

    def toggle_pause(self) -> None:
        self._set_paused(not self.paused)

    def _set_paused(self, paused: bool) -> None:
        if paused == self.paused:
            return
        self.paused = paused
        self.pause_btn.configure(text="Resume" if paused else "Pause")
        self._set_status("Paused - animation frozen" if paused else "Running",
                         WARN if paused else OK)
        for fn in self._pause_listeners:
            fn(paused)

    # -- mode switching --------------------------------------------------------

    def _on_mode_change(self, run: bool = True) -> None:
        mode = self.mode_var.get()
        self.mode_desc.configure(text=MODES[mode][1])

        # Enable only the fields that belong to this mode
        for spec in PARAM_SPECS:
            state = "normal" if spec.min_mode <= mode else "disabled"
            self.entries[spec.key].configure(state=state)

        # LEDs describe which physical effects the selected model includes
        self.led_core.set(mode >= 2)
        self.led_copper.set(mode >= 3)
        self.led_leak.set(mode >= 4)

        if run:
            self.run_simulation()

    # -- reading and validating inputs -------------------------------------------

    def _collect_params(self) -> Params:
        mode = self.mode_var.get()
        values: dict[str, float | int] = {}

        for spec in PARAM_SPECS:
            if spec.min_mode > mode:
                continue                      # inactive field: ignore it
            raw = self.vars[spec.key].get().strip()
            name = spec.label

            try:
                number = float(raw)
            except ValueError:
                raise InputError(spec.key, f"{name} must be a number") from None
            if not math.isfinite(number):
                raise InputError(spec.key, f"{name} must be a finite number")

            if spec.is_int:
                if not number.is_integer():
                    raise InputError(spec.key, f"{name} must be a whole number")
                number = int(number)

            if spec.positive and number <= 0:
                raise InputError(spec.key, f"{name} must be greater than zero")
            if not spec.positive and number < 0:
                raise InputError(spec.key, f"{name} cannot be negative")

            values[spec.key] = number

        return Params(mode=mode, **values)

    # -- running the simulation ------------------------------------------------------

    def run_simulation(self) -> None:
        try:
            params = self._collect_params()
            results = self.engine.run(params)
        except InputError as err:
            self._set_status(str(err), ERR)
            self.entries[err.key].focus_set()
            return
        except EngineError as err:
            self._set_status(str(err).splitlines()[0], ERR)
            return

        self.last_results = results
        self._show_results(results)
        self._set_paused(False)               # Run always restarts the animation
        self._set_status("Simulation complete", OK)
        for listener in self._listeners:
            listener(params, results)

    def _show_results(self, r: Results) -> None:
        # Footer metrics
        self.eff_label.configure(text=f"{r.efficiency_pct:.2f} %")
        if abs(r.I1.angle_deg) < 0.05:
            kind = "unity"
        else:
            kind = "lagging" if r.I1.angle_deg < 0 else "leading"
        self.pf_label.configure(text=f"{r.power_factor:.3f}  {kind}")

        # Results table
        def ph(p, unit: str) -> str:
            return f"{p.magnitude:.3f} {unit}  \u2220 {p.angle_deg:.2f}\u00b0"

        rows = [
            ("Turns ratio  a = N\u2081/N\u2082", f"{r.turns_ratio:.3f}"),
            ("Primary voltage  V\u2081", ph(r.V1, "V")),
            ("Secondary voltage  V\u2082", ph(r.V2, "V")),
            ("Core voltage  Vm", ph(r.Vm, "V")),
            ("Primary current  I\u2081", ph(r.I1, "A")),
            ("Secondary current  I\u2082", ph(r.I2, "A")),
            ("Excitation current  I\u2080", ph(r.I0, "A")),
            ("Input power  Pin", f"{r.P_in_W:.2f} W"),
            ("Output power  Pout", f"{r.P_out_W:.2f} W"),
            ("Core loss  Pfe", f"{r.P_fe_W:.2f} W"),
            ("Copper loss  Pcu", f"{r.P_cu_W:.2f} W"),
            ("Efficiency  \u03b7", f"{r.efficiency_pct:.2f} %"),
            ("Voltage regulation  VR", f"{r.voltage_reg_pct:.2f} %"),
            ("Mutual flux  \u03a6m", f"{r.mutual_flux_Wb * 1000:.4f} mWb"),
            ("Primary leakage flux", f"{r.leakage1_Wb * 1000:.4f} mWb"),
            ("Secondary leakage flux", f"{r.leakage2_Wb * 1000:.4f} mWb"),
        ]
        self.table.delete(*self.table.get_children())
        for row in rows:
            self.table.insert("", "end", values=row)

    def _set_status(self, text: str, colour: str) -> None:
        self.status.configure(text=text, foreground=colour)

    # -- toolbar actions ------------------------------------------------------------

    def reset(self) -> None:
        """Back to defaults: mode 1 and every field restored."""
        for spec in PARAM_SPECS:
            self.vars[spec.key].set(_fmt(spec.default))
        self.mode_var.set(1)
        self._on_mode_change()

    def save_file(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save simulation", defaultextension=".json",
            filetypes=[("Simulation file", "*.json")])
        if not path:
            return
        data = {"app": APP_NAME, "version": APP_VERSION,
                "mode": self.mode_var.get(),
                "parameters": {k: v.get() for k, v in self.vars.items()}}
        try:
            Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as err:
            messagebox.showerror("Save failed", str(err))
            return
        self._set_status(f"Saved {Path(path).name}", OK)

    def load_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Load simulation", filetypes=[("Simulation file", "*.json")])
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            mode = int(data["mode"])
            if mode not in MODES:
                raise ValueError(f"unknown mode {mode}")
            stored = data["parameters"]
            for key, var in self.vars.items():
                if key in stored:
                    var.set(str(stored[key]))
        except (OSError, ValueError, KeyError, TypeError) as err:
            messagebox.showerror("Load failed", f"Not a valid simulation file.\n\n{err}")
            return
        self.mode_var.set(mode)
        self._on_mode_change()

    def show_about(self) -> None:
        messagebox.showinfo(
            f"About {APP_NAME}",
            f"{APP_NAME}  v{APP_VERSION}\n\n"
            f"Developed by {AUTHOR}\n\n"
            "Single-phase transformer simulation for electrical machines "
            "students.\nC++ computation engine with a Python interface.")