# Reviewer Audit

## Reviewer Value Map

| Reviewer concern | Where addressed | Residual risk |
|---|---|---|
| Is this just MACPO + heuristic? | Sandbox A1 + MASOIE A2 + theory B1/B2 | Medium: still embedded in MACPO shell for main benchmarks |
| Does skipping hurt quality? | Prop skip + Fig skip_bound + ablations | Low if h_i vs F distinction kept visible |
| Is gate universal? | Win rates in Fig universality; F2/F4 + K sweep | Low if default-gate limits stated |
| Theory disconnected? | Each prop paired with fig in Sec exp_comm | Low |
| Too long for conference? | 26 pages + appendices | High — venue fit risk |

## Objection Register

| ID | Likely objection | Response in paper | Status |
|---|---|---|---|
| O1 | No global convergence | Explicit disclaimers; linearized consensus only | Mitigated |
| O2 | Gossip underperforms periodic | Panel win-rate + weak mixing discussion | Mitigated |
| O3 | MASOIE n=10 only | Stated in table caption; future work | Open |
| O4 | Page length | Not yet compressed | Open |

## Editorial Fit

Target: IEEE conference (TEVC-style evolutionary/distributed optimization). Contribution mix (method + theory + systems validation) fits if compressed to page limit.
