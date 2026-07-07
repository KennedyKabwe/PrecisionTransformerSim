#include "transformer/CircuitSolver.h"
#include "utils/ArgParser.h"
#include "utils/JsonSerializer.h"

#include <iostream>
#include <exception>

// ─────────────────────────────────────────────────────────────────────────────
// main — entry point
// ─────────────────────────────────────────────────────────────────────────────
//
// Flow:
//   1. Parse command-line arguments into TransformerParams
//   2. Solve the circuit  →  TransformerResults
//   3. Serialise results  →  JSON string to stdout
//
// Python reads the JSON from stdout via subprocess.
// Any fatal error prints to stderr (not stdout) so it never corrupts the JSON.
// ─────────────────────────────────────────────────────────────────────────────

int main(int argc, char* argv[])
{
    try
    {
        // ── Step 1: Parse arguments ───────────────────────────────────────────
        ArgParser parser(argc, argv);

        if (parser.helpRequested()) {
            ArgParser::printHelp(argv[0]);
            return 0;
        }

        const TransformerParams params = parser.parse();

        // ── Step 2: Solve the circuit ─────────────────────────────────────────
        const TransformerResults results = CircuitSolver::solve(params);

        // ── Step 3: Output JSON ───────────────────────────────────────────────
        std::cout << JsonSerializer::serialize(params, results);

        // Return 0 = success, 1 = simulation error (bad inputs etc.)
        return results.valid ? 0 : 1;
    }
    catch (const std::exception& e)
    {
        // Argument parsing errors land here.
        // Print to stderr — never stdout — so Python's JSON parse stays clean.
        std::cerr << "Error: " << e.what() << "\n";
        std::cerr << "Run with --help for usage.\n";
        return 2;
    }
}
