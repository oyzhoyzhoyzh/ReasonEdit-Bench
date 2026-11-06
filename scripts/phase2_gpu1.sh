#!/usr/bin/env bash
# GPU 1 queue: wait for the running CoT generation, refresh the judge, then run
# the verification-driven repair pass and assemble the CausalScaffold system.
set -u
RIE_ROOT="${RIE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd ${RIE_ROOT}/code || exit 1
LOG=${RIE_ROOT}/logs

echo "[gpu1] waiting for the running CoT generation to finish"
while pgrep -f "reasondata.run_edit --model qwen_image_edit --variant cot --gpu 1" > /dev/null; do
    sleep 60
done

echo "[gpu1] refreshing the API judge over the CoT outputs"
python3 -u -m reasondata.judge_run --backend dashscope --model qwen3-vl-plus --shard 0/1 \
    --workers 16 --out ${RIE_ROOT}/results/probes_api_all.jsonl \
    > "$LOG/judge_api3.log" 2>&1

echo "[gpu1] building repair requests"
python3 -u -m reasondata.repair --system qwen_image_edit__cot \
    --source-run ${RIE_ROOT}/results/qwen_image_edit/cot \
    --out ${RIE_ROOT}/results/qwen_image_edit/scaffold_requests.jsonl \
    > "$LOG/repair_build.log" 2>&1
cat "$LOG/repair_build.log"

echo "[gpu1] repair pass"
python3 -u -m reasondata.run_edit --model qwen_image_edit --variant scaffold --gpu 1 \
    --plan ${RIE_ROOT}/results/qwen_image_edit/scaffold_requests.jsonl \
    > "$LOG/gen_qwen_repair.log" 2>&1

echo "[gpu1] assembling the scaffold system"
python3 -u -m reasondata.assemble > "$LOG/assemble.log" 2>&1
cat "$LOG/assemble.log"

echo "[gpu1] judging the scaffold outputs"
python3 -u -m reasondata.judge_run --backend dashscope --model qwen3-vl-plus --shard 0/1 \
    --workers 16 --runs qwen_image_edit__scaffold_full \
    --out ${RIE_ROOT}/results/probes_api_scaffold.jsonl \
    > "$LOG/judge_api_scaffold.log" 2>&1

echo "[gpu1] Qwen-Image-Edit oracle-SCM (shard 1/2)"
python3 -u -m reasondata.run_edit --model qwen_image_edit --variant oracle --gpu 1 \
    --shard 1/2 --out ${RIE_ROOT}/results/qwen_image_edit/oracle_p1 \
    > "$LOG/gen_qwen_oracle1.log" 2>&1

echo "[gpu1] merging oracle shards"
python3 - <<'PY'
import shutil, json
from pathlib import Path
root = Path('${RIE_ROOT}/results/qwen_image_edit')
dest = root / 'oracle'
dest.mkdir(parents=True, exist_ok=True)
manifest = {}
for part in ('oracle_p0', 'oracle_p1'):
    d = root / part
    mf = d / 'manifest.jsonl'
    if not mf.exists():
        continue
    for line in mf.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get('status') != 'ok':
            continue
        src = Path(rec['output'])
        if not src.exists():
            continue
        dst = dest / src.name
        if not dst.exists():
            shutil.copyfile(src, dst)
        rec['output'] = str(dst)
        manifest[rec['item_id']] = rec
(dest / 'manifest.jsonl').write_text(
    "\n".join(json.dumps(r, ensure_ascii=False) for r in manifest.values()))
print('merged', len(manifest), 'oracle outputs')
PY

echo "[gpu1] judging the oracle outputs"
python3 -u -m reasondata.judge_run --backend dashscope --model qwen3-vl-plus --shard 0/1 \
    --workers 16 --runs qwen_image_edit__oracle \
    --out ${RIE_ROOT}/results/probes_api_oracle.jsonl \
    > "$LOG/judge_api_oracle.log" 2>&1
echo "[gpu1] finished"
