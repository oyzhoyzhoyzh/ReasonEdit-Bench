#!/usr/bin/env bash
# Recompute the derived artefacts (scores, statistics, figures, LaTeX tables,
# numbers) from the released probe verdicts.
#
# Only the causal metrics are recomputed here, and they need no GPU: every table
# and figure that depends on the probe verdicts is regenerated on a CPU.
#
# The reference metrics (CLIPScore, CLIP-I, DINO-I, LPIPS, Frechet distance) need
# the generated images and a vision backbone. They are skipped by default; set
# REFRESH_AUTO_METRICS=1 to run them as well (requires the images and a GPU).
#
# Control-specific tables (replication, counterfactual, surface, second backbone)
# have their own entry points under code/reasondata/ -- see the README.
set -eu
RIE_ROOT="${RIE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "${RIE_ROOT}/code"
R="${RIE_ROOT}/results"

if [ "${REFRESH_AUTO_METRICS:-0}" = "1" ]; then
    echo "[auto] recomputing reference metrics (needs images + GPU)"
    python3 -u -m reasondata.run_auto --gpu "${GPU:-0}" --out "$R/auto_metrics.jsonl" | tail -2
else
    echo "[auto] skipped: reference metrics need the generated images;"
    echo "       rerun with REFRESH_AUTO_METRICS=1 if they are present"
fi

python3 -u -m reasondata.aggregate --probe-pattern "$R/probes_api_*.jsonl" \
    --out "$R/analysis" | head -10
python3 -u -m reasondata.stats --scores "$R/analysis/scores.jsonl" \
    --human "$R/human_eval/ratings.jsonl" --out "$R/analysis" > /dev/null
python3 -u -m reasondata.figures --scores "$R/analysis/scores.jsonl" \
    --human "$R/human_eval/ratings.jsonl" --out "$R/figures" | tail -3
python3 -u -m reasondata.export_tables --scores "$R/analysis/scores.jsonl" \
    --out "$R/tables" | head -3
python3 -u -m reasondata.make_numbers --scores "$R/analysis/scores.jsonl" | tail -5
python3 -u -m reasondata.make_report --scores "$R/analysis/scores.jsonl" \
    --stats "$R/analysis/stats.json"

echo "derived artefacts refreshed under $R/analysis, $R/figures and $R/tables"
