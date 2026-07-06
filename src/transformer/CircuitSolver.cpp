#include "transformer/CircuitSolver.h"

#include <cmath>
#include <complex>
#include <string>

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

/// Anything below this is treated as zero (avoids division by zero)
static constexpr double kEps = 1e-12;

/// π — computed at compile time, works on all platforms
static const double kPi = std::acos(-1.0);


// ─────────────────────────────────────────────────────────────────────────────
// Public entry point
// ─────────────────────────────────────────────────────────────────────────────

TransformerResults CircuitSolver::solve(const TransformerParams& p)
{
    std::string err;
    if (!validate(p, err)) {
        TransformerResults bad;
        bad.valid = false;
        bad.error = err;
        return bad;
    }

    TransformerResults res = (p.mode == 1) ? solveIdeal(p)
                                           : solveGeneral(p);
    if (res.valid)
        computeFlux(p, res);

    return res;
}


// ─────────────────────────────────────────────────────────────────────────────
// Validation
// ─────────────────────────────────────────────────────────────────────────────

bool CircuitSolver::validate(const TransformerParams& p, std::string& err)
{
    if (p.mode < 1 || p.mode > 4) { err = "mode must be 1-4";     return false; }
    if (p.V1 <= 0)                 { err = "V1 must be positive";   return false; }
    if (p.f  <= 0)                 { err = "f must be positive";    return false; }
    if (p.N1 <= 0)                 { err = "N1 must be positive";   return false; }
    if (p.N2 <= 0)                 { err = "N2 must be positive";   return false; }
    if (p.RL <= 0)                 { err = "RL must be positive";   return false; }
    if (p.Rc < 0)                  { err = "Rc cannot be negative"; return false; }
    if (p.Xm < 0)                  { err = "Xm cannot be negative"; return false; }
    if (p.R1 < 0)                  { err = "R1 cannot be negative"; return false; }
    if (p.R2 < 0)                  { err = "R2 cannot be negative"; return false; }
    if (p.X1 < 0)                  { err = "X1 cannot be negative"; return false; }
    if (p.X2 < 0)                  { err = "X2 cannot be negative"; return false; }
    return true;
}


// ─────────────────────────────────────────────────────────────────────────────
// Mode 1 — Ideal Transformer
// ─────────────────────────────────────────────────────────────────────────────
//
// No losses, no shunt branch, no series impedance.
// Pure turns-ratio relationships:
//
//   a  = N1/N2
//   V2 = V1 / a       voltage scales by 1/a
//   I2 = V2 / RL      Ohm's law on secondary
//   I1 = I2 / a       ampere-turns balance: N1*I1 = N2*I2
//
// Resistive load means all phasors are in phase.
// Efficiency = 100%, power factor = 1.0, voltage regulation = 0%.
// ─────────────────────────────────────────────────────────────────────────────

TransformerResults CircuitSolver::solveIdeal(const TransformerParams& p)
{
    TransformerResults res;

    const double a = static_cast<double>(p.N1) / p.N2;
    res.turns_ratio = a;

    res.V1 = Complex(p.V1, 0.0);   // reference phasor, angle = 0

    const double V2_mag = p.V1 / a;
    const double I2_mag = V2_mag / p.RL;
    const double I1_mag = I2_mag / a;

    res.V2 = Complex(V2_mag, 0.0);
    res.I2 = Complex(I2_mag, 0.0);
    res.I1 = Complex(I1_mag, 0.0);
    res.I0 = Complex(0.0,    0.0);
    res.Vm = res.V1;                // no series drop

    res.P_out = I2_mag * I2_mag * p.RL;
    res.P_in  = res.P_out;          // ideal: P_in == P_out
    res.P_fe  = 0.0;
    res.P_cu  = 0.0;

    res.efficiency   = 100.0;
    res.power_factor = 1.0;
    res.voltage_reg  = 0.0;

    return res;
}


// ─────────────────────────────────────────────────────────────────────────────
// Modes 2-4 — General T-circuit (node-voltage method)
// ─────────────────────────────────────────────────────────────────────────────
//
//      Z1 = R1+jX1              Z2' = a2(R2+jX2)
// V1--[Z1]-------+----------[Z2']----[ZL']----GND
//                |
//             [Rc]||[jXm]    shunt branch
//                |
//               GND
//
// STEP 1 — Impedances
//   Z1     = R1 + jX1
//   Z2'    = a2*R2 + j*a2*X2      (secondary referred to primary)
//   ZL'    = a2*RL                 (load referred to primary)
//
// STEP 2 — Shunt admittance
//   Y_shunt = 1/Rc - j/Xm         (Rc and jXm in parallel)
//   Parallel branches add as admittances, not impedances.
//
// STEP 3 — Solve for Vm via KCL at shunt node
//   (V1 - Vm)/Z1 = Vm*Y_shunt + Vm/(Z2'+ZL')
//   => Vm = V1 / [1 + Z1*(Y_shunt + Y_load')]
//
//   Special case Z1 = 0 => Vm = V1
//
// STEP 4 — Recover currents, refer back to secondary
// STEP 5 — Power and performance
// ─────────────────────────────────────────────────────────────────────────────

TransformerResults CircuitSolver::solveGeneral(const TransformerParams& p)
{
    TransformerResults res;

    const double a = static_cast<double>(p.N1) / p.N2;
    res.turns_ratio = a;

    const Complex V1(p.V1, 0.0);
    res.V1 = V1;

    // ── STEP 1: Impedances ────────────────────────────────────────────────────

    const Complex Z1(p.R1, p.X1);
    const Complex Z2_prime(p.R2 * a*a,  p.X2 * a*a);
    const Complex ZL_prime (p.RL * a*a,  0.0);

    // ── STEP 2: Shunt admittance ──────────────────────────────────────────────
    // Rc  branch: admittance =  1/Rc        (real — in-phase with voltage)
    // Xm  branch: admittance = -j/Xm        (imaginary — 90 degrees lagging)

    Complex Y_shunt(0.0, 0.0);
    if (p.Rc > kEps) Y_shunt += Complex(1.0 / p.Rc,   0.0);
    if (p.Xm > kEps) Y_shunt += Complex(0.0,          -1.0 / p.Xm);

    // ── STEP 3: Solve for Vm ──────────────────────────────────────────────────

    const Complex Z_secondary  = Z2_prime + ZL_prime;
    const Complex Y_load_prime = Complex(1.0, 0.0) / Z_secondary;

    Complex Vm;
    if (std::abs(Z1) < kEps) {
        Vm = V1;                    // no series drop when Z1 = 0
    } else {
        Vm = V1 / (Complex(1.0, 0.0) + Z1 * (Y_shunt + Y_load_prime));
    }
    res.Vm = Vm;

    // ── STEP 4: Currents and secondary voltage ────────────────────────────────

    const Complex I2_prime = Vm * Y_load_prime;   // secondary (referred)
    const Complex I0       = Vm * Y_shunt;         // excitation current

    Complex I1;
    if (std::abs(Z1) < kEps) {
        I1 = I0 + I2_prime;        // KCL when Z1 = 0
    } else {
        I1 = (V1 - Vm) / Z1;       // Ohm's law across Z1
    }

    // Refer back to actual secondary side:
    //   I2' = I2/a  =>  I2 = I2' * a
    //   V2' = I2' * ZL'  =>  V2 = V2'/a
    const Complex I2 = I2_prime * a;
    const Complex V2 = (I2_prime * ZL_prime) / a;

    res.I1 = I1;
    res.I2 = I2;
    res.I0 = I0;
    res.V2 = V2;

    // ── STEP 5: Power ─────────────────────────────────────────────────────────
    //
    // std::norm(z) returns |z|^2  (C++ standard — used for I^2*R losses)
    //
    // Active input power: P = Re(V * conj(I))
    // This is the standard complex power formula. The real part is watts.
    // The imaginary part would be reactive power (VAR) — not needed here.

    res.P_in  = (V1 * std::conj(I1)).real();
    res.P_out = std::norm(I2) * p.RL;
    res.P_fe  = (p.Rc > kEps) ? std::norm(Vm) / p.Rc : 0.0;
    res.P_cu  = std::norm(I1) * p.R1
              + std::norm(I2) * p.R2;

    // ── STEP 6: Performance metrics ───────────────────────────────────────────

    res.efficiency = (res.P_in > kEps)
        ? (res.P_out / res.P_in) * 100.0
        : 0.0;

    // Power factor = cos(angle of I1 relative to V1)
    // Since V1 is our reference at angle 0, arg(I1) gives the lag angle.
    const double I1_mag = std::abs(I1);
    res.power_factor = (I1_mag > kEps)
        ? std::cos(std::arg(I1))
        : 1.0;

    // Voltage regulation: how much V2 drops under load vs no-load
    const double V2_no_load   = p.V1 / a;
    const double V2_full_load = std::abs(V2);
    res.voltage_reg = (V2_full_load > kEps)
        ? (V2_no_load - V2_full_load) / V2_full_load * 100.0
        : 0.0;

    return res;
}


// ─────────────────────────────────────────────────────────────────────────────
// Flux approximations  (for the Python visualiser)
// ─────────────────────────────────────────────────────────────────────────────
//
// Faraday's law for sinusoidal quantities:
//   V = 4.44 * f * N * Phi_peak
//   => Phi_peak = V / (4.44 * f * N)
//
// Mutual flux uses Vm (voltage driving the core).
// Leakage flux uses:  Phi_leak = X * I / (omega * N)
//   derived from X = omega*L and Phi = L*I/N
// ─────────────────────────────────────────────────────────────────────────────

void CircuitSolver::computeFlux(const TransformerParams& p, TransformerResults& res)
{
    const double Vm_mag = std::abs(res.Vm);
    const double omega  = 2.0 * kPi * p.f;

    res.mutual_flux_Wb = (p.f > kEps && p.N1 > 0)
        ? Vm_mag / (4.44 * p.f * static_cast<double>(p.N1))
        : 0.0;

    if (p.mode == 4) {
        const double I1_mag = std::abs(res.I1);
        const double I2_mag = std::abs(res.I2);

        res.leakage_flux1_Wb = (p.X1 > kEps && omega > kEps)
            ? (p.X1 * I1_mag) / (omega * static_cast<double>(p.N1))
            : 0.0;

        res.leakage_flux2_Wb = (p.X2 > kEps && omega > kEps)
            ? (p.X2 * I2_mag) / (omega * static_cast<double>(p.N2))
            : 0.0;
    }
}
