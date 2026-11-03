"""
bridge.py - connects the Python layer to the C++ computation engine.

Author  : KABWE KENNEDY
Project : Transformer Simulator

Flow:
    Params (Python)  ->  command-line flags  ->  transformer_sim.exe
    transformer_sim.exe  ->  JSON on stdout  ->  Results (Python)

Nothing in this file draws anything. It only talks to the engine, so the GUI
and visualiser never need to know that a subprocess exists.
"""

from __future__ import annotations

import cmath
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants (no magic numbers buried in the code)
# ---------------------------------------------------------------------------

EXE_NAME = "transformer_sim.exe" if sys.platform == "win32" else "transformer_sim"

# This file lives in  <project>/python/bridge.py
#   .parent         -> <project>/python
#   .parent.parent  -> <project>
DEFAULT_EXE_PATH = Path(__file__).resolve().parent.parent / "build" / "bin" / EXE_NAME

TIMEOUT_SECONDS = 5.0

# On Windows, stop a black console window flashing up every time the GUI
# calls the engine. On other platforms the flag does not exist, so use 0.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class EngineError(Exception):
    """Raised for any failure in running or reading the C++ engine."""


# ---------------------------------------------------------------------------
# Input: Params
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Params:
    """
    Inputs for one simulation run. Mirrors TransformerParams.h in C++.

    A dataclass is Python's version of a C++ struct: you declare the fields
    and Python writes the constructor for you.
    frozen=True makes it read-only after creation (like a const struct).
    """
    mode: int = 1
    V1: float = 230.0
    f: float = 50.0
    N1: int = 200
    N2: int = 100
    RL: float = 10.0
    Rc: float = 0.0
    Xm: float = 0.0
    R1: float = 0.0
    R2: float = 0.0
    X1: float = 0.0
    X2: float = 0.0

    def to_args(self) -> list[str]:
        """
        Build the command-line flags for this run.

        Modes are cumulative, so we only send the parameters that belong to
        the selected mode. This is what stops a stale R1 value from leaking
        into a Mode 2 simulation.
        """
        flags: dict[str, float | int] = {
            "mode": self.mode,
            "V1": self.V1, "f": self.f,
            "N1": self.N1, "N2": self.N2, "RL": self.RL,
        }
        if self.mode >= 2:
            flags.update({"Rc": self.Rc, "Xm": self.Xm})
        if self.mode >= 3:
            flags.update({"R1": self.R1, "R2": self.R2})
        if self.mode >= 4:
            flags.update({"X1": self.X1, "X2": self.X2})

        args: list[str] = []
        for name, value in flags.items():
            args += [f"--{name}", str(value)]
        return args


# ---------------------------------------------------------------------------
# Output: Phasor and Results
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Phasor:
    """A rotating-vector quantity: RMS magnitude plus angle relative to V1."""
    magnitude: float
    angle_deg: float

    @property
    def complex(self) -> complex:
        """Same phasor as a Python complex number (handy for plotting)."""
        return cmath.rect(self.magnitude, math.radians(self.angle_deg))


@dataclass(frozen=True)
class Results:
    """Everything the GUI needs. Mirrors TransformerResults.h in C++."""
    mode: int
    turns_ratio: float

    V1: Phasor
    V2: Phasor
    I1: Phasor
    I2: Phasor
    I0: Phasor
    Vm: Phasor

    P_in_W: float
    P_out_W: float
    P_fe_W: float
    P_cu_W: float

    efficiency_pct: float
    power_factor: float
    voltage_reg_pct: float

    mutual_flux_Wb: float
    leakage1_Wb: float
    leakage2_Wb: float

    @classmethod
    def from_json(cls, data: dict) -> "Results":
        """Turn the engine's JSON dictionary into a typed Results object."""
        try:
            ph = data["phasors"]
            pw = data["power"]
            pf = data["performance"]
            fx = data["flux"]

            def phasor(name: str) -> Phasor:
                return Phasor(ph[name]["magnitude"], ph[name]["angle_deg"])

            return cls(
                mode=data["mode"],
                turns_ratio=data["turns_ratio"],
                V1=phasor("V1"), V2=phasor("V2"),
                I1=phasor("I1"), I2=phasor("I2"),
                I0=phasor("I0"), Vm=phasor("Vm"),
                P_in_W=pw["P_in_W"], P_out_W=pw["P_out_W"],
                P_fe_W=pw["P_fe_W"], P_cu_W=pw["P_cu_W"],
                efficiency_pct=pf["efficiency_pct"],
                power_factor=pf["power_factor"],
                voltage_reg_pct=pf["voltage_reg_pct"],
                mutual_flux_Wb=fx["mutual_Wb"],
                leakage1_Wb=fx["leakage1_Wb"],
                leakage2_Wb=fx["leakage2_Wb"],
            )
        except KeyError as missing:
            raise EngineError(f"Engine JSON is missing field {missing}") from missing


# ---------------------------------------------------------------------------
# The bridge itself
# ---------------------------------------------------------------------------

class Engine:
    """Runs the C++ executable and returns parsed results."""

    def __init__(self, exe_path: Path | str = DEFAULT_EXE_PATH) -> None:
        self.exe_path = Path(exe_path)

    def run(self, params: Params) -> Results:
        if not self.exe_path.is_file():
            raise EngineError(
                f"Engine not found at:\n{self.exe_path}\n"
                "Build the C++ project first (cmake --build build)."
            )

        try:
            proc = subprocess.run(
                [str(self.exe_path), *params.to_args()],
                capture_output=True,     # grab stdout and stderr
                text=True,               # decode bytes -> str
                timeout=TIMEOUT_SECONDS,
                creationflags=_NO_WINDOW,
            )
        except subprocess.TimeoutExpired as exc:
            raise EngineError(f"Engine did not finish within {TIMEOUT_SECONDS}s") from exc
        except OSError as exc:
            raise EngineError(f"Could not start engine: {exc}") from exc

        # Exit code 2 = bad command line. The C++ side writes that to stderr.
        if proc.returncode == 2:
            raise EngineError(proc.stderr.strip() or "Engine rejected the arguments")

        # Exit codes 0 and 1 both produce JSON on stdout.
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise EngineError(f"Engine returned invalid JSON: {exc}") from exc

        # Exit code 1 = the engine validated the inputs and rejected them.
        if data.get("status") != "ok":
            raise EngineError(data.get("error", "Unknown engine error"))

        return Results.from_json(data)


# ---------------------------------------------------------------------------
# Self-test:  python bridge.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    engine = Engine()

    base = dict(V1=230.0, f=50.0, N1=200, N2=100, RL=10.0,
                Rc=500.0, Xm=200.0, R1=0.5, R2=0.3, X1=1.2, X2=0.8)

    print(f"Engine: {engine.exe_path}\n")
    print(f"{'Mode':<6}{'V2 (V)':>10}{'I1 (A)':>10}{'P_fe (W)':>11}"
          f"{'P_cu (W)':>11}{'Eff (%)':>10}{'PF':>8}{'VR (%)':>9}")

    for mode in (1, 2, 3, 4):
        r = engine.run(Params(mode=mode, **base))
        print(f"{mode:<6}{r.V2.magnitude:>10.2f}{r.I1.magnitude:>10.3f}"
              f"{r.P_fe_W:>11.2f}{r.P_cu_W:>11.2f}"
              f"{r.efficiency_pct:>10.2f}{r.power_factor:>8.3f}{r.voltage_reg_pct:>9.2f}")

    # Prove error handling works: a negative load resistance must be rejected.
    print("\nError-path check (RL = -5):")
    try:
        engine.run(Params(mode=1, RL=-5.0))
    except EngineError as err:
        print(f"  EngineError caught correctly -> {err}")