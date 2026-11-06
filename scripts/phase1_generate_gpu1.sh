#!/usr/bin/env bash
set -u
RIE_ROOT="${RIE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd ${RIE_ROOT}/code || exit 1
LOG=${RIE_ROOT}/logs

# merge the reasoning-plan shards (they are produced with the API backend)
python3 - <<'PY'
import json, time
from pathlib import Path
root = Path('${RIE_ROOT}/results')
out = root / 'plans_all.jsonl'
for _ in range(240):
    parts = sorted(root.glob('plans_shard*.jsonl'))
    if len(parts) >= 2 and all(p.stat().st_size > 0 for p in parts):
        rows = {}
        for p in parts:
            for line in p.read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    rows[r['item_id']] = r
        out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows.values()))
        print('merged', len(rows), 'plans ->', out, flush=True)
        break
    time.sleep(15)
PY

echo "[gpu1] Qwen-Image-Edit + CoT plan"
python3 -u -m reasondata.run_edit --model qwen_image_edit --variant cot --gpu 1 \
    --plan ${RIE_ROOT}/results/plans_all.jsonl > "$LOG/gen_qwen_cot.log" 2>&1

echo "[gpu1] Qwen-Image-Edit oracle-SCM"
python3 -u -m reasondata.run_edit --model qwen_image_edit --variant oracle --gpu 1 \
    > "$LOG/gen_qwen_oracle.log" 2>&1

echo "[gpu1] probing everything generated so far (shard 1/2)"
python3 -u -m reasondata.judge_run --gpu 1 --shard 1/2 --backend local \
    --out ${RIE_ROOT}/results/probes_local_shard1of2.jsonl \
    > "$LOG/judge1.log" 2>&1

echo "[gpu1] finished"
