#!/usr/bin/env bash
# Generation phase.  GPU 0 and GPU 1 are driven independently; each queue is
# safe to re-run because every command is resumable.
set -u
RIE_ROOT="${RIE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd ${RIE_ROOT}/code || exit 1
LOG=${RIE_ROOT}/logs
mkdir -p "$LOG"

echo "[gpu0] InstructPix2Pix"
python3 -u -m reasondata.run_edit --model instructpix2pix --variant base --gpu 0 \
    > "$LOG/gen_ip2p.log" 2>&1

echo "[gpu0] SDXL-Inpaint baseline"
python3 -u -m reasondata.run_edit --model sdxl_inpaint --variant base --gpu 0 \
    > "$LOG/gen_sdxl.log" 2>&1

echo "[gpu0] Qwen-Image-Edit base"
python3 -u -m reasondata.run_edit --model qwen_image_edit --variant base --gpu 0 \
    > "$LOG/gen_qwen_base.log" 2>&1

echo "[gpu0] probing everything generated so far (shard 0/2)"
python3 -u -m reasondata.judge_run --gpu 0 --shard 0/2 --backend local \
    --out ${RIE_ROOT}/results/probes_local_shard0of2.jsonl \
    > "$LOG/judge0.log" 2>&1

echo "[gpu0] finished"
