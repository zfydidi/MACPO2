# Cover Letter (Draft)

**[Date]**

**Editor-in-Chief**  
*[Journal Name — e.g., IEEE Transactions on Systems, Man, and Cybernetics: Systems]*

**Subject:** Submission of manuscript — *Conflict-Triggered Communication for Distributed Black-Box Optimization*

---

Dear Editor,

We submit the enclosed manuscript for consideration as an original research article.

**Existing penalty-based distributed optimizers mainly assume that communication is always invoked.** In network-based distributed optimization with shared edge variables, neighbors negotiate on every outer loop even when local conflict is weak or consensus references are stale. **This work instead formulates communication timing itself as a first-class design problem.** We separate *whether to communicate* from *how to negotiate*: a lightweight conflict proxy and fail-safe bound decide when to open the negotiation channel; only then does the existing MACPO-style penalty negotiation proceed. On the MACPO NDO benchmark (F1–F18), MACPO-style dispatch simulators, and IEEE transmission-network pilots, conflict gating reduces negotiation trigger rates from always-on to a small fraction of outer loops while preserving or improving terminal fitness.

**MACPO serves only as the implementation platform.** Our contribution is the communication architecture and its empirical validation—not a new global optimizer or a claim that reinforcement learning dominates heuristic controllers. Under identical gating, RL, EMA, and fixed penalty schedules are statistically tied on representative benchmarks; RL is retained as a unified default implementation for automation, not as the primary scientific claim.

**The proposed communication architecture is independent of the specific penalty controller.** The penalty module is a plug-in interface: heuristic, model-based, or learned controllers can replace the default PPO head without modifying the gate, fail-safe logic, or negotiation backbone. This design is algorithm-agnostic and applicable beyond MACPO-style penalty negotiation to other distributed black-box settings where communication bandwidth is constrained.

We identify **communication timing as an overlooked design dimension in distributed black-box optimization**, rather than proposing “yet another RL-tuned MACPO variant.” The manuscript includes structural fail-safe analysis, empirically validated skip criteria, gate ablations, cross-paradigm references where code is available, and transfer experiments on dispatch and grid pilots. **All experimental summaries, reproduction scripts, configuration notes, and representative raw logs are provided as supplementary material** (see attached `Supplementary.zip` and `EXPERIMENT_DATA_MAP.md`).

This manuscript is original, has not been published elsewhere, and is not under consideration by another journal. All authors have approved the submission. We declare no conflicts of interest.

We suggest reviewers with expertise in **distributed optimization, communication-efficient coordination, multi-agent / metaheuristic optimization, and smart-grid dispatch**—rather than reviewers focused solely on deep RL algorithm design.

Thank you for your consideration.

Sincerely,

**Yingjie Zhang**  
School of Computer Science, Guangdong University of Technology  
Guangzhou, China

**Xiao-Min Hu** *(Corresponding Author)*  
School of Computer Science, Guangdong University of Technology  
Guangzhou, China  
Email: xmhu@gdut.edu.cn

---

## Notes for author (remove before sending)

1. Replace *[Journal Name]* and adjust tone/length to journal guidelines (some journals want ≤1 page).  
2. Attach: manuscript PDF, supplementary zip, optional highlight figure.  
3. **Do not** lead with “RL-MACPO achieves …”; keep communication-first framing.  
4. If journal uses online submission form instead of letter file, paste paragraphs 2–4 into the “Comments to Editor” box.
