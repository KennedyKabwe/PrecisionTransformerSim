#pragma once

#include "transformer/TransformerParams.h"
#include "transformer/TransformerResults.h"

/**
 * @file   CircuitSolver.h
 * @brief  Solves the T-equivalent circuit of a single-phase transformer.
 *
 * The standard T-equivalent circuit (all quantities referred to primary):
 *
 *        Z1 = R1+jX1            Z2' = a²(R2+jX2)
 *   V1 ──[■]──────┬──────────────[■]──── V2' ──[RL']── GND
 *                 │
 *              [Rc]║[jXm]     ← shunt branch (core model)
 *                 │
 *                GND
 *
 *  where:
 *    a    = N1/N2  (turns ratio)
 *    Z2'  = a² × Z2       (secondary impedance referred to primary)
 *    RL'  = a² × RL       (load referred to primary)
 *    Rc║jXm               (parallel core-loss + magnetising branch)
 *
 * Node-voltage method at the shunt junction gives:
 *
 *   Vm = V1 / [ 1 + Z1·(Y_shunt + Y_load') ]
 *
 * Special case Z1 = 0:  Vm = V1  (primary directly at node, no series drop).
 *
 * All four modes use this same equation — unused parameters are simply zero,
 * which collapses their branch out of the circuit automatically.
 */
class CircuitSolver
{
public:
    /**
     * @brief  Run the simulation for the given parameters.
     * @param  p  Fully populated TransformerParams (unused fields = 0).
     * @return    TransformerResults with all outputs filled in.
     *            On invalid input, results.valid == false and results.error
     *            contains a description.
     */
    static TransformerResults solve(const TransformerParams& p);

private:
    // ── Sub-solvers ───────────────────────────────────────────────────────────

    /// Mode 1: closed-form ideal solution (no complex arithmetic needed).
    static TransformerResults solveIdeal(const TransformerParams& p);

    /// Modes 2–4: general T-circuit via node-voltage method.
    static TransformerResults solveGeneral(const TransformerParams& p);

    // ── Post-processing ───────────────────────────────────────────────────────

    /// Compute flux approximations and store in res.
    static void computeFlux(const TransformerParams& p, TransformerResults& res);

    // ── Validation ────────────────────────────────────────────────────────────

    /// Returns false and fills err when inputs are out of range.
    static bool validate(const TransformerParams& p, std::string& err);
};
