#pragma once

#include "transformer/TransformerParams.h"
#include <map>
#include <string>

/**
 * @file   ArgParser.h
 * @brief  Parses command-line arguments into a TransformerParams struct.
 *
 * Expected format:  --key value  (all flags use double-dash)
 *
 * Example:
 *   ./transformer_sim.exe --mode 3 --V1 230 --f 50 --N1 200 --N2 100
 *                         --RL 10 --Rc 500 --Xm 200 --R1 0.5 --R2 0.3
 */
class ArgParser
{
public:
    /// Parse argc/argv on construction.  Throws std::runtime_error on bad input.
    ArgParser(int argc, char* argv[]);

    /// Returns true if the user passed --help or -h.
    bool helpRequested() const;

    /// Build and return a TransformerParams from the parsed flags.
    TransformerParams parse() const;

    /// Print usage instructions to stdout.
    static void printHelp(const char* programName);

private:
    std::map<std::string, std::string> args_;   ///< key → value store
    bool help_ = false;

    /// Get a double from args_, or return defaultVal if key is absent.
    double getDouble(const std::string& key, double defaultVal = 0.0) const;

    /// Get an int from args_, or return defaultVal if key is absent.
    int    getInt   (const std::string& key, int    defaultVal = 0)   const;

    /// Returns true if --key was provided.
    bool   has      (const std::string& key) const;
};
