#!/usr/bin/env bash
# Counterfactual control: score each editor's attempt at the stored causally invalid
# counterfactual against the *original* contract and compare it with its attempt at
# the real instruction.
#
#   bash scripts/phase5_counterfactual.sh
#
# Produces:
#   results/<model>/cf/                            counterfactual edits
#   results/probes_cf_shard{0,1}of2.jsonl          local verdicts (resumable)
#   results/analysis_cf/                           scores under the local judge
#   results/analysis/counterfactual.json           paired comparison
#   paper/tables/counterfactual_table.tex          the paper's table
set -u
RIE_ROOT="${RIE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ROOT=${RIE_ROOT}
LOG="$ROOT/logs"
R="$ROOT/results"

# 1. generate the invalid edit with two editors, one shard per GPU
for gpu in 0 1; do
    (cd "$ROOT/code" && CUDA_VISIBLE_DEVICES=$gpu setsid nohup \
        python3 -u -m reasondata.run_edit --model qwen_image_edit --variant cf \
        --gpu 0 --shard "$gpu/2" > "$LOG/gen_qwen_cf${gpu}.log" 2>&1 < /dev/null &)
done
(cd "$ROOT/code" && CUDA_VISIBLE_DEVICES=1 setsid nohup \
    python3 -u -m reasondata.run_edit --model instructpix2pix --variant cf \
    --gpu 0 > "$LOG/gen_ip2p_cf.log" 2>&1 < /dev/null &)
# wait for both qwen shards (the slow part), then judge
while pgrep -f "run_edit --model qwen_image_edit --variant cf" > /dev/null; do sleep 60; done

# 2. reference metrics for the new runs
(cd "$ROOT/code" && python3 -u -m reasondata.run_auto --gpu 0 \
    --out "$R/auto_metrics.jsonl" >> "$LOG/auto_cf.log" 2>&1)

# 3. judge with the local open-weight judge, one shard per GPU
for gpu in 0 1; do
    (cd "$ROOT/code" && CUDA_VISIBLE_DEVICES=$gpu setsid nohup \
        python3 -u -m reasondata.judge_run --gpu 0 --shard "$gpu/2" \
        --runs qwen_image_edit__cf,instructpix2pix__cf --backend local --batch-size 8 \
        --out "$R/probes_cf_shard${gpu}of2.jsonl" \
        > "$LOG/judge_cf${gpu}.log" 2>&1 < /dev/null &)
done
while pgrep -f "judge_run --gpu 0 --shard" > /dev/null; do sleep 30; done

# 4. score and compare
cd "$ROOT/code" || exit 1
python3 -u -m reasondata.aggregate --probe-pattern "$R/probes_cf_shard*.jsonl" \
    --systems qwen_image_edit__cf,instructpix2pix__cf --out "$R/analysis_cf" > /dev/null
python3 -u -m reasondata.counterfactual \
    --positive "$R/analysis_local/scores.jsonl" --cf "$R/analysis_cf/scores.jsonl" \
    --out "$R/analysis/counterfactual.json" \
    --table "$ROOT/paper/tables/counterfactual_table.tex"
python3 -u -m reasondata.make_numbers --scores "$R/analysis/scores.jsonl" > /dev/null
echo "counterfactual control finished; numbers.tex and the table refreshed"
