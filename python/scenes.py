"""
scenes.py - all drawing code for the visualiser.

Author  : KABWE KENNEDY
Project : Transformer Simulator

Pure matplotlib. Nothing here knows about Tkinter, so every scene can be
rendered to an image file and tested without opening a window.
visualiser.py embeds these scenes in the GUI and runs the animation clock.

Two scenes:
    PhasorScene       phasor diagram of V1, V2, I1, I2 (+ Vm, I0)
    TransformerScene  core, coils, flux lines and loss heat-map
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass

import numpy as np
from matplotlib.axes import Axes
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LinearSegmentedColormap, Normalize, to_rgb
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Arc, Circle, Rectangle

import theme as T
from bridge import Params, Results

HEAT_CMAP = LinearSegmentedColormap.from_list("heat", T.HEAT_COLOURS)


# ===========================================================================
# PHASOR DIAGRAM
# ===========================================================================

V_RADIUS = 1.0      # length of the longest voltage phasor
I_RADIUS = 0.72     # length of the longest current phasor (separate scale)


@dataclass(frozen=True)
class PhasorEntry:
    name: str           # plain text, used in the CSV export
    label: str          # matplotlib mathtext, used on the plot
    value: complex      # RMS phasor
    unit: str           # "V" or "A"
    colour: str
    dashed: bool = False


def build_entries(res: Results, refer: bool) -> list[PhasorEntry]:
    """
    Decide which phasors to draw.

    refer=True shows the secondary quantities referred to the primary side:
        V2' = a * V2        I2' = I2 / a
    which is how textbooks draw it, because then  I1 = I0 + I2'  is a
    genuine vector addition.
    """
    a = res.turns_ratio if refer else 1.0
    tag = "'" if refer else ""

    v1, vm = res.V1.complex, res.Vm.complex
    entries = [PhasorEntry("V1", r"$V_1$", v1, "V", T.C_V1)]

    if abs(vm - v1) > 1e-6 * max(abs(v1), 1.0):       # only when Z1 drops voltage
        entries.append(PhasorEntry("Vm", r"$V_m$", vm, "V", T.C_VM, dashed=True))

    entries.append(PhasorEntry(f"V2{tag}", rf"$V_2{tag}$", res.V2.complex * a, "V", T.C_V2))
    entries.append(PhasorEntry("I1", r"$I_1$", res.I1.complex, "A", T.C_I1))
    entries.append(PhasorEntry(f"I2{tag}", rf"$I_2{tag}$", res.I2.complex / a, "A", T.C_I2))

    if abs(res.I0.complex) > 1e-9:
        entries.append(PhasorEntry("I0", r"$I_0$", res.I0.complex, "A", T.C_I0))
    return entries


class PhasorScene:
    """Draws the phasor diagram into one matplotlib Axes."""

    def __init__(self, ax: Axes) -> None:
        self.ax = ax
        self.entries: list[PhasorEntry] = []

    def draw(self, res: Results, *, refer: bool = True, labels: bool = True,
             theta: float = 0.0, projections: bool = False) -> None:
        """
        theta       rotation angle in radians. 0 = the usual static diagram.
                    Increasing it spins every phasor together, which is what
                    "alternating" means: the real-axis shadow is the
                    instantaneous value.
        projections draw each tip's shadow on the real axis (for animation).
        """
        ax = self.ax
        ax.clear()
        ax.set_facecolor(T.PANEL)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlim(-1.35, 1.35)
        ax.set_ylim(-1.35, 1.35)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color(T.C_GRID)

        entries = build_entries(res, refer)
        self.entries = entries
        by_name = {e.name: e for e in entries}

        vmax = max(abs(e.value) for e in entries if e.unit == "V") or 1.0
        imax = max(abs(e.value) for e in entries if e.unit == "A") or 1.0
        rot = cmath.exp(1j * theta)

        def tip(e: PhasorEntry) -> complex:
            radius = (V_RADIUS / vmax) if e.unit == "V" else (I_RADIUS / imax)
            return e.value * radius * rot

        # Reference circles and axes
        ax.add_patch(Circle((0, 0), V_RADIUS, fill=False, ec=T.C_GRID, ls=":", lw=1))
        ax.add_patch(Circle((0, 0), I_RADIUS, fill=False, ec=T.C_I1, ls=":", lw=0.8, alpha=0.35))
        ax.axhline(0, color=T.C_GRID, lw=0.8)
        ax.axvline(0, color=T.C_GRID, lw=0.8)

        # Construction lines:  I1 = I0 + I2'  (parallelogram)
        if refer and "I0" in by_name:
            p1 = tip(by_name["I1"])
            for name in ("I0", "I2'"):
                q = tip(by_name[name])
                ax.plot([q.real, p1.real], [q.imag, p1.imag],
                        color=T.C_I1, ls="--", lw=1, alpha=0.55)

        # Arrows
        for e in entries:
            t = tip(e)
            ax.annotate("", xy=(t.real, t.imag), xytext=(0, 0),
                        arrowprops=dict(arrowstyle="-|>", color=e.colour,
                                        lw=1.6 if e.dashed else 2.6,
                                        linestyle="--" if e.dashed else "-",
                                        shrinkA=0, shrinkB=0, mutation_scale=16))
            if projections and e.name in ("V1", "I1"):
                ax.plot([t.real, t.real], [t.imag, 0], color=e.colour, ls=":", lw=1)
                ax.plot(t.real, 0, "o", color=e.colour, ms=5)

        # Labels at the arrow tips. Tips that coincide (always true in Mode 1,
        # where V1 = V2' and I1 = I2') are stacked so the text never overlaps.
        if labels:
            placed: list[complex] = []
            for e in entries:
                t = tip(e)
                direction = t / abs(t) if abs(t) > 1e-9 else 1 + 0j
                anchor = t + 0.09 * direction
                while any(abs(anchor - p) < 0.11 for p in placed):
                    anchor += 0.11j
                placed.append(anchor)
                ax.text(anchor.real, anchor.imag, e.label, color=e.colour,
                        fontsize=13, fontweight="bold", ha="center", va="center")

        # Angle between V1 and I1 (the power-factor angle phi)
        a_v = math.degrees(cmath.phase(tip(by_name["V1"])))
        a_i = math.degrees(cmath.phase(tip(by_name["I1"])))
        d = (a_i - a_v + 180.0) % 360.0 - 180.0
        if abs(d) > 0.5:
            start = a_v if d > 0 else a_v + d
            ax.add_patch(Arc((0, 0), 0.5, 0.5, theta1=start, theta2=start + abs(d),
                             color=T.FG, lw=1.4))

        # Legend with the actual numbers (outside the plot, on the right)
        handles = [
            Line2D([0], [0], color=e.colour, lw=3,
                   label=f"{e.label}   {abs(e.value):.2f} {e.unit}   "
                         f"\u2220 {math.degrees(cmath.phase(e.value)):.1f}\u00b0")
            for e in entries
        ]
        ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.03, 0.66),
                  frameon=True, facecolor=T.PANEL, edgecolor=T.C_GRID,
                  labelcolor=T.FG, fontsize=10, borderpad=0.8)

        phi = res.I1.angle_deg - res.V1.angle_deg
        kind = "unity" if abs(phi) < 0.05 else ("lagging" if phi < 0 else "leading")
        notes = [f"\u03c6 = {abs(phi):.2f}\u00b0     PF = {res.power_factor:.3f} {kind}"]
        if kind != "unity":
            notes.append(f"I\u2081 {kind} V\u2081")
        if refer:
            notes.append("Secondary referred to primary:")
            notes.append("V\u2082\u2032 = a\u00b7V\u2082,   I\u2082\u2032 = I\u2082 / a")
            if "I0" in by_name:
                notes.append("Dashed: I\u2081 = I\u2080 + I\u2082\u2032")
        notes.append(f"Solid circle = {vmax:.1f} V")
        notes.append(f"Faint circle = {imax:.2f} A")
        ax.text(1.03, 0.36, "\n".join(notes), transform=ax.transAxes,
                color=T.MUTED, fontsize=9.5, va="top", linespacing=1.5)


# ===========================================================================
# TRANSFORMER: core, coils, flux and heat
# ===========================================================================

# Geometry in drawing units. The core is a rectangular ring:
CORE_W, CORE_H = 10.0, 7.0
WIN_X0, WIN_Y0, WIN_X1, WIN_Y1 = 3.0, 1.5, 7.0, 5.5     # window (the hole)
CENTRE = (5.0, 3.5)
COIL1 = (-0.55, 1.9, 4.10, 3.2)                          # x, y, width, height
COIL2 = (6.45, 1.9, 4.10, 3.2)

# Flux loop centrelines (half-width, half-height of each rounded rectangle).
# Each must lie inside the core ring: 2 < hx < 5 and 2 < hy < 3.5
MUTUAL_LOOPS = [(2.5, 2.35), (3.5, 2.75), (4.5, 3.15)]
# Leakage loops: (x inside the limb, x outside in the air, half-height)
LEAK_LOOPS = [(0.8, -0.5, 2.0), (1.5, -1.0, 2.4), (2.2, -1.5, 2.8)]

# How much loss counts as "fully hot". Colours are relative to input power
# so a bigger share lost as heat looks hotter.
CORE_FULL_FRACTION = 0.10       # core loss = 10 % of P_in  -> fully hot core
COIL_FULL_FRACTION = 0.05       # winding loss = 5 % of P_in -> fully hot coil

# Leakage flux is only ~1-3 % of mutual flux: invisible if drawn to scale.
LEAK_MIN_VISUAL = 0.35          # leakage arrows never shrink below this
LEAK_REF_FRACTION = 0.05        # leakage at 5 % of mutual -> full-size arrows

MUTUAL_ARROW = 0.60
LEAK_ARROW = 0.45


def _rounded_rect(cx: float, cy: float, hx: float, hy: float, r: float,
                  arc_points: int = 14) -> np.ndarray:
    """Closed CLOCKWISE rounded-rectangle path: up the left side, right along the top."""
    r = min(r, hx, hy)

    def arc(x0: float, y0: float, a0: float, a1: float) -> np.ndarray:
        t = np.linspace(a0, a1, arc_points)
        return np.column_stack((x0 + r * np.cos(t), y0 + r * np.sin(t)))

    pieces = [
        np.array([[cx - hx + r, cy + hy], [cx + hx - r, cy + hy]]),   # top      ->
        arc(cx + hx - r, cy + hy - r, math.pi / 2, 0.0),               # top-right
        np.array([[cx + hx, cy + hy - r], [cx + hx, cy - hy + r]]),   # right    down
        arc(cx + hx - r, cy - hy + r, 0.0, -math.pi / 2),              # bottom-right
        np.array([[cx + hx - r, cy - hy], [cx - hx + r, cy - hy]]),   # bottom   <-
        arc(cx - hx + r, cy - hy + r, -math.pi / 2, -math.pi),         # bottom-left
        np.array([[cx - hx, cy - hy + r], [cx - hx, cy + hy - r]]),   # left     up
        arc(cx - hx + r, cy + hy - r, math.pi, math.pi / 2),           # top-left
    ]
    path = np.vstack(pieces)
    return np.vstack([path, path[:1]])


def _resample(path: np.ndarray, count: int, offset: float = 0.0
              ) -> tuple[np.ndarray, np.ndarray]:
    """Return `count` evenly spaced points on a closed path and the unit tangent at each."""
    seg = np.diff(path, axis=0)
    seg_len = np.hypot(seg[:, 0], seg[:, 1])
    cum = np.concatenate(([0.0], np.cumsum(seg_len)))
    total = cum[-1]
    s = (np.arange(count) / count + offset) % 1.0 * total
    x = np.interp(s, cum, path[:, 0])
    y = np.interp(s, cum, path[:, 1])
    idx = np.clip(np.searchsorted(cum, s, side="right") - 1, 0, len(seg) - 1)
    tangent = seg[idx] / np.maximum(seg_len[idx], 1e-12)[:, None]
    return np.column_stack((x, y)), tangent


def _core_heat_field(nx: int = 300, ny: int = 210) -> np.ndarray:
    """
    Relative loss density across the core, 0..1, NaN inside the window.

    Flux density B is higher where the magnetic path is shorter (the inner
    edge of the ring), and core loss density goes as B squared.
    """
    xs = np.linspace(0, CORE_W, nx)
    ys = np.linspace(0, CORE_H, ny)
    X, Y = np.meshgrid(xs, ys)
    half_w = (WIN_X1 - WIN_X0) / 2.0
    half_h = (WIN_Y1 - WIN_Y0) / 2.0
    s = np.maximum(np.abs(X - CENTRE[0]) / half_w, np.abs(Y - CENTRE[1]) / half_h)
    field = (1.0 / np.maximum(s, 1.0)) ** 2
    field /= field.max()
    in_window = (X > WIN_X0) & (X < WIN_X1) & (Y > WIN_Y0) & (Y < WIN_Y1)
    field[in_window] = np.nan
    return field


def _coil_colour(level: float) -> tuple[float, float, float]:
    """Copper when cold, blending toward hot orange/yellow as loss rises."""
    base = np.array(to_rgb(T.C_COPPER))
    hot = np.array(HEAT_CMAP(0.55 + 0.45 * level)[:3])
    return tuple(base * (1.0 - level) + hot * level)


def _sample_points(rng: np.random.Generator, n: int, rect: tuple[float, float, float, float],
                   exclude_window: bool) -> np.ndarray:
    """n random points inside rect=(x0, y0, x1, y1), optionally outside the core window."""
    out = np.empty((0, 2))
    while len(out) < n:
        pts = np.column_stack((rng.uniform(rect[0], rect[2], 4 * n),
                               rng.uniform(rect[1], rect[3], 4 * n)))
        if exclude_window:
            inside = ((pts[:, 0] > WIN_X0) & (pts[:, 0] < WIN_X1) &
                      (pts[:, 1] > WIN_Y0) & (pts[:, 1] < WIN_Y1))
            pts = pts[~inside]
        out = np.vstack((out, pts))
    return out[:n]


class TransformerScene:
    """
    The transformer drawing.

    set_data() builds the static picture (core, coils, heat-map, flux paths).
    tick(theta) moves only the animated parts: the flux arrows (which flip
    direction every half cycle) and the heat particles leaving the core.
    """

    def __init__(self, fig: Figure) -> None:
        self.fig = fig
        self.ax = fig.add_axes([0.01, 0.02, 0.88, 0.96])
        self.cax = fig.add_axes([0.915, 0.24, 0.02, 0.52])
        self.show_heat = True
        self.show_flux = True

        cb = fig.colorbar(ScalarMappable(Normalize(0, 1), HEAT_CMAP), cax=self.cax)
        cb.set_ticks([0, 1])
        cb.set_ticklabels(["cool", "hot"])
        cb.ax.tick_params(colors=T.MUTED, labelsize=9)
        cb.outline.set_edgecolor(T.C_GRID)
        cb.set_label("Relative loss", color=T.MUTED, fontsize=9)

        self._params: Params | None = None
        self._res: Results | None = None
        self._q_mutual = None
        self._q_leak1 = None
        self._q_leak2 = None
        self._heat = None

    @property
    def has_data(self) -> bool:
        return self._res is not None

    def set_data(self, params: Params, res: Results) -> None:
        self._params, self._res = params, res
        self.rebuild()

    # -- static picture ------------------------------------------------------

    def rebuild(self) -> None:
        if self._res is None or self._params is None:
            return
        p, r = self._params, self._res
        ax = self.ax
        ax.clear()
        ax.axis("off")
        self._q_mutual = self._q_leak1 = self._q_leak2 = self._heat = None

        mode = r.mode
        p_in = max(r.P_in_W, 1e-9)

        # Loss levels 0..1 (0 = cold)
        core_level = min(1.0, r.P_fe_W / (CORE_FULL_FRACTION * p_in)) if mode >= 2 else 0.0
        cu1 = r.I1.magnitude ** 2 * p.R1 if mode >= 3 else 0.0
        cu2 = r.I2.magnitude ** 2 * p.R2 if mode >= 3 else 0.0
        level1 = min(1.0, cu1 / (COIL_FULL_FRACTION * p_in))
        level2 = min(1.0, cu2 / (COIL_FULL_FRACTION * p_in))
        if not self.show_heat:
            core_level = level1 = level2 = 0.0

        # Core with heat-map
        cmap = HEAT_CMAP.copy()
        cmap.set_bad((0, 0, 0, 0))                    # window stays transparent
        ax.imshow(_core_heat_field() * core_level, extent=(0, CORE_W, 0, CORE_H),
                  origin="lower", cmap=cmap, vmin=0, vmax=1,
                  interpolation="bilinear", zorder=1)
        ax.add_patch(Rectangle((0, 0), CORE_W, CORE_H, fill=False,
                               ec=T.C_CORE_EDGE, lw=1.8, zorder=3))
        ax.add_patch(Rectangle((WIN_X0, WIN_Y0), WIN_X1 - WIN_X0, WIN_Y1 - WIN_Y0,
                               fill=False, ec=T.C_CORE_EDGE, lw=1.8, zorder=3))

        # Coils
        for rect, level in ((COIL1, level1), (COIL2, level2)):
            x, y, w, h = rect
            ax.add_patch(Rectangle((x, y), w, h, fc=_coil_colour(level),
                                   ec=T.C_CORE_EDGE, lw=1.2, alpha=0.95, zorder=4))
            for yy in np.linspace(y + 0.15, y + h - 0.15, 12):
                ax.plot([x, x + w], [yy, yy], color=(0, 0, 0, 0.35), lw=1, zorder=5)

        ax.text(1.5, 7.3, f"Primary   N\u2081 = {p.N1}", color=T.FG, fontsize=11,
                fontweight="bold", ha="center", va="bottom")
        ax.text(8.5, 7.3, f"Secondary   N\u2082 = {p.N2}", color=T.FG, fontsize=11,
                fontweight="bold", ha="center", va="bottom")
        ax.text(1.5, -0.45, rf"$V_1$ = {r.V1.magnitude:.1f} V", color=T.C_V1,
                fontsize=11, fontweight="bold", ha="center", va="top")
        ax.text(8.5, -0.45, rf"$V_2$ = {r.V2.magnitude:.1f} V", color=T.C_V2,
                fontsize=11, fontweight="bold", ha="center", va="top")

        # Flux paths and arrows
        legend: list[Line2D] = []
        if self.show_flux:
            self._build_flux(ax, r)
            legend.append(Line2D([0], [0], color=T.C_FLUX, lw=2.5, label="Mutual (working) flux"))
            if self._q_leak1 is not None:
                legend.append(Line2D([0], [0], color=T.C_LEAK, lw=2.5, label="Leakage flux"))
        if legend:
            ax.legend(handles=legend, loc="upper center", bbox_to_anchor=(0.5, 1.0),
                      ncol=len(legend), frameon=False, labelcolor=T.FG, fontsize=10)

        # Heat particles leaving the hot parts
        if self.show_heat:
            self._build_heat(ax, core_level, level1, level2)

        # Caption
        lines: list[str] = []
        if mode == 1:
            lines.append("Ideal transformer: no losses, all input power reaches the load.")
        if mode >= 2:
            lines.append(f"Core loss  P_fe = {r.P_fe_W:.1f} W   "
                         f"({100 * r.P_fe_W / p_in:.1f} % of input)")
        if mode >= 3:
            lines.append(f"Copper loss  P_cu = {r.P_cu_W:.1f} W   "
                         f"({100 * r.P_cu_W / p_in:.1f} % of input)")
        if mode >= 4:
            lines.append("Leakage flux is exaggerated so that it is visible.")
        ax.text(5.0, -1.05, "\n".join(lines), color=T.MUTED, fontsize=10,
                ha="center", va="top", linespacing=1.6)

        ax.set_aspect("equal")
        ax.set_xlim(-2.4, 12.4)
        ax.set_ylim(-2.5, 8.7)

    def _build_flux(self, ax: Axes, r: Results) -> None:
        # Mutual flux: rounded loops through the core, arrows on each loop
        pos, tan = [], []
        for hx, hy in MUTUAL_LOOPS:
            path = _rounded_rect(CENTRE[0], CENTRE[1], hx, hy, r=0.6)
            ax.plot(path[:, 0], path[:, 1], color=T.C_FLUX, lw=0.9, alpha=0.35, zorder=2)
            p_, t_ = _resample(path, 10, offset=0.02)
            pos.append(p_)
            tan.append(t_)
        self._m_pos = np.vstack(pos)
        self._m_tan = np.vstack(tan)
        z = np.zeros(len(self._m_pos))
        self._q_mutual = ax.quiver(self._m_pos[:, 0], self._m_pos[:, 1], z, z,
                                   angles="xy", scale_units="xy", scale=1,
                                   color=T.C_FLUX, width=0.007, headwidth=4.2,
                                   headlength=5, headaxislength=4.4,
                                   pivot="mid", zorder=6)

        # Phases: flux lags the core voltage by 90 degrees; leakage follows
        # its own winding current (secondary opposes the primary, hence +pi).
        self._phase_m = cmath.phase(r.Vm.complex) - math.pi / 2
        self._phase_1 = cmath.phase(r.I1.complex)
        self._phase_2 = cmath.phase(r.I2.complex) + math.pi

        # Leakage flux: only in Mode 4
        if r.mode < 4:
            return
        self._amp_1 = self._leak_visual(r.leakage1_Wb, r.mutual_flux_Wb)
        self._amp_2 = self._leak_visual(r.leakage2_Wb, r.mutual_flux_Wb)
        if self._amp_1 == 0.0 and self._amp_2 == 0.0:
            return

        pos1, tan1, pos2, tan2 = [], [], [], []
        t_line = np.linspace(0, 2 * math.pi, 200)
        t_arr = np.linspace(0, 2 * math.pi, 8, endpoint=False) + 0.2
        for x_in, x_out, b in LEAK_LOOPS:
            cx, a = (x_in + x_out) / 2.0, (x_in - x_out) / 2.0
            for side in (1, 2):
                cxs = cx if side == 1 else CORE_W - cx
                ax.plot(cxs + a * np.cos(t_line), CENTRE[1] + b * np.sin(t_line),
                        color=T.C_LEAK, lw=0.9, ls="--", alpha=0.5, zorder=2)
                pts = np.column_stack((cxs + a * np.cos(t_arr), CENTRE[1] + b * np.sin(t_arr)))
                tg = np.column_stack((-a * np.sin(t_arr), b * np.cos(t_arr)))
                tg /= np.hypot(tg[:, 0], tg[:, 1])[:, None]
                (pos1 if side == 1 else pos2).append(pts)
                (tan1 if side == 1 else tan2).append(tg)
        self._l1_pos, self._l1_tan = np.vstack(pos1), np.vstack(tan1)
        self._l2_pos, self._l2_tan = np.vstack(pos2), np.vstack(tan2)
        kw = dict(angles="xy", scale_units="xy", scale=1, color=T.C_LEAK, width=0.006,
                  headwidth=4.2, headlength=5, headaxislength=4.4, pivot="mid", zorder=6)
        z1, z2 = np.zeros(len(self._l1_pos)), np.zeros(len(self._l2_pos))
        self._q_leak1 = ax.quiver(self._l1_pos[:, 0], self._l1_pos[:, 1], z1, z1, **kw)
        self._q_leak2 = ax.quiver(self._l2_pos[:, 0], self._l2_pos[:, 1], z2, z2, **kw)

    @staticmethod
    def _leak_visual(leak: float, mutual: float) -> float:
        if leak <= 0.0:
            return 0.0
        ratio = leak / (LEAK_REF_FRACTION * max(mutual, 1e-12))
        return LEAK_MIN_VISUAL + (1.0 - LEAK_MIN_VISUAL) * min(1.0, ratio)

    def _build_heat(self, ax: Axes, core_level: float, level1: float, level2: float) -> None:
        rng = np.random.default_rng(7)
        origins, dirs, levels, colours, reach = [], [], [], [], []

        def add(pts: np.ndarray, direction: np.ndarray, level: float, colour_at: float, dist: float):
            if level < 0.02:
                return
            n = len(pts)
            origins.append(pts)
            dirs.append(direction)
            levels.append(np.full(n, level))
            colours.append(np.tile(HEAT_CMAP(colour_at)[:3], (n, 1)))
            reach.append(np.full(n, dist))

        core = _sample_points(rng, 90, (0, 0, CORE_W, CORE_H), exclude_window=True)
        radial = core - np.array(CENTRE)
        radial /= np.maximum(np.hypot(radial[:, 0], radial[:, 1]), 1e-9)[:, None]
        add(core, radial, core_level, 0.85, 1.4)

        for (x, y, w, h), axis_x, level in ((COIL1, 1.5, level1), (COIL2, 8.5, level2)):
            pts = _sample_points(rng, 45, (x, y, x + w, y + h), exclude_window=False)
            d = np.column_stack((np.sign(pts[:, 0] - axis_x + 1e-6),
                                 0.35 * rng.uniform(-1, 1, len(pts))))
            d /= np.hypot(d[:, 0], d[:, 1])[:, None]
            add(pts, d, level, 0.7, 1.1)

        if not origins:
            return
        self._h_origin = np.vstack(origins)
        self._h_dir = np.vstack(dirs)
        self._h_level = np.concatenate(levels)
        self._h_rgb = np.vstack(colours)
        self._h_reach = np.concatenate(reach)
        self._h_phase = rng.uniform(0, 1, len(self._h_origin))
        rgba = np.column_stack((self._h_rgb, np.zeros(len(self._h_origin))))
        self._heat = ax.scatter(self._h_origin[:, 0], self._h_origin[:, 1], s=26,
                                c=rgba, linewidths=0, zorder=8)

    # -- animation ------------------------------------------------------------

    def tick(self, theta: float) -> None:
        """Move the flux arrows and heat particles to time-angle theta (radians)."""
        if self._res is None:
            return

        if self._q_mutual is not None:
            m = math.cos(theta + self._phase_m)
            self._q_mutual.set_UVC(self._m_tan[:, 0] * MUTUAL_ARROW * m,
                                   self._m_tan[:, 1] * MUTUAL_ARROW * m)
        if self._q_leak1 is not None:
            k1 = self._amp_1 * math.cos(theta + self._phase_1)
            k2 = self._amp_2 * math.cos(theta + self._phase_2)
            self._q_leak1.set_UVC(self._l1_tan[:, 0] * LEAK_ARROW * k1,
                                  self._l1_tan[:, 1] * LEAK_ARROW * k1)
            self._q_leak2.set_UVC(self._l2_tan[:, 0] * LEAK_ARROW * k2,
                                  self._l2_tan[:, 1] * LEAK_ARROW * k2)

        if self._heat is not None:
            u = (self._h_phase + theta / (2 * math.pi)) % 1.0       # 0 = just born, 1 = gone
            pos = self._h_origin + self._h_dir * (self._h_reach * u)[:, None]
            alpha = self._h_level * (1.0 - u) ** 1.2
            self._heat.set_offsets(pos)
            self._heat.set_facecolor(np.column_stack((self._h_rgb, alpha)))
