# Confirmed Contribution

## Core Contribution

| Field | Content |
|---|---|
| Main contribution statement | A protocol-agnostic, three-layer conflict gate that schedules neighbor negotiation in penalty-based black-box NDO from a local conflict proxy and phase-relative threshold, with fail-safe synchronization, yielding large communication savings at matched evaluation budget while preserving terminal fitness when conflict is low or consensus demand is moderate. |
| Contribution type | new method + new theory + new empirical finding |
| One-sentence reviewer payoff | Reviewers get an interpretable communication-timing layer—not another opaque RL trigger—with formal skip/consensus guarantees and cross-paradigm validation beyond a single MACPO shell. |

## Why This Contribution Is Needed

| Field | Content |
|---|---|
| Field problem | Distributed black-box NDO in bandwidth/energy-limited networks must coordinate shared variables without continuous synchronization. |
| Specific gap | Existing penalty-based cooperative evolution (e.g., MACPO) negotiates almost every outer loop; no standard, interpretable rule decides *when* negotiation is worth its communication cost. |
| Concrete challenge | The decision must be made online from local black-box conflict signals, remain stable under phase drift, and not assume gradients or a fixed negotiation protocol. |
| Why prior work leaves it unresolved | Gradient/federated/event-triggered methods schedule gradients or consensus states, not explicit shared-variable negotiation in black-box NDO; always-on penalty evolution ignores communication budget entirely. |

## How This Paper Responds

| Field | Content |
|---|---|
| Design response | Three-layer gate (minimum interval, relative CI threshold with fail-safe K, phase sampling) inserted before negotiation; RL confined to post-gate penalty adaptation only. |
| Evidence required | (E1) Matched-budget fitness vs always-on MACPO on F1–F18; (E2) trigger-rate reduction; (E3) ablations isolating gate vs penalty controller; (E4) formal skip/drift/consensus bounds with numerical validation; (E5) same gate on abstract rules + MASOIE external-learning solver. |
| Evidence available | Tables for F1–F18, comm-rate table, gate-variant ablations, Figs gated_universality/skip_bound/gated_convergence/masoie_recovery, MASOIE Table tab:masoie_gated, application pilots. |
| Evidence missing | Global convergence of full black-box search; MAES-CCSA matched comparison; proof of bounded drift for embedded LLSO/CSO; asynchronous/time-varying networks. |

## Claim Boundary

| Field | Content |
|---|---|
| Strong claims allowed | Large trigger reduction at matched budget; fitness match/improve on most benchmarks; bounded skip suboptimality on h_i; intermittent consensus rates in linearized sandbox; protocol-agnostic plug-in on averaging/gossip/best-response and MASOIE; operating-point recovery via K on consensus-critical cases. |
| Claims to soften or avoid | Do not claim global optimality or universal superiority over periodic/random on weak single-round gossip at all budgets; do not claim bounds on pure global F; do not claim default gate works on all consensus-critical instances without higher trigger rate. |
| Novelty risk | Event-triggered / communication-efficient distributed optimization literature; answer: those methods target gradients/consensus, not black-box penalty negotiation scheduling with CI proxy. |
| Significance risk | "Only a MACPO patch"; answer: sandbox + MASOIE integration + theory show scheduling layer independent of negotiation protocol. |
