# Motivation Options After Research

The research stage supports three defensible ways to organize the journal
article. The final rewrite must use one controlling motivation; the options are
not interchangeable titles for the same draft.

## Option A — Communication timing as the primary gap (recommended)

**Controlling motivation.** Physical networked systems cannot sustain
always-on neighbor negotiation, yet penalty-based black-box NDO lacks a
transparent online rule for deciding when another shared-variable negotiation
round is worth opening. The paper therefore introduces and validates a
conflict-gated scheduling layer whose decisions are interpretable and whose
quality loss is bounded only at the explicitly stated gate/linearized levels.

**Main contribution.** The three-layer conflict gate and its scheduling
interface.

**Evidence spine.**

1. Gate definition and mechanism ablation.
2. Approximately matched-budget F1–F18 fitness and trigger-rate evidence.
3. Scoped skip, drift, and intermittent-consensus checks.
4. Transfer to abstract negotiation operators and MASOIE.
5. Dispatch-style pilots as relevance evidence.

**Necessary boundaries.** Do not claim global convergence, universal SOTA
superiority, or physical network-cost savings from trigger counts alone.

**Reviewer payoff.** A clear answer to *when to negotiate* that is broader than
a MACPO-specific tuning patch.

## Option B — A protocol-facing scheduling interface

**Controlling motivation.** Communication-efficient distributed optimization
often entangles triggering with a particular update rule. Black-box NDO needs a
separable scheduling interface that can sit above different shared-variable
negotiation operators while preserving their internal mechanics.

**Main contribution.** Separation of the gate from averaging, gossip,
best-response, MACPO penalty negotiation, and MASOIE external learning.

**Evidence spine.** Interface definition, solver-agnostic sandbox, MASOIE
integration, default failures on consensus-critical cases, and recovery through
a tighter fail-safe period.

**Risk.** The transfer evidence is limited to the tested operators and six
MASOIE functions. Without broader full-solver tests, “protocol-agnostic” must
remain an interface claim.

**Reviewer payoff.** A reusable architecture rather than another monolithic
optimizer.

## Option C — Operating-point control under communication budgets

**Controlling motivation.** Distributed black-box solvers need an interpretable
way to navigate the communication-quality trade-off instead of adopting either
always-on negotiation or a fixed period selected without observing conflict.

**Main contribution.** A conflict-conditioned operating surface controlled by
\((\lambda,K,p_{\mathrm{phase}})\), with explicit safety/quality trade-offs.

**Evidence spine.** Periodic/random comparisons, low-conflict trigger behavior,
parameter sensitivity, fail-safe recovery, and communication–fitness frontiers.

**Risk.** Existing evidence covers selected functions and does not justify
Pareto dominance across all budgets. A principled parameter-selection rule
would need stronger treatment.

**Reviewer payoff.** An interpretable policy for spending a limited negotiation
budget.

## Research recommendation

Choose **Option A** as the journal spine. Use Option B as the strongest
generality argument and Option C as the operating-envelope interpretation.
This arrangement matches the available evidence while keeping RL-based penalty
adaptation clearly auxiliary.

## Confirmation required

PaperSpine must not begin substantive rewriting until the user explicitly
selects, revises, or replaces the controlling motivation.
