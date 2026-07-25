# Confirmed Motivation

**Status:** Confirmed by user request to improve the existing IEEE conference draft using PaperSpine (2026-07-25).

## Controlling Motivation

Physical networked systems (UAV swarms, VEC, wide-area dispatch) face communication budgets that make always-on neighbor negotiation unsustainable. Penalty-based black-box NDO remains the relevant solver class when gradients are unavailable, but current always-on schedules waste transmissions when local shared variables are already aligned.

## Research Question

**When should agents open the negotiation channel in distributed black-box NDO under a matched evaluation budget—and can that decision be made interpretably, with bounded quality loss when skipping low-conflict rounds?**

## Why Now / Why This Paper

Recent work strengthens communication-efficient distributed optimization and cross-paradigm cooperative evolution, but does not supply a transparent, protocol-agnostic gate with formal skip/consensus guarantees validated on both abstract negotiation rules and a real external-learning solver (MASOIE).

## Non-Goals

- Replacing local evolutionary search with RL for communication decisions
- Claiming global convergence of the full nonconvex workflow
- Hiding consensus-critical failure modes of the default gate
