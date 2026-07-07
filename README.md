# Transformer Simulator

An educational single-phase transformer simulator built with **C++** (computation engine)
and **Python** (GUI + visualisation). Designed to help electrical engineering students
understand transformer behaviour by simulating four progressive models.

## Simulation Modes

| Mode | Model | What it adds |
|------|-------|-------------|
| 1 | Ideal Transformer | Turns ratio, voltage/current transformation |
| 2 | Core Losses | Adds Rc (core resistance) and Xm (magnetising reactance) |
| 3 | Copper Losses | Adds R1, R2 (winding resistances) |
| 4 | Practical | Adds X1, X2 (leakage reactance) — full model |

## Architecture

```
Python GUI  ──►  subprocess call  ──►  C++ engine  ──►  JSON output  ──►  Python visualiser
```

The C++ engine handles all electrical circuit mathematics and outputs JSON.
Python reads that JSON and drives the interface and visualisations.

## Requirements

| Tool | Version |
|------|---------|
| CMake | ≥ 3.20 |
| g++ (MinGW64 / GCC) | ≥ 11 (C++17) |
| Python | ≥ 3.10 |
| Git | any |

## Build

```bash
# 1. Configure (first time only, or when CMakeLists.txt changes)
cmake -S . -B build -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Debug

# 2. Compile
cmake --build build --parallel

# Binary lands at:
./build/bin/transformer_sim.exe
```

## Usage

```bash
# Mode 1 — Ideal
./build/bin/transformer_sim.exe --mode 1 --V1 230 --f 50 --N1 200 --N2 100 --RL 10

# Mode 4 — Practical (full model)
./build/bin/transformer_sim.exe \
  --mode 4 --V1 230 --f 50 --N1 200 --N2 100 --RL 10 \
  --Rc 500 --Xm 200 --R1 0.5 --R2 0.3 --X1 1.2 --X2 0.8
```

Output is JSON to stdout — the Python layer reads this.

## Project Structure

```
transformer_sim/
├── include/
│   ├── transformer/        # Header files — declarations
│   └── utils/              # Utility headers
├── src/
│   ├── transformer/        # C++ source — circuit math
│   ├── utils/              # Argument parser, JSON serializer
│   └── main.cpp            # Entry point
├── python/                 # GUI + visualisation (coming soon)
├── .vscode/                # VSCode build and debug config
├── CMakeLists.txt
└── README.md
```

## Roadmap

- [x] Project scaffold and build system
- [x] C++ computation engine (all 4 modes)
- [ ] Python bridge (subprocess + JSON)
- [ ] Python GUI (tkinter)
- [ ] Visualiser — transformer schematic
- [ ] Visualiser — core/winding heatmap
- [ ] Visualiser — leakage flux diagram
- [ ] Phasor diagram

## License

MIT
