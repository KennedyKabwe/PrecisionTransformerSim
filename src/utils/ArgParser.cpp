#include "utils/ArgParser.h"

#include <iostream>
#include <stdexcept>
#include <string>

// ─────────────────────────────────────────────────────────────────────────────
// Constructor — parses argc/argv into the args_ map
// ─────────────────────────────────────────────────────────────────────────────
//
// argv[] looks like this at runtime:
//   argv[0] = "transformer_sim.exe"   (program name — we skip it)
//   argv[1] = "--mode"
//   argv[2] = "2"
//   argv[3] = "--V1"
//   argv[4] = "230"
//
// We walk in steps of 2: flag then value.
// Every flag must start with "--".
// ─────────────────────────────────────────────────────────────────────────────

ArgParser::ArgParser(int argc, char* argv[])
{
    for (int i = 1; i < argc; ++i)
    {
        std::string token(argv[i]);

        // ── Help flag ─────────────────────────────────────────────────────────
        if (token == "--help" || token == "-h") {
            help_ = true;
            return;
        }

        // ── Every flag must start with "--" ───────────────────────────────────
        if (token.size() < 3 || token.substr(0, 2) != "--") {
            throw std::runtime_error(
                "Invalid argument: '" + token + "'. Flags must start with --");
        }

        // ── Value must follow immediately ─────────────────────────────────────
        if (i + 1 >= argc) {
            throw std::runtime_error(
                "Flag '" + token + "' has no value after it");
        }

        // Strip "--"  →  "--mode" becomes "mode"
        const std::string key   = token.substr(2);
        const std::string value = std::string(argv[++i]);   // consume next token

        // Catch duplicates:  --V1 230 --V1 115  is an error
        if (args_.count(key)) {
            throw std::runtime_error("Duplicate flag: --" + key);
        }

        args_[key] = value;
    }
}

// ─────────────────────────────────────────────────────────────────────────────

bool ArgParser::helpRequested() const { return help_; }

// ─────────────────────────────────────────────────────────────────────────────
// parse — builds TransformerParams from the map
// ─────────────────────────────────────────────────────────────────────────────
//
// getDouble/getInt return the default value when a flag is absent,
// so the student only passes flags relevant to their chosen mode.
// ─────────────────────────────────────────────────────────────────────────────

TransformerParams ArgParser::parse() const
{
    TransformerParams p;

    p.mode = getInt   ("mode",  1);
    p.V1   = getDouble("V1",  230.0);
    p.f    = getDouble("f",    50.0);
    p.N1   = getInt   ("N1",   200);
    p.N2   = getInt   ("N2",   100);
    p.RL   = getDouble("RL",   10.0);
    p.Rc   = getDouble("Rc",    0.0);
    p.Xm   = getDouble("Xm",    0.0);
    p.R1   = getDouble("R1",    0.0);
    p.R2   = getDouble("R2",    0.0);
    p.X1   = getDouble("X1",    0.0);
    p.X2   = getDouble("X2",    0.0);

    return p;
}

// ─────────────────────────────────────────────────────────────────────────────
// printHelp
// ─────────────────────────────────────────────────────────────────────────────

void ArgParser::printHelp(const char* programName)
{
    std::cout
        << "\nTransformer Simulator — C++ Computation Engine\n"
        << "================================================\n\n"
        << "Usage:\n"
        << "  " << programName << " [flags]\n\n"
        << "Flags (all modes):\n"
        << "  --mode  int     Simulation mode 1-4          (default: 1)\n"
        << "  --V1    double  Primary voltage, RMS (V)     (default: 230)\n"
        << "  --f     double  Frequency (Hz)               (default: 50)\n"
        << "  --N1    int     Primary turns                (default: 200)\n"
        << "  --N2    int     Secondary turns              (default: 100)\n"
        << "  --RL    double  Load resistance (Ohm)        (default: 10)\n\n"
        << "Mode 2 — core losses:\n"
        << "  --Rc    double  Core loss resistance (Ohm)   (default: 0)\n"
        << "  --Xm    double  Magnetising reactance (Ohm)  (default: 0)\n\n"
        << "Mode 3 — copper losses:\n"
        << "  --R1    double  Primary winding R (Ohm)      (default: 0)\n"
        << "  --R2    double  Secondary winding R (Ohm)    (default: 0)\n\n"
        << "Mode 4 — leakage reactance:\n"
        << "  --X1    double  Primary leakage X (Ohm)      (default: 0)\n"
        << "  --X2    double  Secondary leakage X (Ohm)    (default: 0)\n\n"
        << "Output: JSON to stdout\n\n";
}

// ─────────────────────────────────────────────────────────────────────────────
// Private helpers
// ─────────────────────────────────────────────────────────────────────────────

double ArgParser::getDouble(const std::string& key, double defaultVal) const
{
    auto it = args_.find(key);
    if (it == args_.end()) return defaultVal;
    try {
        return std::stod(it->second);
    } catch (...) {
        throw std::runtime_error(
            "Flag --" + key + " expects a number, got: '" + it->second + "'");
    }
}

int ArgParser::getInt(const std::string& key, int defaultVal) const
{
    auto it = args_.find(key);
    if (it == args_.end()) return defaultVal;
    try {
        return std::stoi(it->second);
    } catch (...) {
        throw std::runtime_error(
            "Flag --" + key + " expects an integer, got: '" + it->second + "'");
    }
}

bool ArgParser::has(const std::string& key) const
{
    return args_.count(key) > 0;
}
