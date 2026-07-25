# Style Profile

## Target scene

- English IEEE journal article; exact journal and article category remain TBD.
- Use `IEEEtran` as a provisional formatting baseline, not as evidence that the
  current conference layout satisfies the eventual journal requirements.
- Write for reviewers in distributed optimization, evolutionary computation,
  networked systems, and black-box optimization.

## Controlling narrative

The paper should be organized around one question: **when is another
shared-variable negotiation round worth its communication cost in distributed
black-box NDO?** The conflict gate is the primary contribution. Variable
selection, negotiation operators, and penalty adaptation are supporting modules.
RL must remain subordinate and must not be presented as the source of the main
communication reduction.

## Journal-level structure

1. Introduction: physical communication constraint -> black-box NDO setting ->
   precise timing gap -> bounded contributions and evidence.
2. Related work: distinguish the decision layer used by gradient/event-triggered
   methods from explicit shared-variable negotiation in black-box NDO.
3. Problem formulation: define communication, negotiation, conflict, evaluation
   budget, and the optimization objective without conflating them.
4. Method: gate and assumptions first; scoped guarantees second; variable
   selection/negotiation third; auxiliary penalty controller last.
5. Experiments: mechanism isolation -> matched-budget benchmarks ->
   communication-quality trade-off -> theory checks -> transfer -> applications.
6. Discussion: interpret gains, failures, wall-time effects, consensus-critical
   cases, and theory boundaries separately from the conclusion.
7. Conclusion: calibrated achievement, operating envelope, and open problems.

## Rhetorical rules

- Begin sections and result subsections with the contribution promise being
  tested; end them with the bounded conclusion supported by that evidence.
- Use promise-evidence contribution bullets rather than listing modules.
- Prefer precise contrast: prior work may decide when to exchange gradients,
  models, or consensus states; this work schedules explicit negotiation of
  shared variables in a gradient-free setting.
- Treat default-gate failures and recovery through tighter \(K\) as part of the
  operating envelope, not as details to hide.
- Do not convert negotiation-trigger reduction into claims about bytes, energy,
  latency, or monetary cost without direct measurements.

## Terminology

Use consistently:

- `communication trigger rate`
- `negotiation round`
- `shared-variable conflict`
- `matched evaluation budget`
- `gate-level fail-safe drift bound`
- `single-round penalized-objective skip bound`
- `linearized intermittent-consensus rate`

Do not use communication, synchronization, exchange, and negotiation
interchangeably when they refer to different operations.

## Claim calibration

Allowed when verified:

- large trigger reductions under the tested matched-budget protocol;
- preserved or improved terminal fitness on most tested benchmarks;
- bounded gate-level behavior under the stated assumptions;
- unchanged gate interface across the tested negotiation operators and MASOIE.

Avoid or soften:

- global convergence or global optimality of the full black-box optimizer;
- universal superiority over all periodic/random/event-triggered schedules;
- a field-wide first claim before citation-level novelty verification;
- protocol-agnostic compatibility beyond the tested settings;
- deployment-level communication savings.

## Sentence and paragraph style

- Formal, compact IEEE journal English with direct subject-verb sentences.
- One technical purpose per paragraph.
- Define symbols before use and state conditions next to conclusions.
- Attach comparison denominators and evaluation conditions to numerical claims.
- Use evidence-linked transitions such as “To isolate the gate” and “To assess
  transfer beyond penalty negotiation.”
- Avoid promotional adjectives, vague novelty statements, and AI-like repeated
  summary sentences.

## Figure and table role

- Every main-text figure or table must validate a stated contribution promise.
- Retain only the smallest evidence set necessary in the main article.
- Move extended tables, implementation diagnostics, drift summaries, and
  detailed scenario definitions to appendices or supplementary material.
- Plot files are not independent evidence; numerical captions must trace to the
  corresponding JSON/CSV/TXT artifacts.

## Unresolved venue-dependent requirements

The following must be revisited after the target journal is selected: page or
word limit, abstract length, keyword count, section policy, graphical abstract,
supplement rules, data/code availability language, reference style, and
double-column/single-column submission format.
