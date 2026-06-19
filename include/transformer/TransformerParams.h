#pragma once

/**
 * @file   TransformerParams.h
 * @brief  All input parameters for one simulation run.
 *
 * The four simulation modes are cumulative — each adds parameters:
 *
 *  Mode 1  Ideal          V1, f, N1, N2, RL
 *  Mode 2  + Core losses  adds Rc, Xm
 *  Mode 3  + Copper loss  adds R1, R2
 *  Mode 4  + Leakage      adds X1, X2
 *
 * Parameters not relevant to the chosen mode stay at their default (0.0).
 * The solver ignores any parameter that is zero.
 */
struct TransformerParams
{
    // ── Simulation mode ───────────────────────────────────────────────────────
    int mode = 1;           ///< 1 = Ideal, 2 = Core loss, 3 = Copper, 4 = Practical

    // ── Mode 1 — always required ──────────────────────────────────────────────
    double V1  = 230.0;     ///< Primary voltage, RMS (V)
    double f   =  50.0;     ///< Supply frequency (Hz)
    int    N1  =  200;      ///< Primary winding turns
    int    N2  =  100;      ///< Secondary winding turns
    double RL  =  10.0;     ///< Load resistance (Ω)

    // ── Mode 2 — core loss model (shunt branch) ───────────────────────────────
    double Rc  =   0.0;     ///< Core loss resistance  (Ω)  — 0 means branch absent
    double Xm  =   0.0;     ///< Magnetising reactance (Ω)  — 0 means branch absent

    // ── Mode 3 — copper loss model (series winding resistance) ────────────────
    double R1  =   0.0;     ///< Primary winding resistance   (Ω)
    double R2  =   0.0;     ///< Secondary winding resistance (Ω)

    // ── Mode 4 — leakage reactance (series winding reactance) ────────────────
    double X1  =   0.0;     ///< Primary leakage reactance   (Ω)
    double X2  =   0.0;     ///< Secondary leakage reactance (Ω)
};
