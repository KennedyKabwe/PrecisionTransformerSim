#pragma once

#include "transformer/TransformerParams.h"
#include "transformer/TransformerResults.h"
#include <string>

/**
 * @file   JsonSerializer.h
 * @brief  Converts simulation results into a JSON string.
 *
 * No external library used — JSON is hand-built from the results struct.
 * Python reads this output via subprocess and parses it with json.loads().
 *
 * Output structure:
 * {
 *   "status":      "ok" | "error",
 *   "mode":        1–4,
 *   "turns_ratio": a,
 *   "phasors":     { V1, V2, I1, I2, I0, Vm — each with magnitude + angle_deg },
 *   "power":       { P_in_W, P_out_W, P_fe_W, P_cu_W },
 *   "performance": { efficiency_pct, power_factor, voltage_reg_pct },
 *   "flux":        { mutual_Wb, leakage1_Wb, leakage2_Wb }
 * }
 */
class JsonSerializer
{
public:
    static std::string serialize(const TransformerParams&  p,
                                 const TransformerResults& r);

private:
    /// Format a phasor as:  "name": { "magnitude": x, "angle_deg": y }
    static std::string phasorField(const std::string& name, Complex c);

    /// Format a double with fixed precision.
    static std::string fmt(double v, int precision = 6);
};
