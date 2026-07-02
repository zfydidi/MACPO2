# Symbol & Reference Consistency Report

**Manuscript:** `conference_new_ready.tex`  
**Date:** 2026-06-15  
**Scope:** Final proofreading pass before journal submission (no content changes unless noted).

---

## 1. Cross-reference audit (automated)

| Check | Result |
|-------|--------|
| `\ref{}` / `\eqref{}` → `\label{}` | **Pass** — all in-file labels resolve after `\input{media/application_appendix_stats.tex}` |
| Undefined references in `conference_new_ready.log` | **Pass** — none after two-pass compile |
| Hard-coded “Section VII / Table V” | **Pass** — none; all use `\ref{}` |
| Hard-coded equation numbers (“Eq. (25)”) | **Pass** — all use `\eqref{}` |

**Note:** `tab:application_run_stats` is defined in `media/application_appendix_stats.tex` (included via `\input`). Static grep on the main `.tex` alone will flag it as “missing”; compile resolves it correctly.

---

## 2. Notation consistency

| Symbol | Convention in manuscript | Status |
|--------|-------------------------|--------|
| **Global objective** | $F(\mathbf{X})$ in Eq.~\eqref{eq:global_objective}; table captions say “Final global objective $F$” | **Consistent** |
| **Logged pure objective** | $f_{\mathrm{pure}}$ — defined once in §Experimental Notation (line ~348) | **Consistent** |
| **MACPO endpoint on F7–F18** | Penalized archived $F$ (footnote `MACPO$^{\ddagger}$`) | **Explicit** |
| **RL-MACPO endpoint** | Terminal logged $f_{\mathrm{pure}}$ (= $f_{\mathrm{penalty}}$ in archived runs) | **Explicit** |
| **F9/F15 large gaps** | Explained in table caption + Discussion Route~1 | **Consistent** |
| **Trigger rate** | $\bar p_{\mathrm{comm}}$ = fraction of outer loops with $g^t=1$ | **Consistent** |

### Terminology touch-ups applied (this pass)

Replaced ambiguous “communication rate” with **trigger rate** in five prose/caption locations (Q4 roadmap, λ sensitivity, penalty-controller caption, synthesis, IEEE-30 success note). Table column headers **Comm.** retained as shorthand where captions define them as *fraction of outer loops that trigger negotiation*.

---

## 3. Figure / Table / Appendix inventory

All `\ref{fig:...}`, `\ref{tab:...}`, `\ref{app:...}` targets exist. Key appendix chain:

- `app:empirical_drift` → Appendix A  
- `app:rl_controller` → Appendix B (+ subsections `app:rl_traj`, `app:rl_variants`, `app:rl_stability`)  
- `app:applications` → Appendix C  

---

## 4. Items intentionally left as-is

| Item | Rationale |
|------|-----------|
| Table header **Comm.** / **RL comm.** | Space-saving; captions define = trigger rate |
| **negotiation rate** vs **trigger rate** | Both used; negotiation rate = same metric when MACPO always negotiates |
| Unused `\label{}` keys (e.g. `sec:conclusion`, `fig:rl_traj_alpha`) | Harmless; subfigures referenced via parent `fig:rl_traj_metrics` |
| Wall-clock Table `tab:wall_time_f1_f18` | Hard-coded indicative values; documented in `EXPERIMENT_DATA_MAP.md` §6.4 |

---

## 5. Pre-submission manual checklist (human pass)

- [ ] PDF: every figure renders; no “??” references  
- [ ] Author names / affiliations / corresponding author email  
- [ ] Bibliography complete (currently `thebibliography`; switch to `.bib` only if journal requires)  
- [ ] Journal template (page limit, double-column if required) — **Priority 3, last day**  
- [ ] Supplementary zip matches Cover Letter claim  

---

## 6. Verdict

**Ready for submission materials phase.** No blocking reference or notation inconsistencies found. Remaining work is journal formatting and optional human read-through for typos.
