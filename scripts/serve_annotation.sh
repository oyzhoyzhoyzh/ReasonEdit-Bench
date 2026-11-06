#!/usr/bin/env bash
# B5 human-annotation server helper.
#
#   bash scripts/serve_annotation.sh sample [n] [raters]   # freeze the sample
#   bash scripts/serve_annotation.sh start                 # serve on 127.0.0.1:9001
#   bash scripts/serve_annotation.sh status                # progress + three kappas
#   bash scripts/serve_annotation.sh report                # write report files
#   bash scripts/serve_annotation.sh stop                  # stop the server
set -euo pipefail

RIE_ROOT="${RIE_ROOT:-${RIE_ROOT}}"
HOST="${ANNO_HOST:-127.0.0.1}"
PORT="${ANNO_PORT:-9001}"
LOG_DIR="$RIE_ROOT/logs"
PID_FILE="$LOG_DIR/annotation_server.pid"
LOG_FILE="$LOG_DIR/annotation_server.log"

cd "$RIE_ROOT/code"   # the package is imported from here, like the other phase scripts
mkdir -p "$LOG_DIR"

cmd="${1:-start}"
shift || true

case "$cmd" in
  sample)
    n="${1:-360}"
    raters="${2:-3}"
    python -m reasondata.anno_app sample --n "$n" --raters "$raters"
    ;;
  start)
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "already running (pid $(cat "$PID_FILE"))"
    else
      # setsid + nohup: the server must outlive the shell (and the SSH session)
      setsid nohup python -m reasondata.anno_app serve --host "$HOST" --port "$PORT" \
        >"$LOG_FILE" 2>&1 < /dev/null &
      echo $! >"$PID_FILE"
      sleep 2
      echo "started pid $(cat "$PID_FILE") -> http://$HOST:$PORT  (log: $LOG_FILE)"
    fi
    echo
    echo "Xshell tunnel: 源主机 localhost / 侦听端口 $PORT  ->  目标主机 localhost / 目标端口 $PORT"
    echo "then open http://localhost:$PORT on the client"
    ;;
  stop)
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      kill "$(cat "$PID_FILE")" && echo "stopped pid $(cat "$PID_FILE")"
    else
      echo "not running"
    fi
    rm -f "$PID_FILE"
    ;;
  status)
    python -m reasondata.anno_app status
    ;;
  report)
    python -m reasondata.anno_report --print
    ;;
  *)
    echo "usage: $0 {sample [n] [raters]|start|stop|status|report}" >&2
    exit 2
    ;;
esac
