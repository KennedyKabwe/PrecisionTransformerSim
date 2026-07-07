#include "utils/JsonSerializer.h"

#include <cmath>
#include <iomanip>
#include <sstream>

// ─────────────────────────────────────────────────────────────────────────────
// serialize — main entry point
// ─────────────────────────────────────────────────────────────────────────────
//
// Produces a single JSON object on stdout.  Python reads this with json.loads().
//
// Structure:
// {
//   "status":      "ok" | "error",
//   "error":       "..." ,                  // only present when status=error
//   "mode":        1-4,
//   "turns_ratio": a,
//   "phasors": {
//       "V1": { "magnitude": x, "angle_deg": y },
//       ...
//   },
//   "power": {
//       "P_in_W":  x,
//       "P_out_W": x,
//       "P_fe_W":  x,
//       "P_cu_W":  x
//   },
//   "performance": {
//       "efficiency_pct":  x,
//       "power_factor":    x,
//       "voltage_reg_pct": x
//   },
//   "flux": {
//       "mutual_Wb":    x,
//       "leakage1_Wb":  x,
//       "leakage2_Wb":  x
//   }
// }
// ─────────────────────────────────────────────────────────────────────────────

std::string JsonSerializer::serialize(const TransformerParams&  p,
                                      const TransformerResults& r)
{
    std::ostringstream o;
    o << "{\n";

    // ── Status ────────────────────────────────────────────────────────────────
    if (!r.valid) {
        o << "  \"status\": \"error\",\n";
        o << "  \"error\":  \"" << r.error << "\"\n";
        o << "}\n";
        return o.str();
    }

    o << "  \"status\":      \"ok\",\n";
    o << "  \"mode\":        "  << p.mode           << ",\n";
    o << "  \"turns_ratio\": "  << fmt(r.turns_ratio) << ",\n";

    // ── Phasors ───────────────────────────────────────────────────────────────
    // Each phasor is stored as magnitude (RMS) + angle in degrees.
    // Python's visualiser reads magnitude for vector length,
    // angle for the direction to draw the arrow on the phasor diagram.
    o << "  \"phasors\": {\n";
    o << "    " << phasorField("V1", r.V1) << ",\n";
    o << "    " << phasorField("V2", r.V2) << ",\n";
    o << "    " << phasorField("I1", r.I1) << ",\n";
    o << "    " << phasorField("I2", r.I2) << ",\n";
    o << "    " << phasorField("I0", r.I0) << ",\n";
    o << "    " << phasorField("Vm", r.Vm) << "\n";
    o << "  },\n";

    // ── Power ─────────────────────────────────────────────────────────────────
    // All in watts.  Python uses P_fe and P_cu to drive the heatmap intensity.
    o << "  \"power\": {\n";
    o << "    \"P_in_W\":  " << fmt(r.P_in)  << ",\n";
    o << "    \"P_out_W\": " << fmt(r.P_out) << ",\n";
    o << "    \"P_fe_W\":  " << fmt(r.P_fe)  << ",\n";
    o << "    \"P_cu_W\":  " << fmt(r.P_cu)  << "\n";
    o << "  },\n";

    // ── Performance ───────────────────────────────────────────────────────────
    o << "  \"performance\": {\n";
    o << "    \"efficiency_pct\":  " << fmt(r.efficiency)   << ",\n";
    o << "    \"power_factor\":    " << fmt(r.power_factor) << ",\n";
    o << "    \"voltage_reg_pct\": " << fmt(r.voltage_reg)  << "\n";
    o << "  },\n";

    // ── Flux ──────────────────────────────────────────────────────────────────
    // mutual_Wb   → visualiser draws working flux lines through the core
    // leakage1_Wb → visualiser draws leakage lines around primary coil
    // leakage2_Wb → visualiser draws leakage lines around secondary coil
    o << "  \"flux\": {\n";
    o << "    \"mutual_Wb\":   " << fmt(r.mutual_flux_Wb)   << ",\n";
    o << "    \"leakage1_Wb\": " << fmt(r.leakage_flux1_Wb) << ",\n";
    o << "    \"leakage2_Wb\": " << fmt(r.leakage_flux2_Wb) << "\n";
    o << "  }\n";

    o << "}\n";
    return o.str();
}

// ─────────────────────────────────────────────────────────────────────────────
// phasorField — formats one complex number as a JSON sub-object
// ─────────────────────────────────────────────────────────────────────────────
//
// std::abs(c)  → magnitude   |c|           (RMS value)
// std::arg(c)  → angle in radians          (relative to V1 at 0°)
// × 180/π      → convert to degrees        (more intuitive for students)
// ─────────────────────────────────────────────────────────────────────────────

std::string JsonSerializer::phasorField(const std::string& name, Complex c)
{
    static const double kPi = std::acos(-1.0);

    const double magnitude = std::abs(c);
    const double angle_deg = std::arg(c) * 180.0 / kPi;

    std::ostringstream o;
    o << "\"" << name << "\": { "
      << "\"magnitude\": " << fmt(magnitude) << ", "
      << "\"angle_deg\": " << fmt(angle_deg)
      << " }";
    return o.str();
}

// ─────────────────────────────────────────────────────────────────────────────
// fmt — format a double with fixed decimal places
// ─────────────────────────────────────────────────────────────────────────────
//
// std::fixed       : always show decimal point
// std::setprecision: number of digits after the decimal
// We default to 6 decimal places — sufficient for all electrical quantities.
// ─────────────────────────────────────────────────────────────────────────────

std::string JsonSerializer::fmt(double v, int precision)
{
    std::ostringstream o;
    o << std::fixed << std::setprecision(precision) << v;
    return o.str();
}
