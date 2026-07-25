# Source Map

## Scope and authority

This map identifies the local evidence that may be used during the PaperSpine
rewrite. Numerical results, theoretical statements, and implementation claims
must remain traceable to these sources. External papers may support positioning
and style, but they must not be used as evidence for this manuscript's own
results.

| Source group | Authoritative path | Role in rewrite | Permitted use | Constraint |
|---|---|---|---|---|
| Current manuscript | `conference_new_ready.tex` | Primary draft and current claim set | Recover structure, equations, tables, citations, captions, and stated conclusions | Do not silently strengthen any claim |
| Current rendered manuscript | `conference_new_ready.pdf` | Visual/layout reference | Check pagination, figure placement, table legibility, and cross-references | TeX source remains authoritative for editable content |
| Prior manuscript | `conference_en_ready.tex` and `conference_en_ready.pdf` | Version history | Recover earlier wording or omitted rationale when consistent with current evidence | Do not reintroduce superseded numbers or claims |
| Scenario supplement | `conference_new_ready_supplement_scenarios.tex` | Additional application evidence and framing | Evaluate whether material belongs in a journal-length main paper or supplement | Include only claims supported by the underlying experiment artifacts |
| Experiment summary | `experiment_summary_zh.tex` and `experiment_summary_zh.pdf` | Human-readable experiment record | Cross-check experiment scope and interpretations | Resolve inconsistencies against raw result files |
| Raw/recomputed results | `media/*.json`, `media/*.csv`, `media/*.txt` | Primary numerical evidence | Verify tables, reported reductions, controller comparisons, sensitivity, scalability, and confidence summaries | Numbers must be recomputed or directly traceable before editing |
| Figures | `media/*.pdf`, `media/*.svg`, `media/*.png` | Visual evidence | Reuse or revise figures after matching them to raw data and manuscript claims | A rendered plot alone is not sufficient evidence for a new numerical claim |
| Local literature set | `references_intro/*.pdf` and `references_intro/README.md` | Background, positioning, and exemplar learning | Support related-work claims and learn journal structure | Bibliographic metadata and claim support require verification |
| Submission audits | `submission/WRITEPAPER_AUDIT.md`, `submission/SYMBOL_CONSISTENCY_REPORT.md`, `submission/REBUTTAL_FAQ.md` | Existing quality-control record | Seed reviewer-risk and consistency checks | Treat as prior analysis, not independent evidence |
| IEEE class/template | `IEEEtran.cls` | Formatting baseline | Preserve IEEE-compatible structure until a specific target journal is selected | Final journal requirements remain unresolved |

## Current rewrite target

- Workflow: rewrite an existing manuscript.
- Draft: `conference_new_ready.tex`.
- Scene: English journal article.
- Provisional venue: IEEE journal, exact title not yet selected.
- Output rule: preserve the original draft; all rewritten artifacts belong
  under `paper_rewriting_output/`.

## Evidence hierarchy

1. Raw or recomputed experiment files.
2. Current TeX equations, algorithms, and tables when consistent with raw data.
3. Experiment notes and prior manuscript versions.
4. Rendered figures and PDFs.
5. External literature for background and structural learning only.

## Known unresolved items

- The exact target journal, article category, page limit, and author guidelines
  have not been specified.
- Citation metadata and sentence-level support must be verified before the final
  bibliography is accepted.
- Any difference between the current manuscript, prior versions, and raw result
  files must be logged rather than reconciled by assumption.
