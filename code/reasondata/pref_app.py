"""Interactive human *preference* study server.

    python -m reasondata.pref_app sample --per-pairing 40 --raters 3
    python -m reasondata.pref_app serve --host 127.0.0.1 --port 9030

The server binds to loopback, which is what the Xshell tunnel forwards
(listen localhost:9030 -> target localhost:9030 on the server), so raters open
http://localhost:9030 in their own browser.

It is deliberately built on the Python standard library only: no web framework has
to be installed on the machine that serves the study, which is the machine that
also holds the images.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import posixpath
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import config, pref

WEB_DIR = Path(__file__).resolve().parent / "web"


class Study:
    """Frozen sample + submissions, kept in memory and refreshed from disk."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = data_dir
        self._lock = threading.RLock()
        self.reload()

    def reload(self) -> None:
        with self._lock:
            self.study = pref.load_study(self.data_dir)
            self.trials = {t["id"]: t for t in self.study.get("trials", [])}
            self.assignment = self.study.get("assignment", {})
            self.annotators = self.study.get("annotators", [])
            self.tokens: dict[str, Path] = {}
            for t in self.trials.values():
                for key in ("source", "left", "right"):
                    node = t.get(key)
                    path = node if isinstance(node, str) else (node or {}).get("path")
                    if path:
                        self.tokens[self._token(path)] = Path(path)
            self.submissions = pref.load_submissions(self.data_dir)

    @staticmethod
    def _token(path: str) -> str:
        return hashlib.sha1(str(path).encode()).hexdigest()[:16]

    def url_for(self, path: str | None) -> str | None:
        if not path:
            return None
        token = self._token(path)
        self.tokens.setdefault(token, Path(path))
        return f"/img/{token}"

    def queue(self, rater: str) -> list[str]:
        ids = self.assignment.get(rater)
        if not ids:
            return []
        return sorted(ids, key=lambda tid: self.trials[tid].get("order", 0))

    def done(self, rater: str) -> dict[str, dict]:
        return self.submissions.get(rater, {})

    def progress(self, rater: str | None = None) -> dict:
        out = {}
        for a in self.annotators:
            aid = a["id"]
            out[aid] = {"assigned": len(self.assignment.get(aid, [])),
                        "submitted": len(self.submissions.get(aid, {}))}
        if rater:
            return out.get(rater, {"assigned": 0, "submitted": 0})
        return out

    def public_trial(self, tid: str, rater: str | None) -> dict:
        t = self.trials[tid]
        queue = self.queue(rater) if rater else []
        index = queue.index(tid) if tid in queue else -1
        sub = self.done(rater).get(tid) if rater else None
        return {
            "id": tid,
            "index": index,
            "total": len(queue),
            "instruction": t["instruction"],
            "source_url": self.url_for(t.get("source")),
            "left_url": self.url_for(t["left"]["path"]),
            "right_url": self.url_for(t["right"]["path"]),
            "prev_id": queue[index - 1] if index > 0 else None,
            "next_id": queue[index + 1] if 0 <= index < len(queue) - 1 else None,
            "submission": sub,
            "choices": pref.CHOICES,
        }

    def submit(self, payload: dict) -> dict:
        with self._lock:
            rec = pref.normalise_submission(payload, self.study)
            pref.append_submission(rec, self.data_dir)
            self.submissions.setdefault(rec["rater"], {})[rec["trial_id"]] = rec
            return rec


def _html_page(title: str, body: str) -> bytes:
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><link rel="stylesheet" href="/static/pref.css"></head>
<body class="report"><div class="wrap"><h1>{title}</h1>{body}</div></body></html>""".encode()


def _md_to_rows(md: str) -> str:
    """Very small markdown -> HTML for the report page (tables, headings, lists)."""
    out, in_table = [], False
    for line in md.splitlines():
        s = line.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if cells and all(set(c) <= set("-: ") for c in cells):
                continue
            tag = "th" if not in_table else "td"
            out.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
            in_table = True
            continue
        if in_table:
            out.append("</table>")
            in_table = False
        if s.startswith("## "):
            out.append(f"<h3>{s[3:]}</h3>")
        elif s.startswith("# "):
            continue
        elif s.startswith("> "):
            out.append(f"<p class='note'>{s[2:]}</p>")
        elif s.startswith("- "):
            out.append(f"<p>• {s[2:]}</p>")
        elif s:
            out.append(f"<p>{s}</p>")
    if in_table:
        out.append("</table>")
    return "".join(out)


def make_handler(store: Study):
    class Handler(BaseHTTPRequestHandler):
        server_version = "ReasonEditPref/1.0"

        # ------------------------------------------------------------ helpers --
        def log_message(self, fmt, *args):  # keep the console quiet
            pass

        def _send(self, code: int, body: bytes, ctype: str = "application/json",
                  extra: dict | None = None) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, obj, code: int = 200) -> None:
            self._send(code, json.dumps(obj, ensure_ascii=False).encode())

        def _file(self, path: Path) -> None:
            if not path.exists() or not path.is_file():
                self._send(404, b"not found", "text/plain")
                return
            ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self._send(200, path.read_bytes(), ctype)

        # --------------------------------------------------------------- GET --
        def do_GET(self):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            path = u.path
            try:
                if path in ("/", "/index.html"):
                    self._file(WEB_DIR / "pref.html")
                elif path.startswith("/static/"):
                    name = posixpath.basename(path)
                    self._file(WEB_DIR / name)
                elif path.startswith("/img/"):
                    token = posixpath.basename(path)
                    target = store.tokens.get(token)
                    if not target:
                        self._send(404, b"unknown image", "text/plain")
                    else:
                        self._file(target)
                elif path == "/api/meta":
                    rater = (q.get("rater") or [None])[0]
                    payload = {
                        "annotators": store.annotators,
                        "n_trials": store.study.get("n_trials", 0),
                        "n_gold": store.study.get("n_gold", 0),
                        "raters_per_item": store.study.get("raters_per_item", 0),
                        "progress": store.progress(),
                    }
                    if rater:
                        payload["queue"] = store.queue(rater)
                        payload["done"] = sorted(store.done(rater))
                    self._json(payload)
                elif path.startswith("/api/trial/"):
                    tid = posixpath.basename(path)
                    if tid not in store.trials:
                        self._json({"error": "unknown trial"}, 404)
                        return
                    self._json(store.public_trial(tid, (q.get("rater") or [None])[0]))
                elif path == "/api/report":
                    self._json(pref.compute_report(store.data_dir))
                elif path == "/report":
                    rep = pref.compute_report(store.data_dir)
                    md = pref.report_markdown(rep)
                    body = _md_to_rows(md) + (
                        "<p><a href='/'>返回评价界面</a> · "
                        "<a href='/api/export/submissions.jsonl'>导出原始判定</a></p>")
                    self._send(200, _html_page("人工偏好研究报告", body), "text/html")
                elif path == "/api/export/submissions.jsonl":
                    rows = []
                    for per in store.submissions.values():
                        rows.extend(per.values())
                    body = ("\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
                            + "\n").encode()
                    self._send(200, body, "application/x-ndjson", {
                        "Content-Disposition": "attachment; filename=preference_submissions.jsonl"})
                else:
                    self._send(404, b"not found", "text/plain")
            except Exception as exc:  # noqa: BLE001
                self._json({"error": f"{type(exc).__name__}: {exc}"}, 500)

        # -------------------------------------------------------------- POST --
        def do_POST(self):
            u = urlparse(self.path)
            try:
                length = int(self.headers.get("Content-Length") or 0)
                payload = json.loads(self.rfile.read(length) or b"{}")
                if u.path == "/api/submit":
                    rec = store.submit(payload)
                    self._json({"ok": True, "trial_id": rec["trial_id"],
                                "choice": rec["choice"], "submitted": rec["submitted"]})
                elif u.path == "/api/reload":
                    store.reload()
                    self._json({"ok": True})
                else:
                    self._send(404, b"not found", "text/plain")
            except Exception as exc:  # noqa: BLE001
                self._json({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 400)

    return Handler


# ----------------------------------------------------------------------- cli --
def cmd_sample(args: argparse.Namespace) -> None:
    items = [json.loads(l) for l in (config.BENCH_DIR / args.bench).read_text().splitlines()
             if l.strip()]
    annotators = pref.DEFAULT_ANNOTATORS
    if args.annotators:
        annotators = [{"id": f"p{i+1}", "name": n.strip()}
                      for i, n in enumerate(args.annotators.split(","))]
    study = pref.build_study(items, n_per_pairing=args.per_pairing,
                             raters_per_item=args.raters, annotators=annotators,
                             seed=args.seed, gold_frac=args.gold_frac,
                             data_dir=args.data_dir)
    path = pref.write_study(study, args.data_dir)
    print(f"study: {study['n_trials']} trials ({study['n_gold']} gold) -> {path}")
    print(f"  per pairing: {study['pairings']}")
    print(f"  per annotator: "
          f"{ {a: len(v) for a, v in study['assignment'].items()} }")
    if study["shortfall"]:
        print(f"  shortfall (not enough images): {study['shortfall']}")


def cmd_status(args: argparse.Namespace) -> None:
    rep = pref.compute_report(args.data_dir)
    if not rep.get("ready"):
        print("no study sampled yet")
        return
    c = rep["coverage"]
    print(f"study: {rep['protocol']['n_trials']} trials x "
          f"{rep['protocol']['raters_per_item']} raters")
    print(f"progress: {c['trials_complete']}/{c['trials_total']} complete; "
          f"{c['submissions']}/{c['submissions_expected']} submissions")
    for r, st in c["per_rater"].items():
        g = "—" if st["gold_pass_rate"] is None else f"{100*st['gold_pass_rate']:.0f}%"
        print(f"  {r}: {st['submitted']}/{st['assigned']}  gold {g}")


def cmd_report(args: argparse.Namespace) -> None:
    rep = pref.compute_report(args.data_dir)
    md = pref.report_markdown(rep)
    out = pref.study_dir(args.data_dir) / "report.md"
    out.write_text(md, encoding="utf-8")
    (pref.study_dir(args.data_dir) / "report.json").write_text(
        json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    if args.print:
        print(md)
    else:
        print(f"wrote {out}")


def cmd_serve(args: argparse.Namespace) -> None:
    store = Study(args.data_dir)
    if not store.trials:
        raise SystemExit("no study sampled yet — run `sample` first")
    handler = make_handler(store)
    try:
        httpd = ThreadingHTTPServer((args.host, args.port), handler)
    except OSError as exc:
        print(f"cannot bind {args.host}:{args.port} — {exc}")
        who = port_occupant(args.port)
        if who:
            print("port is held by:\n  " + who)
            print(f"free it (or pick another port with --port / PREF_PORT) and retry.")
        raise SystemExit(2)
    print(f"preference study on http://{args.host}:{args.port}")
    print(f"data dir: {pref.study_dir(args.data_dir)}")
    print(f"trials: {len(store.trials)}  raters: {len(store.annotators)}")
    if args.host in ("127.0.0.1", "localhost"):
        print(f"Xshell tunnel: 源主机 localhost / 侦听端口 {args.port}  ->  "
              f"目标主机 localhost / 目标端口 {args.port}")
        print(f"then open http://localhost:{args.port} on the client")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


def port_occupant(port: int) -> str:
    """Best-effort description of whatever holds ``port`` (for the error message)."""
    try:
        out = subprocess.run(["ss", "-ltnp"], capture_output=True, text=True, timeout=5).stdout
    except Exception:  # noqa: BLE001
        return ""
    lines = [l for l in out.splitlines() if f":{port} " in l]
    if not lines:
        return ""
    pids = set()
    for line in lines:
        for part in line.split("pid=")[1:]:
            pids.add(part.split(",")[0])
    desc = [l.strip() for l in lines]
    for pid in pids:
        try:
            cmd = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode().strip()
            cwd = Path(f"/proc/{pid}/cwd").resolve()
            desc.append(f"pid {pid}: {cmd}   (cwd {cwd})")
        except Exception:  # noqa: BLE001
            pass
    return "\n  ".join(desc)


def cmd_export(args: argparse.Namespace) -> None:
    study = pref.load_study(args.data_dir)
    if args.index:
        print(json.dumps({k: study[k] for k in study if k != "trials"}, ensure_ascii=False, indent=1))
        return
    dst = pref.study_dir(args.data_dir) / "trials.jsonl"
    with dst.open("w") as fh:
        for t in study.get("trials", []):
            fh.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"wrote {dst}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="human preference study server")
    ap.add_argument("--data-dir", default=None)
    sub = ap.add_subparsers(dest="cmd")

    s = sub.add_parser("sample", help="freeze the trials and assignments")
    s.add_argument("--per-pairing", type=int, default=40)
    s.add_argument("--raters", type=int, default=3)
    s.add_argument("--seed", type=int, default=20261010)
    s.add_argument("--gold-frac", type=float, default=0.1)
    s.add_argument("--bench", default="bench.jsonl")
    s.add_argument("--annotators", default=None, help="comma separated display names")
    s.set_defaults(fn=cmd_sample)

    s = sub.add_parser("serve", help="run the web interface")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=9030)
    s.set_defaults(fn=cmd_serve)

    s = sub.add_parser("status", help="print progress")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("report", help="write report.md / report.json")
    s.add_argument("--print", action="store_true")
    s.set_defaults(fn=cmd_report)

    s = sub.add_parser("export", help="dump the trial list (without images)")
    s.add_argument("--index", action="store_true")
    s.set_defaults(fn=cmd_export)

    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help()
        return
    args.fn(args)


if __name__ == "__main__":
    main()
