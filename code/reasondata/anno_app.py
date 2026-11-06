"""Interactive human-annotation server for the B5 protocol.

    python -m reasondata.anno_app sample --n 360 --raters 3   # freeze the sample
    python -m reasondata.anno_app serve --host 127.0.0.1 --port 9001

The server binds to loopback, which is exactly what the Xshell tunnel forwards
(listen localhost:9001 -> localhost:9001 on the server), so annotators open
http://localhost:9001 on their own machine.
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
import uvicorn

from . import anno, config

WEB_DIR = Path(__file__).resolve().parent / "web"


class Store:
    """Sample + submissions with the bench kept in memory."""

    def __init__(self, data_dir: str | Path | None = None, bench: str = "bench.jsonl",
                 surface: str = "surface.jsonl") -> None:
        self.data_dir = anno.anno_dir(data_dir)
        self.bench, self.surface = bench, surface
        self._lock = threading.RLock()
        self.sample = anno.load_sample(self.data_dir)
        self.items = {it["id"]: it for it in anno.load_pool((bench, surface))}
        self._reload()

    # ---------------------------------------------------------------- state --
    def _reload(self) -> None:
        with self._lock:
            self.submissions = anno.load_submissions(self.data_dir)
            self._mtime = self._submission_mtime()

    def _submission_mtime(self) -> float:
        latest = 0.0
        for path in anno.submissions_dir(self.data_dir).glob("*.jsonl"):
            latest = max(latest, path.stat().st_mtime)
        return latest

    def refresh(self) -> None:
        if self._submission_mtime() > self._mtime:
            self._reload()

    def annotators(self) -> list[dict]:
        return anno.annotators_of(self.sample)

    def queue(self, annotator: str) -> list[str]:
        return list(self.sample["assignment"].get(annotator, []))

    def done(self, annotator: str) -> dict[str, dict]:
        self.refresh()
        return self.submissions.get(annotator, {})

    def item(self, item_id: str) -> dict:
        it = self.items.get(item_id)
        if it is None:
            raise HTTPException(404, f"unknown item {item_id}")
        return it

    def submit(self, payload: dict) -> dict:
        annotator = (payload.get("annotator") or "").strip()
        item_id = payload.get("item_id")
        roster = {a["id"] for a in self.annotators()}
        if annotator not in roster:
            raise HTTPException(400, f"annotator {annotator!r} not in roster")
        if item_id not in self.queue(annotator):
            raise HTTPException(403, f"item {item_id} is not assigned to {annotator}")
        item = self.item(item_id)
        rec = anno.normalise_submission({**payload, "annotator": annotator}, self.sample, item)
        rec["received"] = anno.now_iso()
        with self._lock:
            anno.append_submission(rec, self.data_dir)
            self.submissions.setdefault(annotator, {})[item_id] = rec
            self._mtime = self._submission_mtime()
        return rec


def create_app(data_dir: str | Path | None = None) -> FastAPI:
    store = Store(data_dir)
    app = FastAPI(title="ReasonEdit-Bench 人工标注 (B5)")
    app.state.store = store

    # ------------------------------------------------------------- static ---
    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        return HTMLResponse((WEB_DIR / "annotate.html").read_text())

    @app.get("/favicon.ico")
    def favicon():
        return JSONResponse({}, status_code=204)

    @app.get("/static/{name}")
    def static(name: str):
        path = (WEB_DIR / name).resolve()
        if WEB_DIR not in path.parents or not path.exists():
            raise HTTPException(404, "not found")
        media = {
            ".css": "text/css",
            ".js": "application/javascript",
            ".html": "text/html",
        }.get(path.suffix, "application/octet-stream")
        return FileResponse(path, media_type=media)

    @app.get("/api/image/{image_id}")
    def image(image_id: str):
        if not image_id.replace("-", "").replace("_", "").isalnum():
            raise HTTPException(400, "bad image id")
        path = config.BENCH_IMAGES / f"{image_id}.jpg"
        if not path.exists():
            raise HTTPException(404, f"no image {image_id}")
        return FileResponse(path, media_type="image/jpeg")

    # --------------------------------------------------------------- api ----
    @app.get("/api/state")
    def state(annotator: str | None = Query(None)):
        roster = store.annotators()
        sample = store.sample
        info: dict[str, Any] = {
            "annotators": roster,
            "protocol": {
                "n_items": sample["n_items"],
                "raters_per_item": sample["raters_per_item"],
                "seed": sample["seed"],
                "created": sample["created"],
                "by_type": sample["by_type"],
                "by_domain": sample["by_domain"],
                "by_pool": sample["by_pool"],
            },
        }
        if annotator:
            done = store.done(annotator)
            queue = store.queue(annotator)
            info["annotator"] = annotator
            info["queue"] = [{"item_id": i, "done": i in done} for i in queue]
            info["progress"] = {"done": sum(1 for i in queue if i in done), "total": len(queue)}
            info["server_time"] = anno.now_iso()
        return info

    @app.get("/api/item/{item_id}")
    def get_item(item_id: str, annotator: str | None = Query(None)):
        item = store.item(item_id)
        queue = store.queue(annotator) if annotator else []
        index = queue.index(item_id) if item_id in queue else -1
        prev_id = queue[index - 1] if index > 0 else None
        next_id = queue[index + 1] if 0 <= index < len(queue) - 1 else None
        sub = store.done(annotator).get(item_id) if annotator else None
        return anno.public_item(item, index, len(queue), prev_id, next_id, sub)

    @app.post("/api/submit")
    def submit(payload: dict = Body(...)):
        rec = store.submit(payload)
        return {"ok": True, "submitted": rec["submitted"], "record": {
            "item_id": rec["item_id"],
            "scm_verdict": rec["scm"]["verdict"],
            "chain_verdict": rec["chain"]["verdict"],
        }}

    @app.get("/api/report")
    def report():
        return anno.compute_report(store.data_dir, store.bench, store.surface)

    @app.get("/api/export/submissions.jsonl")
    def export():
        rows = []
        for per_item in anno.load_submissions(store.data_dir).values():
            rows.extend(per_item.values())
        body = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n"
        return PlainTextResponse(
            body,
            media_type="application/x-ndjson",
            headers={"Content-Disposition": "attachment; filename=submissions.jsonl"},
        )

    @app.get("/report", response_class=HTMLResponse)
    def report_page():
        rep = anno.compute_report(store.data_dir, store.bench, store.surface)
        md = anno.report_markdown(rep)
        body = md.split("\n", 1)[1] if md.startswith("#") else md
        rows = []
        for line in body.splitlines():
            if line.startswith("|"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                if cells and all(set(c) <= set("-: ") for c in cells):
                    continue  # markdown table separator
                rows.append(
                    "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"
                )
            elif line.startswith("##"):
                rows.append(f"<h3>{line.lstrip('# ').strip()}</h3>")
            elif line.startswith("#"):
                rows.append(f"<h2>{line.lstrip('# ').strip()}</h2>")
            elif line.startswith("> "):
                rows.append(f"<p class=note>{line[2:]}</p>")
            elif line.startswith("- "):
                rows.append(f"<p>{line[2:]}</p>")
            elif line.strip():
                rows.append(f"<p>{line}</p>")
        html = f"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<title>人工标注报告</title><link rel=stylesheet href=/static/style.css></head>
<body class=report><div class=wrap><h1>人工标注协议报告（B5）</h1>
<p class=hint>数据实时汇总自 <code>results/annotation/submissions/</code>；
完整报告见 <code>results/annotation/report.md</code>。
<a href="/">返回标注界面</a> · <a href="/api/export/submissions.jsonl">导出原始标注</a></p>
{"".join(rows)}</div></body></html>"""
        return HTMLResponse(html)

    return app


# ------------------------------------------------------------------- cli ------


def cmd_sample(args: argparse.Namespace) -> None:
    pools = tuple(args.pool.split(","))
    items = anno.load_pool(pools)
    annotators = anno.DEFAULT_ANNOTATORS
    if args.annotators:
        annotators = [
            {"id": f"a{i+1}", "name": name}
            for i, name in enumerate(args.annotators.split(","))
        ]
    sample = anno.build_sample(items, n=args.n, seed=args.seed,
                               raters_per_item=args.raters, annotators=annotators)
    path = anno.write_sample(sample, args.data_dir)
    per_ann = {a: len(v) for a, v in sample["assignment"].items()}
    print(f"pool {len(items)} items -> sample {sample['n_items']} items at {path}")
    print(f"  raters/item={sample['raters_per_item']}  per annotator: {per_ann}")
    print(f"  by type: {sample['by_type']}")
    print(f"  by pool: {sample['by_pool']}")


def cmd_status(args: argparse.Namespace) -> None:
    rep = anno.compute_report(args.data_dir)
    cov, p = rep["coverage"], rep["protocol"]
    print(f"sample: {p['n_items']} items x {p['raters_per_item']} raters "
          f"({p['n_annotators']} annotators)")
    print(f"progress: {cov['items_with_full_k_raters']}/{p['n_items']} items complete; "
          f"{cov['item_annotations_submitted']}/{cov['item_annotations_expected']} submissions")
    for ann, st in cov["per_annotator"].items():
        print(f"  {ann}: {st['submitted']}/{st['assigned']}")
    for key, val in rep["primary"].items():
        print(f"  {key}: {val}")


def cmd_serve(args: argparse.Namespace) -> None:
    app = create_app(args.data_dir)
    print(f"annotation server on http://{args.host}:{args.port}")
    print(f"data dir: {anno.anno_dir(args.data_dir)}")
    if args.host in ("127.0.0.1", "localhost"):
        print("Xshell tunnel: listen localhost:%d -> target localhost:%d" % (args.port, args.port))
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level,
                access_log=args.access_log)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="human annotation server (review item B5)")
    ap.add_argument("--data-dir", default=None)
    sub = ap.add_subparsers(dest="cmd")

    s = sub.add_parser("sample", help="freeze the stratified sample and assignments")
    s.add_argument("--n", type=int, default=360)
    s.add_argument("--seed", type=int, default=20260926)
    s.add_argument("--raters", type=int, default=3, help="annotators per item")
    s.add_argument("--pool", default="bench.jsonl,surface.jsonl")
    s.add_argument("--annotators", default=None, help="comma separated display names")
    s.set_defaults(fn=cmd_sample)

    s = sub.add_parser("serve", help="run the web interface")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=9001)
    s.add_argument("--log-level", default="info")
    s.add_argument("--access-log", action="store_true")
    s.set_defaults(fn=cmd_serve)

    s = sub.add_parser("status", help="print progress and the three kappas")
    s.set_defaults(fn=cmd_status)

    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help()
        return
    args.fn(args)


if __name__ == "__main__":
    main()
