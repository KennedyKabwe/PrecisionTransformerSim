#pragma once

#include <complex>
#include <string>

/**
 * @file   TransformerResults.h
 * @brief  All computed outputs from one simulation run.
 *
 * std::complex<double> stores a phasor as (real, imaginary).
 * From a phasor you can get:
 *   std::abs(z)   → magnitude  (e.g. RMS voltage in volts)
 *   std::arg(z)   → angle in radians  (convert × 180/π for degrees)
 *
 * Every quantity is in SI units and RMS unless stated otherwise.
 */

/// Shorthand — used throughout the codebase
using Complex = std::complex<double>;

struct TransformerResults
{
    // ── Phasors (RMS) ─────────────────────────────────────────────────────────
    Complex V1;     ///< Primary voltage phasor         (V)   — reference, angle = 0
    Complex V2;     ///< Secondary voltage phasor       (V)
    Complex I1;     ///< Primary current phasor         (A)
    Complex I2;     ///< Secondary current phasor       (A)
    Complex I0;     ///< No-load / excitation current   (A)   — zero in mode 1
    Complex Vm;     ///< Voltage at shunt branch node   (V)   — centre of T-circuit

    // ── Power (W) ─────────────────────────────────────────────────────────────
    double P_in  = 0.0;     ///< Active input power            (W)
    double P_out = 0.0;     ///< Active output power           (W)
    double P_fe  = 0.0;     ///< Core (iron) losses            (W)  — zero in mode 1
    double P_cu  = 0.0;     ///< Total copper losses           (W)  — zero in modes 1–2

    // ── Performance metrics ───────────────────────────────────────────────────
    double efficiency   = 0.0;  ///< η  = P_out / P_in × 100       (%)
    double power_factor = 0.0;  ///< cos φ at primary terminals     (dimensionless)
    double voltage_reg  = 0.0;  ///< VR = (V2_nl − V2_fl)/V2_fl × 100  (%)
    double turns_ratio  = 0.0;  ///< a  = N1 / N2                   (dimensionless)

    // ── Flux approximations (for visualiser) ──────────────────────────────────
    // Derived from Faraday's law:  Φ_peak = Vm / (4.44 × f × N)
    double mutual_flux_Wb   = 0.0;  ///< Working (mutual) flux linking both coils (Wb)
    double leakage_flux1_Wb = 0.0;  ///< Primary leakage flux   (Wb) — mode 4 only
    double leakage_flux2_Wb = 0.0;  ///< Secondary leakage flux (Wb) — mode 4 only

    // ── Status ────────────────────────────────────────────────────────────────
    bool        valid = true;   ///< false if validation or solver failed
    std::string error;          ///< human-readable error message when valid == false
};
