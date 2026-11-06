#!/usr/bin/env bash
# Recompute every derived artefact (reference metrics, scores, statistics,
# figures, LaTeX tables, numbers) from the released probe verdicts.
#
# Everything below the generation step needs no GPU and no model weights.
set -eu
RIE_ROOT="${RIE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "${RIE_ROOT}/code"
R="${RIE_ROOT}/results"

python3 -u -m reasondata.run_auto --gpu "${GPU:-0}" --out "$R/auto_metrics.jsonl" | tail -2
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
