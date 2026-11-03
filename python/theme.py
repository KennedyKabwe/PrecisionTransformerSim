"""
theme.py - colours and fonts shared by the whole application.

Author : KABWE KENNEDY

No GUI or plotting code lives here, so any module can import it.
Change the look of the entire app by editing this one file.
"""

# --- Window palette ---------------------------------------------------------
BG = "#171a1f"          # window background (visible in the gaps)
PANEL = "#22262d"       # panels and plot backgrounds
FIELD = "#2d323b"       # entry boxes, unselected buttons
BORDER = "#3a404a"
FG = "#e6e9ef"
MUTED = "#8b93a1"
ACCENT = "#3d8bfd"
ACCENT_HOVER = "#5a9dff"
OK = "#3ddc84"
WARN = "#ffb02e"
ERR = "#ff6b6b"
LED_OFF = "#3a404a"

# --- Fonts ------------------------------------------------------------------
FONT_FAMILY = "Segoe UI"
FONT = (FONT_FAMILY, 10)
FONT_BOLD = (FONT_FAMILY, 10, "bold")
FONT_BIG = (FONT_FAMILY, 18, "bold")

# --- Plot colours (one colour per electrical quantity) ------------------------
C_V1 = "#4da3ff"        # primary voltage
C_VM = "#9bb8ff"        # core (magnetising) voltage
C_V2 = "#2ee6d6"        # secondary voltage
C_I1 = "#ffb02e"        # primary current
C_I2 = "#ff6b6b"        # secondary current
C_I0 = "#c39bff"        # excitation current

C_FLUX = "#4da3ff"      # mutual (working) flux
C_LEAK = "#ff5fd2"      # leakage flux
C_COPPER = "#b87333"    # winding colour when cold
C_CORE_EDGE = "#aab2c0"
C_GRID = "#4a5160"

# Heat-map colours, cold -> hot
HEAT_COLOURS = ["#2b3445", "#4b3a7a", "#b3303a", "#ff8a1f", "#ffe36b"]
