"""
visualiser.py - puts the drawings from scenes.py into the Tk window.

Author  : KABWE KENNEDY
Project : Transformer Simulator

Three classes:
    PhasorTab   the "Phasor Diagram" tab: figure + option checkboxes + CSV export
    FluxTab     the "Flux & Heat-Map" tab: figure + option checkboxes
    Visualiser  owns the animation clock and connects both tabs to the App

Connection to the rest of the program (no other file needs to change):
    app.register_listener(...)        called after every successful Run
    app.register_pause_listener(...)  called when Pause / Resume is pressed
"""

from __future__ import annotations

import cmath
import csv
import math
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import theme as T
from bridge import Params, Results
from gui import App, Tooltip
from scenes import PhasorScene, TransformerScene

FRAME_MS = 40               # 25 frames per second
CYCLE_SECONDS = 5.0         # one electrical cycle takes 5 s on screen (slow motion)
STATIC_THETA = 0.7          # frozen pose used when animation is switched off


class PhasorTab(ttk.Frame):
    """Phasor diagram with label toggle, referral toggle, animation and export."""

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.labels_var = tk.BooleanVar(value=True)
        self.refer_var = tk.BooleanVar(value=True)
        self.animate_var = tk.BooleanVar(value=False)
        self._res: Results | None = None
        self._theta = 0.0

        bar = ttk.Frame(self)
        bar.pack(side="top", fill="x", pady=(0, 6))
        options = (
            ("Vector labels", self.labels_var, self._redraw,
             "Show or hide the name next to each arrow."),
            ("Refer secondary to primary", self.refer_var, self._redraw,
             "Draw V\u2082 and I\u2082 on the primary side: V\u2082\u2032 = a\u00b7V\u2082, "
             "I\u2082\u2032 = I\u2082/a.\nThen I\u2081 = I\u2080 + I\u2082\u2032 is a real "
             "vector addition."),
            ("Animate rotation", self.animate_var, self._on_animate_toggle,
             "Spin all phasors together. The dotted shadow on the horizontal "
             "axis is the instantaneous value of V\u2081 and I\u2081."),
        )
        for text, var, command, tip in options:
            box = ttk.Checkbutton(bar, text=text, variable=var, command=command)
            box.pack(side="left", padx=(0, 16))
            Tooltip(box, tip)
        export = ttk.Button(bar, text="Export CSV", command=self.export_csv)
        export.pack(side="right")
        Tooltip(export, "Save the plotted phasors (magnitude, angle, real, imaginary) to a CSV file.")

        self.fig = Figure(figsize=(9, 5.4), dpi=100, facecolor=T.PANEL)
        self.scene = PhasorScene(self.fig.add_axes([0.03, 0.05, 0.58, 0.90]))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    # -- called by Visualiser --------------------------------------------------

    def show(self, _params: Params, res: Results) -> None:
        self._res = res
        self._redraw()

    def tick(self, theta: float) -> None:
        self._theta = theta
        if self._res is not None and self.animate_var.get() and self.winfo_ismapped():
            self._redraw()

    # -- internals ---------------------------------------------------------------

    def _on_animate_toggle(self) -> None:
        if not self.animate_var.get():
            self._theta = 0.0                       # back to the standard static diagram
        self._redraw()

    def _redraw(self) -> None:
        if self._res is None:
            return
        animating = self.animate_var.get()
        self.scene.draw(self._res,
                        refer=self.refer_var.get(),
                        labels=self.labels_var.get(),
                        theta=self._theta if animating else 0.0,
                        projections=animating)
        self.canvas.draw_idle()

    def export_csv(self) -> None:
        if not self.scene.entries:
            messagebox.showinfo("Export", "Run a simulation first.")
            return
        path = filedialog.asksaveasfilename(
            title="Export phasors", defaultextension=".csv",
            filetypes=[("CSV file", "*.csv")])
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["quantity", "magnitude", "unit", "angle_deg",
                                 "real", "imag", "referred_to_primary"])
                for e in self.scene.entries:
                    writer.writerow([e.name, f"{abs(e.value):.6f}", e.unit,
                                     f"{math.degrees(cmath.phase(e.value)):.4f}",
                                     f"{e.value.real:.6f}", f"{e.value.imag:.6f}",
                                     self.refer_var.get()])
        except OSError as err:
            messagebox.showerror("Export failed", str(err))


class FluxTab(ttk.Frame):
    """Transformer drawing with flux arrows and the loss heat-map."""

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.heat_var = tk.BooleanVar(value=True)
        self.flux_var = tk.BooleanVar(value=True)
        self.animate_var = tk.BooleanVar(value=True)
        self._theta = STATIC_THETA

        bar = ttk.Frame(self)
        bar.pack(side="top", fill="x", pady=(0, 6))
        options = (
            ("Heat-map", self.heat_var, self._on_option,
             "Colour the core and windings by how much energy they lose,\n"
             "and show heat leaving them. Hotter = a larger share of the input power."),
            ("Flux lines", self.flux_var, self._on_option,
             "Working flux through the core. In Mode 4 also the leakage flux "
             "around each winding."),
            ("Animate", self.animate_var, self._on_animate_toggle,
             "Flux direction reverses every half cycle. Use Pause (bottom bar) to freeze it."),
        )
        for text, var, command, tip in options:
            box = ttk.Checkbutton(bar, text=text, variable=var, command=command)
            box.pack(side="left", padx=(0, 16))
            Tooltip(box, tip)

        self.fig = Figure(figsize=(9, 5.4), dpi=100, facecolor=T.PANEL)
        self.scene = TransformerScene(self.fig)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def show(self, params: Params, res: Results) -> None:
        self.scene.set_data(params, res)
        self.scene.tick(self._theta)
        self.canvas.draw_idle()

    def tick(self, theta: float) -> None:
        if self.animate_var.get():
            self._theta = theta
        if self.scene.has_data and self.animate_var.get() and self.winfo_ismapped():
            self.scene.tick(theta)
            self.canvas.draw_idle()

    def _on_option(self) -> None:
        self.scene.show_heat = self.heat_var.get()
        self.scene.show_flux = self.flux_var.get()
        self.scene.rebuild()
        self.scene.tick(self._theta)
        self.canvas.draw_idle()

    def _on_animate_toggle(self) -> None:
        if not self.animate_var.get():
            self._theta = STATIC_THETA
            self.scene.tick(self._theta)
            self.canvas.draw_idle()


class Visualiser:
    """Owns the animation clock and wires both tabs into the App."""

    def __init__(self, app: App) -> None:
        self.app = app
        self.theta = 0.0
        self.paused = False

        self.phasor = PhasorTab(app.phasor_tab)
        self.phasor.pack(fill="both", expand=True)
        self.flux = FluxTab(app.flux_tab)
        self.flux.pack(fill="both", expand=True)

        app.register_listener(self._on_results)
        app.register_pause_listener(self._on_pause)
        self._loop()

    def _on_results(self, params: Params, res: Results) -> None:
        self.phasor.show(params, res)
        self.flux.show(params, res)

    def _on_pause(self, paused: bool) -> None:
        self.paused = paused

    def _loop(self) -> None:
        try:
            if not self.paused:
                self.theta = (self.theta + 2 * math.pi * FRAME_MS / 1000 / CYCLE_SECONDS) \
                             % (2 * math.pi)
                self.phasor.tick(self.theta)
                self.flux.tick(self.theta)
        except Exception:                       # never let a drawing bug kill the clock
            traceback.print_exc()
        finally:
            self.app.after(FRAME_MS, self._loop)


def attach(app: App) -> Visualiser:
    """Create the visualiser and connect it to the App. Call once, before mainloop()."""
    return Visualiser(app)
