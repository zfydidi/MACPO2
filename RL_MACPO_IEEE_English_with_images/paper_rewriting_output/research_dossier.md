# Research Dossier: IEEE Journal Conversion (Target Journal TBD)

## Scope and Evidence Boundary

This dossier supports conversion of `conference_new_ready.tex` from a conference-formatted manuscript into an English journal article. It is based only on:

- `paper_spine_config.json`;
- `reference_materials/source_index.md`;
- the complete current main manuscript, `conference_new_ready.tex`;
- the local journal-scenario instructions in PaperSpine;
- the local pre-submission audit and symbol-consistency report.

No target IEEE journal, article type, official author-guideline URL, or set of accepted target-journal papers has been supplied. Consequently, journal-specific limits and policies are **not verified** here. Any venue statement below is either (a) directly observable in the local files, (b) a target-independent review expectation, or (c) explicitly marked as pending verification.

## Venue Requirements

### Confirmed from the Current Configuration

- Scene: research journal.
- Language: English.
- Workflow: substantial improvement of an existing paper, not language-only polishing.
- Working target: “IEEE journal (target TBD).”
- Required integrity constraint: preserve verified numerical results and do not fabricate experiments, metrics, citations, or theoretical claims.
- Current source is still formatted with `\documentclass[conference]{IEEEtran}` and conference-style author blocks. It is therefore **not yet in a verified journal template**.

### Safe IEEE-Journal Preparation Actions Before Venue Selection

The following actions are useful regardless of which technically appropriate IEEE journal is eventually selected:

1. Reframe the paper around one durable journal-level claim: conflict-gated scheduling is a communication decision layer for black-box network-based distributed optimization.
2. Separate the primary contribution (when to communicate) from the optional RL penalty controller (how to tune a post-gate penalty).
3. Make every theorem’s scope, assumptions, and experimental validation explicit and consistent.
4. Use one comparable evaluation objective across all methods in every headline table.
5. Report statistical design, randomization, paired seeds, sample size, test choice, effect sizes or confidence intervals, and failure handling consistently.
6. Provide enough algorithmic and parameter detail for independent implementation.
7. Consolidate supplementary material so that the main article remains self-contained while secondary diagnostics move to a supplement.
8. Prepare data/code availability and reproducibility statements, even if the final venue later changes their required wording.

These are manuscript-quality requirements, not claims about a particular journal’s formal policy.

### Requirements That Cannot Be Confirmed Until the Target Journal Is Named

The following must remain unresolved rather than guessed:

- exact journal template and document-class options;
- permitted article type (regular paper, brief, letters, survey, application paper, etc.);
- page, word, abstract, reference, and supplementary-material limits;
- required abstract structure and keyword count;
- figure width, font size, color, graphical-abstract, and table rules;
- whether author biographies, photos, ORCID identifiers, highlights, or nomenclature are required;
- data-availability and code/software-availability wording;
- generative-AI disclosure policy;
- cover-letter, conflict-of-interest, funding, ethics, and prior-conference-extension requirements;
- double-anonymous versus single-anonymous review rules;
- whether a journal extension of a prior conference paper requires a stated percentage or a detailed novelty comparison;
- open-access options and publication charges.

The target journal must therefore be selected before final formatting or submission-package work. Plausible venue families cannot be ranked responsibly from local evidence alone.

## Review Criteria

### 1. Importance and Fit

Reviewers should be able to see a technically important problem beyond the MACPO implementation: when agents should negotiate shared variables when communication is costly and local objectives are black-box. The strongest fit is likely with a journal that publishes distributed optimization, evolutionary computation, multi-agent systems, networked control, or computational intelligence. Exact fit is unconfirmed until a journal is named.

Current strength:

- The manuscript gives physical motivations in UAV, vehicular-edge, and power-network settings.
- It identifies an interpretable communication-timing gap in penalty-based black-box NDO.

Current risk:

- The application motivation is broader than the demonstrated evidence. The empirical pilots are dispatch-oriented, while UAV and VEC serve mainly as motivating examples.
- The paper must avoid implying deployment-level energy, bandwidth, latency, or monetary savings when it measures negotiation-trigger rate rather than physical communication cost.

### 2. Novelty and Positioning

The reviewable novelty should be stated narrowly:

- a conflict-proxy gate for deciding when shared-variable negotiation occurs in black-box NDO;
- decoupling communication timing from negotiation mechanics and penalty adaptation;
- validation across MACPO-style negotiation, a solver-agnostic sandbox, and gated MASOIE.

The paper should not claim that event-triggered communication itself is new. It must distinguish its contribution from gradient-based or state-error-based event triggers and from fixed-period communication in cooperative coevolution. The related-work section currently gives this distinction, but journal revision should add a compact comparison table covering information required, trigger signal, optimization assumptions, communication unit, guarantees, and supported black-box setting.

### 3. Technical Correctness

This is the highest-priority review criterion because the paper promotes three formal guarantees.

Blocking issue in the current gate definition:

- Equation `local_gate` requires interval, threshold/fail-safe, **and** phase sampling to pass. Thus, when `t-t_last >= K`, communication is not necessarily forced if the phase-sampling check fails. This conflicts with the prose, Algorithm 1, Proposition 1, the claimed silent-stretch bound `tau <= K-1`, and the stated communication floor `1/K`. The journal version must either make the fail-safe override phase sampling or weaken/rederive every associated guarantee.

Other technical points requiring formal audit:

- Proposition 2 states that negotiation leaves `f_i` unchanged because it updates shared references, but it writes `h_i(x)-h_i(Nx)` as if the operator acts on the decision vector. The operator, state, and reference update must be defined consistently.
- The non-expansiveness claim should be proved for each negotiation operator actually used, with the precise norm and system/local level stated.
- Proposition 3 assumes a state-independent Bernoulli gate, whereas the proposed gate is explicitly state dependent and includes interval, threshold, phase, and fail-safe logic. The result is therefore a surrogate linearized model, not a guarantee for the implemented gate. This separation must be prominent in the theorem title, discussion, abstract, and contribution list.
- The “Chebyshev gain” statement should be rechecked. If `lambda_c` is optimized for the expected operator `I-p lambda_c L`, the minimizer generally depends on `p`; the current expression omits that dependence.
- Proposition 1 assumes bounded normalized drift; the appendix provides empirical observations but not a proof. It should be presented as a conditional engineering bound, as the manuscript partly does already.
- The full black-box optimizer has no global convergence result. No sentence should let readers infer otherwise.

### 4. Experimental Soundness and Fairness

Positive elements:

- 25-run experiments are reported for many main comparisons.
- Paired seeds are stated for the principal LLSO experiments.
- Communication-trigger rates, wall time, ablations, sensitivity, application pilots, and transfer to MASOIE are included.
- The paper acknowledges that the penalty-controller choice is secondary once gating is fixed.

Major risks:

- For F7–F18, the manuscript explicitly says Proposed reports penalty-free best-so-far `F`, while archived MACPO endpoints may include residual overlap penalties. Those are not the same endpoint. The headline “wins all 12 pairs” is not defensible until both methods are recomputed using the identical pure global objective at identical checkpoints.
- “Same evaluation budget” is weakened by the stated 3.2% difference in end-of-run evaluation counts on F1–F6. The stopping and accounting protocol needs a precise explanation and preferably exact matching.
- External GFPDO/DPSO columns are reproduced from another protocol without significance tests. They should not visually imply paired, like-for-like evidence.
- The MASOIE comparison uses a different interaction topology and unmatched communication semantics in one table, then a gated binary in another. These roles must be separated clearly: contextual external reference versus controlled transfer test.
- Trigger rates that repeatedly equal 8.0% or 8.3% need raw-count definitions and variance where applicable; reviewers may otherwise infer a deterministic fail-safe floor rather than conflict-responsive gating.
- Statistical reporting should include effect sizes and confidence intervals, not only p-values. Multiple comparisons across 18 functions and two optimizers require a declared correction strategy or a clear family-wise interpretation.
- CSO uses Mann–Whitney U while LLSO uses paired Wilcoxon. If CSO also uses matched seeds, the reason for an unpaired test should be explained.
- IEEE-30 contains two failures and a very large mean variance, while the primary statistic is the paired median and “success” is defined as Proposed cost no more than twice MACPO. This threshold requires justification and failures must be analyzed rather than hidden by the median.
- Physical communication savings are represented by trigger frequency, not transmitted bytes, messages, latency, or energy. Claims must use “negotiation-trigger reduction” unless additional measurements are available.

### 5. Reproducibility

The journal manuscript should allow a reader to reconstruct:

- graph generation and fixed graph instances for F1–F18;
- local objective construction, shifts, rotations, overlap maps, and bounds;
- all gate parameters and initialization;
- phase boundaries and `p_phase` schedule;
- consensus-reference refresh behavior on skipped rounds;
- variable-selection score and update rule (currently described only at a high level);
- negotiation implementation, bilateral comparison, perturbation check, and acceptance rule;
- RL state, action, reward, architecture, training/inference protocol, seeds, and whether training is online;
- exact pure-objective logging for all algorithms;
- hardware, software, source versions, and wall-time measurement protocol;
- raw run-level results and scripts for figures and statistical tests.

The current manuscript provides default gate values and high-level algorithms, but the variable-selection and RL modules are not yet specified at journal-reproducibility depth.

### 6. Clarity and Internal Consistency

The current narrative is substantially stronger when communication gating remains the spine and RL is treated as optional. The journal revision should:

- reduce repeated statements of the same contribution across Introduction, Experiment roadmap, synthesis paragraphs, and Conclusion;
- distinguish communication, negotiation, trigger, message, and shared-dimension update consistently;
- avoid switching between “Proposed,” “RL-MACPO,” “RL,” and “complete” without an explicit naming table;
- keep `F`, penalized `h_i`, and archived endpoint metrics visibly distinct;
- replace very large result tables with a primary summary plus complete supplementary tables;
- shorten captions that currently perform too much argumentative work;
- split dense limitation and theory paragraphs;
- ensure every numerical claim has a directly identifiable table, figure, or run-level source.

## Accepted Paper Patterns

### Evidence Status

No accepted papers from a named target journal were supplied or verified. Therefore, no target-venue style pattern can be claimed. The 77-item local source index mostly inventories the current manuscript, figures, notes, and cited PDFs; it does not establish that a representative sample of accepted target-journal articles was analyzed.

### Provisional Field Pattern to Use, Not a Venue Rule

For a journal article in distributed/evolutionary optimization, the most defensible structure from the current evidence is:

1. **Introduction:** physical/algorithmic communication constraint → black-box NDO gap → why existing event-triggered gradient methods do not solve it → precise timing question → contribution and evidence map.
2. **Problem and metric definition:** NDO model → pure global objective → local penalized objective → exact communication-cost proxy.
3. **Method:** gate definition first → fail-safe semantics → post-gate variable selection and negotiation → optional penalty controller.
4. **Theory:** assumptions and scope table → conditional drift bound → skip-cost result → surrogate intermittent-consensus analysis → explicit boundary between these results and full-search convergence.
5. **Experiments:** research questions → common protocol → gate ablation → matched-objective baseline comparison → communication–quality frontier → robustness/sensitivity → transfer → applications.
6. **Discussion:** what the results establish → where gating fails or needs higher trigger rates → physical-cost limitations → theory limitations → external validity.
7. **Conclusion:** one restrained claim, no new quantitative result.

This pattern is recommended because it matches the paper’s argument, not because it has been verified as a rule of a particular IEEE journal.

### Result-Ordering Pattern

The journal version should order evidence by inferential strength:

1. verify that the gate actually responds to conflict rather than only to the fail-safe;
2. establish a fair matched-objective comparison;
3. show the communication–quality trade-off and sensitivity to `lambda`, `K`, and phase sampling;
4. validate theory under the exact assumptions of each proposition;
5. test transfer to another solver;
6. present applications as external-validity evidence, with failures and offsets visible.

## Constraints for This Paper

### Non-Negotiable Evidence Constraints

- Do not alter or invent any numerical result.
- Do not present archived penalized endpoints as the same metric as penalty-free `F`.
- Do not infer physical energy/bandwidth savings from trigger-rate reduction alone.
- Do not claim full-algorithm convergence from linearized, state-independent consensus analysis.
- Do not claim a fail-safe bound until gate logic actually guarantees a maximum silent interval.
- Do not describe the RL controller as superior; the current ablation says gated controllers are statistically tied.
- Do not claim target-journal compliance before the journal and article type are specified.
- Do not invent accepted-paper patterns, official policies, page limits, or AI-use rules.

### Journal-Conversion Constraints

- Replace the conference document class only after choosing the target journal and downloading its official template.
- Expand substance rather than merely length. Journal value should come from corrected theory, fairer experiments, deeper reproducibility, and stronger robustness analysis.
- If this manuscript extends a prior conference paper, create a verifiable novelty map and disclose overlap according to the selected journal’s policy.
- Preserve the communication-timing spine. RL diagnostics, long run-level tables, and secondary application detail are candidates for supplementary material.
- Retain limitations that materially qualify claims, especially consensus-critical F2/F4, IEEE-118 offset, IEEE-30 failures, lack of asynchronous/time-varying-network experiments, and unavailable MAES-CCSA code.

### Priority Actions for the Rewrite

**P0 — correctness before prose**

1. Resolve the fail-safe/phase-sampling logical contradiction.
2. Recompute or relabel F7–F18 so every compared method uses the identical pure objective.
3. Audit all propositions and proofs, especially operator definitions and the `p` dependence of the consensus-rate discussion.
4. Define the exact communication-cost unit and constrain claims to what is measured.

**P1 — journal-level evidence**

1. Make evaluation budgets exactly comparable or justify and normalize the difference.
2. Add confidence intervals/effect sizes and a multiple-comparison policy.
3. Provide the missing implementation detail for variable selection and RL.
4. Analyze failure cases and sensitivity beyond favorable defaults.

**P2 — structure and presentation**

1. Compress repeated contribution summaries.
2. Move secondary RL diagnostics and oversized tables to supplementary material.
3. Add a related-work comparison matrix.
4. Harmonize method names, metrics, captions, and terminology.

**P3 — venue-dependent finalization**

1. Select the journal.
2. Verify official author guidelines and recent accepted papers.
3. Apply the official template, length limits, declarations, and submission package.

## Research-Stage Verdict

The manuscript has a viable journal-level spine: an interpretable communication gate for black-box distributed optimization, supported by extensive benchmark, transfer, and application evidence. It is **not ready for journal submission yet** because the target venue is unknown and several central claims depend on technical or metric inconsistencies that must be resolved before stylistic rewriting. The next stage should preserve verified results while prioritizing correctness, comparable endpoints, and reproducibility.
