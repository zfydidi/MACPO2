# Possible Reviewer Questions & Standard Responses (Pre-drafted Rebuttal)

Use this document when revision/rebuttal arrives: copy the relevant block, adapt to the specific review, and cite manuscript sections/appendices.

---

## Q1. Why can you multiply negotiation cost by $\bar p_{\mathrm{comm}}$ in Eq.~\eqref{eq:nego_complexity}?

**Short answer:** We model **expected execution cost**, not worst-case asymptotic complexity.

**Response template:**

> Equation~\eqref{eq:nego_complexity} is an **expected execution-cost model** (Section~\ref{sec:exec_cost}), not a worst-case $\mathcal{O}(\cdot)$ bound independent of runtime behavior. The expectation is taken over independent runs, paired seeds, and the stochastic gate path (phase sampling; policy sampling when RL is active). Multiplying by $\bar p_{\mathrm{comm}}$ reflects that negotiation work is incurred only on outer loops where $g^t=1$. Section~\ref{sec:exp_q2} reports measured trigger rates (Table~\ref{tab:comm_rate_f1_f18}). The model is empirical and complementary to fail-safe scheduling, which enforces a floor $\bar p_{\mathrm{comm}}\ge 1/K$ when relative thresholds rarely fire.

---

## Q2. Why assume bounded per-loop drift ($\varepsilon_d$)? Can you prove it for MACPO?

**Short answer:** We treat it as an **engineering assumption**, supported by logged drift statistics—not a MACPO convergence theorem.

**Response template:**

> We do **not** prove bounded per-loop drift for MACPO local search. Proposition~\ref{prop:failsafe} states what fail-safe timing guarantees **if** normalized shared-gap drift per silent loop is bounded. Appendix~\ref{app:empirical_drift} (Table~\ref{tab:empirical_drift}) reports observed per-loop drift on archived F1–F6 headline runs: mean $\bar\varepsilon\approx 0.004$–$0.005$, pooled max $\approx 0.007$–$0.010$. This supports the assumption empirically. A full MACPO drift proof would require additional structure on local search updates that black-box NDO does not provide.

---

## Q3. Why are improvements on F9/F15 so large ($10^{12}\to 10^{3}$)?

**Short answer:** MACPO endpoints retain **penalty from unresolved overlap inconsistency**; this is not a nine-order-of-magnitude improvement in the underlying landscape.

**Response template:**

> Table~\ref{tab:macpo_rl_mean_f1_f18} compares MACPO’s **penalized archived endpoint** $F$ (still inflated when shared-variable inconsistency remains) against RL-MACPO’s **terminal logged** $f_{\mathrm{pure}}$. On F9/F15, always-on MACPO under static penalties fails to eliminate constraint violation; the global penalized sum therefore remains orders of magnitude above the pure objective. Discussion (Route~1) states explicitly that the large numerical gaps **mainly reflect unresolved penalty violations in the original MACPO implementation**, not proportional improvements in the underlying objective. Both methods share the same evaluation budget and paired seeds.

---

## Q4. If RL is not better than EMA or fixed schedules, why include RL at all?

**Short answer:** RL is a **default plug-in implementation**, not the main contribution.

**Response template:**

> Once conflict gating is fixed, Table~\ref{tab:penalty_controller_f3_f5} shows RL, EMA, and fixed phase schedules are **statistically tied** at similarly low trigger rates. We therefore do **not** claim RL superiority for penalty control. RL is retained as a unified default that avoids benchmark-specific hand schedules and supports automation (Section~\ref{sec:discussion}, Route~3). Appendix~\ref{app:rl_controller} provides supplementary diagnostics for completeness only. A genuine RL research contribution in this line would target **harder timing decisions** (who/when to communicate), noted as future work (Section~\ref{sec:future_rl}).

---

## Q5. Why is the conflict proxy CI defined as the **mean** over dimensions, not max / variance / entropy?

**Short answer:** Mean CI is a **cheap, interpretable aggregate** aligned with per-dimension fail-safe drift; alternatives are future work.

**Response template:**

> We use $\mathrm{CI}=\frac{1}{D}\sum_d c_d$ as a dimension-wise aggregate conflict proxy because (i) it matches the per-dimension normalized-gap structure used in Proposition~\ref{prop:failsafe} and Empirical Criterion~\ref{crit:skip}, (ii) it is cheap to compute online without distributional estimation, and (iii) CI-bin trigger diagnostics (Fig.~\ref{fig:ci_bin_trigger}) and gate ablations empirically validate that low-CI rounds are skipped while quality is preserved. Max-, variance-, or entropy-based proxies may sharpen tail sensitivity; we treat them as **future variants** of the same timing framework rather than a flaw in the current design, and we did not tune CI’s functional form separately per benchmark.

---

## Q6. Is this just a MACPO-specific tweak?

**Short answer:** MACPO is the **platform**; the insight is **when to communicate**, algorithm-agnostic.

**Response template:**

> The manuscript separates *whether to communicate* from *how to negotiate*. MACPO instantiates the negotiation step, but the gate, fail-safe bound, and phase-relative skip rule apply wherever distributed black-box agents share edge-coupled variables and bandwidth is limited. Dispatch simulators and IEEE pilots (Section~\ref{sec:applications}, Appendix~\ref{app:applications}) test transfer beyond F1–F18. Discussion explicitly states this viewpoint is **algorithm-agnostic** and applicable beyond MACPO-style penalty negotiation.

---

## Q7. How strong are the external baselines (MASOIE / MAES-CCSA)?

**Response template:**

> MASOIE (Table~\ref{tab:external_masoie}) is included as a **cross-paradigm reference** on shared function names, not a matched-budget MACPO-clone baseline. MAES-CCSA code is **not available in open source** at the time of submission; we compare primarily against always-on MACPO, periodic-$K$ communication, and internal gate variants on a **common codebase** with paired seeds and matched evaluation caps. We state these limitations explicitly in Related Work and Limitations.

---

## Q8. IEEE-118 / IEEE-30 show cost offsets or outliers—does gating break correctness?

**Response template:**

> IEEE pilots exhibit a **case-dependent accuracy–communication trade-off** (Table~\ref{tab:ieee_power_cases}). IEEE-118 shows a small detectable median cost offset at substantially lower trigger rate (Wilcoxon $p=0.01$). IEEE-30 success is 23/25 due to **two LLSO stagnation outliers**, not a lower trigger rate; Appendix~\ref{app:applications} (Table~\ref{tab:application_run_stats}) reports run-level paired-$\Delta$ quartiles. We do not claim universal zero-cost reduction on every grid instance.

---

## Q9. Reproducibility / data availability?

**Response template:**

> Supplementary material includes JSON table summaries, reproduction scripts, configuration names (`Selection_0.9_0.7_0.5`, gate defaults in Table~\ref{tab:gate_defaults}), paired-seed protocol (`MACPO_PAIR_SEED`), and paths to archived run logs (`EXPERIMENT_DATA_MAP.md`). Representative raw trajectories and aggregation utilities are bundled in `Supplementary.zip`.

---

## Quick mapping: likely reviewer archetypes

| Reviewer focus | Lead with | Cite |
|----------------|-----------|------|
| Theory / TEVC | Execution-cost vs worst-case; CI as engineering proxy | §Complexity, Prop.~\ref{prop:failsafe}, Appendix A |
| Systems / TSMC | Dispatch + IEEE transfer, trigger-rate tables | §Q4, Tables~\ref{tab:application_cases},~\ref{tab:ieee_power_cases} |
| RL skeptic | RL demoted; tied with EMA | Table~\ref{tab:penalty_controller_f3_f5}, Appendix B disclaimer |
| MACPO author | Platform role; when-vs-how separation | §Discussion Route~1, §Method |
