#!/usr/bin/env bash
# ============================================================================
# run_paper_scenarios.sh — 附录 V/VI 配对实验（MACPO vs RL-MACPO，统一协议）
#
# 用法: bash scripts/run_paper_scenarios.sh [runs=5]
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ALGO="$ROOT/algorithms"
RUNS="${1:-5}"
OUTPUT_ROOT="$ROOT/output/paper_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_ROOT"

export MACPO_PAIRED=1

MACPO_BIN="$ALGO/MACPO_sourcecode/build/MACPO_ndo"
RL_BIN="$ALGO/RL-MACPO/build/RL_MACPO_ndo"

for bin in "$MACPO_BIN" "$RL_BIN"; do
    [[ -x "$bin" ]] || { echo "ERROR: $bin 未编译, 请先 bash setup.sh"; exit 1; }
done

parse_result() {
    local log="$1" algo="$2"
    grep '\[RESULT\]' "$log" 2>/dev/null | tail -1 | sed "s/.*algorithm=${algo} //" || true
}

run_scenario() {
    local scenario="$1" ranks="$2"
    local out="$OUTPUT_ROOT/$scenario"
    mkdir -p "$out/MACPO" "$out/RL-MACPO"

    echo ""
    echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
    echo " 场景: $scenario  (mpirun -n $ranks)"
    echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"

    for i in $(seq 1 "$RUNS"); do
        local seed=$(( $(date +%s) + i * 1000 + RANDOM ))
        local mout="$out/MACPO/run_${i}"
        local rout="$out/RL-MACPO/run_${i}"
        mkdir -p "$mout" "$rout"

        echo "  [PAIR $i/$RUNS] seed=$seed"
        cd "$ALGO/MACPO_sourcecode"
        MACPO_PAIR_SEED="$seed" MACPO_PAIRED=1 \
            mpirun -n "$ranks" --oversubscribe -x MACPO_PAIR_SEED -x MACPO_PAIRED \
                "$MACPO_BIN" "$scenario" LLSO "$mout/" \
                > "$mout/run.log" 2>&1

        cd "$ALGO/RL-MACPO"
        MACPO_PAIR_SEED="$seed" MACPO_PAIRED=1 \
            mpirun -n "$ranks" --oversubscribe -x MACPO_PAIR_SEED -x MACPO_PAIRED \
                "$RL_BIN" "$scenario" Full "$rout/" \
                > "$rout/run.log" 2>&1

        echo "    MACPO    $(parse_result "$mout/run.log" MACPO)"
        echo "    RL-MACPO $(parse_result "$rout/run.log" RL-MACPO)"
    done

    python3 - "$out" "$RUNS" "$scenario" <<'PY'
import json, re, sys
from datetime import datetime, timezone
from pathlib import Path

out = Path(sys.argv[1])
runs = int(sys.argv[2])
scenario = sys.argv[3]
pat = re.compile(
    r"f_pure=([0-9.eE+-]+)\s+best_f_pure=([0-9.eE+-]+)\s+"
    r"eva=(\d+)\s+wall_ms=(\d+)\s+outer_iters=(\d+)\s+"
    r"comm_triggers=(\d+)\s+comm_rate=([0-9.]+)"
)

def load(sub, algo):
    rows = []
    for i in range(1, runs + 1):
        log = out / sub / f"run_{i}" / "run.log"
        if not log.exists():
            rows.append({"run_id": i, "missing": True})
            continue
        hits = [pat.search(l.split(f"algorithm={algo}", 1)[-1])
                for l in log.read_text(errors="replace").splitlines()
                if "[RESULT]" in l and f"algorithm={algo}" in l]
        hits = [h for h in hits if h]
        if not hits:
            rows.append({"run_id": i, "missing": True})
            continue
        m = hits[-1]
        rows.append({
            "run_id": i,
            "f_pure": float(m.group(1)),
            "best_f_pure": float(m.group(2)),
            "eva_count": int(m.group(3)),
            "wall_ms": int(m.group(4)),
            "outer_iters": int(m.group(5)),
            "comm_triggers": int(m.group(6)),
            "comm_rate": float(m.group(7)),
        })
    return rows

def agg(rows):
    ok = [r for r in rows if not r.get("missing")]
    if not ok:
        return {"n": 0}
    def mean(k):
        return sum(r[k] for r in ok) / len(ok)
    return {
        "n": len(ok),
        "f_pure_mean": mean("f_pure"),
        "best_f_pure_mean": mean("best_f_pure"),
        "comm_rate_mean": mean("comm_rate"),
        "wall_ms_mean": mean("wall_ms"),
        "eva_count_mean": mean("eva_count"),
        "outer_iters_mean": mean("outer_iters"),
    }

macpo, rl = load("MACPO", "MACPO"), load("RL-MACPO", "RL-MACPO")
summary = {
    "scenario": scenario,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "runs": runs,
    "MACPO": agg(macpo),
    "RL-MACPO": agg(rl),
    "rows": [{"algorithm": "MACPO", **r} for r in macpo]
            + [{"algorithm": "RL-MACPO", **r} for r in rl],
}
if summary["MACPO"].get("n") and summary["RL-MACPO"].get("n"):
    m0, r0 = summary["MACPO"]["best_f_pure_mean"], summary["RL-MACPO"]["best_f_pure_mean"]
    summary["best_f_pure_improvement_pct"] = (m0 - r0) / abs(m0) * 100 if m0 else 0
    m1, r1 = summary["MACPO"]["f_pure_mean"], summary["RL-MACPO"]["f_pure_mean"]
    summary["f_pure_improvement_pct"] = (m1 - r1) / abs(m1) * 100 if m1 else 0
    cr0 = summary["MACPO"]["comm_rate_mean"]
    cr1 = summary["RL-MACPO"]["comm_rate_mean"]
    summary["comm_reduction_pct"] = (cr0 - cr1) / cr0 * 100 if cr0 else 0
    summary["protocol"] = {
        "swarm_size": 100,
        "gen_per_d": 3.0,
        "eva_per_d": 20000,
        "optimizer": "LLSO",
        "paired_seed_env": "MACPO_PAIR_SEED",
        "paired_mode_env": "MACPO_PAIRED=1",
    }

(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    "scenario": scenario,
    "MACPO": summary["MACPO"],
    "RL-MACPO": summary["RL-MACPO"],
    "f_pure_improvement_pct": summary.get("f_pure_improvement_pct"),
    "best_f_pure_improvement_pct": summary.get("best_f_pure_improvement_pct"),
    "comm_reduction_pct": summary.get("comm_reduction_pct"),
}, indent=2))
PY
}

run_scenario RESOURCE 10
run_scenario EVDISPATCH 10

# 总览
python3 - "$OUTPUT_ROOT" <<'PY'
import json
from pathlib import Path
import sys
root = Path(sys.argv[1])
overview = {}
for name in ["RESOURCE", "EVDISPATCH"]:
    p = root / name / "summary.json"
    if p.exists():
        overview[name] = json.loads(p.read_text())
(root / "overview.json").write_text(json.dumps(overview, indent=2) + "\n")
print("\n=== 附录 V/VI 配对总览 ===")
print(json.dumps(overview, indent=2, ensure_ascii=False))
print(f"\n[完成] {root}/overview.json")
PY

echo "============================================"
