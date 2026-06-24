#!/usr/bin/env bash
# ============================================================================
# run_power.sh — IEEE 标准算例区域电力调度 MACPO vs RL-MACPO 配对实验
#
# 用法: bash scripts/run_power.sh [CASE] [runs=5] [mode=paired]
#   CASE: IEEE14 | IEEE30 | IEEE57 | IEEE118  (默认 IEEE14)
#   或:  bash scripts/run_power.sh ALL 5 paired   # 依次跑四个算例
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ALGO="$ROOT/algorithms"
CASE="${1:-IEEE14}"
RUNS="${2:-5}"
MODE="${3:-paired}"

export MACPO_PAIRED=1

ranks_for_case() {
    case "$1" in
        IEEE14|POWER14|IEEE30|POWER30|IEEE57|POWER57) echo 4 ;;
        IEEE118|POWER118) echo 8 ;;
        *) echo 0 ;;
    esac
}

run_one_case() {
    local CASE_NAME="$1"
    local NRANKS
    NRANKS=$(ranks_for_case "$CASE_NAME")
    if [[ "$NRANKS" == "0" ]]; then
        echo "ERROR: unknown CASE '$CASE_NAME'"
        exit 1
    fi

    local OUTPUT_DIR="$ROOT/output/power_${CASE_NAME}_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$OUTPUT_DIR"

    echo "============================================"
    echo " $CASE_NAME 区域电力调度 MACPO vs RL-MACPO"
    echo " ranks: $NRANKS  runs: $RUNS  mode: $MODE"
    echo " output: $OUTPUT_DIR"
    echo "============================================"

    parse_result() {
        local log="$1" algo="$2"
        grep '\[RESULT\]' "$log" 2>/dev/null | tail -1 | sed "s/.*algorithm=${algo} //" || true
    }

    local MACPO_BIN="$ALGO/MACPO_sourcecode/build/MACPO_power"
    local RL_BIN="$ALGO/RL-MACPO/build/RL_MACPO_power"

    run_paired() {
        local run_id="$1" seed="$2"
        local macpo_out="$OUTPUT_DIR/MACPO/run_${run_id}"
        local rl_out="$OUTPUT_DIR/RL-MACPO/run_${run_id}"
        mkdir -p "$macpo_out" "$rl_out"

        echo "  [PAIR $run_id] MACPO (seed=$seed)"
        cd "$ALGO/MACPO_sourcecode"
        MACPO_PAIR_SEED="$seed" MACPO_PAIRED=1 \
            mpirun -n "$NRANKS" --oversubscribe -x MACPO_PAIR_SEED -x MACPO_PAIRED \
                "$MACPO_BIN" "$CASE_NAME" LLSO "$macpo_out/" \
                > "$macpo_out/run.log" 2>&1

        echo "  [PAIR $run_id] RL-MACPO (seed=$seed)"
        cd "$ALGO/RL-MACPO"
        MACPO_PAIR_SEED="$seed" MACPO_PAIRED=1 \
            mpirun -n "$NRANKS" --oversubscribe -x MACPO_PAIR_SEED -x MACPO_PAIRED \
                "$RL_BIN" "$CASE_NAME" Full "$rl_out/" \
                > "$rl_out/run.log" 2>&1

        local mr rl
        mr=$(parse_result "$macpo_out/run.log" "MACPO")
        rl=$(parse_result "$rl_out/run.log" "RL-MACPO")
        echo "       MACPO    ${mr:-N/A}"
        echo "       RL-MACPO ${rl:-N/A}"
    }

    for i in $(seq 1 "$RUNS"); do
        SEED=$(( $(date +%s) + i * 1000 + RANDOM ))
        run_paired "$i" "$SEED"
    done

    python3 - "$OUTPUT_DIR" "$RUNS" "$CASE_NAME" <<'PY'
import json, re, sys
from datetime import datetime, timezone
from pathlib import Path

out_dir = Path(sys.argv[1])
runs = int(sys.argv[2])
case_name = sys.argv[3]
pat = re.compile(
    r"f_pure=([0-9.eE+-]+)\s+best_f_pure=([0-9.eE+-]+)\s+"
    r"eva=(\d+)\s+wall_ms=(\d+)\s+outer_iters=(\d+)\s+"
    r"comm_triggers=(\d+)\s+comm_rate=([0-9.]+)"
)

def load_algo_rows(sub, algo_key):
    rows = []
    for i in range(1, runs + 1):
        log = out_dir / sub / f"run_{i}" / "run.log"
        if not log.exists():
            rows.append({"run_id": i, "missing": True})
            continue
        hits = [pat.search(line.split("algorithm=" + algo_key, 1)[-1])
                for line in log.read_text(errors="replace").splitlines()
                if "[RESULT]" in line and f"algorithm={algo_key}" in line]
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
        "simulator": f"power_{case_name.lower()}",
    }

macpo = load_algo_rows("MACPO", "MACPO")
rl = load_algo_rows("RL-MACPO", "RL-MACPO")
overall_macpo, overall_rl = agg(macpo), agg(rl)

summary = {
    "experiment": f"power_{case_name.lower()}_macpo_vs_rl",
    "created_at": datetime.now(timezone.utc).isoformat(),
    "scenario": case_name,
    "runs": runs,
    "metric": "f_pure=global_eva(globalBest)",
    "MACPO": overall_macpo,
    "RL-MACPO": overall_rl,
    "rows": [{"algorithm": "MACPO", **r} for r in macpo]
            + [{"algorithm": "RL-MACPO", **r} for r in rl],
}
if overall_macpo.get("n") and overall_rl.get("n"):
    m0, r0 = overall_macpo["f_pure_mean"], overall_rl["f_pure_mean"]
    summary["f_pure_improvement_pct"] = (m0 - r0) / m0 * 100 if m0 else 0.0
    m1, r1 = overall_macpo["best_f_pure_mean"], overall_rl["best_f_pure_mean"]
    summary["best_f_pure_improvement_pct"] = (m1 - r1) / abs(m1) * 100 if m1 else 0.0
    cr0, cr1 = overall_macpo["comm_rate_mean"], overall_rl["comm_rate_mean"]
    summary["comm_reduction_pct"] = (cr0 - cr1) / cr0 * 100 if cr0 else 0.0

(out_dir / "summary.json").write_text(
    json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
)
print(json.dumps({
    "scenario": case_name,
    "MACPO": overall_macpo,
    "RL-MACPO": overall_rl,
    "best_f_pure_improvement_pct": summary.get("best_f_pure_improvement_pct"),
    "comm_reduction_pct": summary.get("comm_reduction_pct"),
}, indent=2, ensure_ascii=False))
print(f"\n[完成] {out_dir / 'summary.json'}")
PY
}

for bin in "$ALGO/MACPO_sourcecode/build/MACPO_power" \
           "$ALGO/RL-MACPO/build/RL_MACPO_power"; do
    [[ -x "$bin" ]] || { echo "ERROR: $bin 未编译, 请先 bash setup.sh"; exit 1; }
done

if [[ "$CASE" == "ALL" ]]; then
    for c in IEEE14 IEEE30 IEEE57 IEEE118; do
        run_one_case "$c"
    done
else
    run_one_case "$CASE"
fi

echo "============================================"
