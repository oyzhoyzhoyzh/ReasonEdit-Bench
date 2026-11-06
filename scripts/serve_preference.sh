#!/usr/bin/env bash
# Human *preference* study server.
#
#   bash scripts/serve_preference.sh sample [per-pairing] [raters]
#   bash scripts/serve_preference.sh start          # serve on 127.0.0.1:9030
#   bash scripts/serve_preference.sh status         # progress + attention checks
#   bash scripts/serve_preference.sh report         # write report.md / report.json
#   bash scripts/serve_preference.sh stop
#   bash scripts/serve_preference.sh who            # who holds the port (if anyone)
#   bash scripts/serve_preference.sh takeover       # stop the other study, then start
#
# Xshell tunnel (as configured on the client):
#   源主机 localhost / 侦听端口 9030  ->  目标主机 localhost / 目标端口 9030
# then open http://localhost:9030 on the client.
set -euo pipefail

RIE_ROOT="${RIE_ROOT:-${RIE_ROOT}}"
HOST="${PREF_HOST:-127.0.0.1}"
PORT="${PREF_PORT:-9030}"
LOG_DIR="$RIE_ROOT/logs"
PID_FILE="$LOG_DIR/preference_server.pid"
LOG_FILE="$LOG_DIR/preference_server.log"
PYTHON="${PYTHON:-python}"
SELF="$(readlink -f "$0")"      # survives the `cd` below

cd "$RIE_ROOT/code"          # the package is imported from here, like the other scripts
mkdir -p "$LOG_DIR"

cmd="${1:-start}"
shift || true

port_pids() {
  ss -ltnp 2>/dev/null | awk -v p=":$PORT" '$4 ~ p"$" {print}' \
    | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u
}

case "$cmd" in
  sample)
    per="${1:-40}"
    raters="${2:-3}"
    "$PYTHON" -m reasondata.pref_app sample --per-pairing "$per" --raters "$raters"
    ;;
  start)
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "already running (pid $(cat "$PID_FILE"))"
    else
      # setsid + nohup so the server outlives this shell and the SSH session
      setsid nohup "$PYTHON" -m reasondata.pref_app serve --host "$HOST" --port "$PORT" \
        >"$LOG_FILE" 2>&1 < /dev/null &
      echo $! >"$PID_FILE"
      sleep 2
      echo "started pid $(cat "$PID_FILE")  (log: $LOG_FILE)"
    fi
    echo
    echo "Xshell 隧道：源主机 localhost / 侦听端口 $PORT  ->  目标主机 localhost / 目标端口 $PORT"
    echo "然后在客户端浏览器打开  http://localhost:$PORT"
    ;;
  stop)
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      kill "$(cat "$PID_FILE")" && echo "stopped pid $(cat "$PID_FILE")"
    else
      echo "not running"
    fi
    rm -f "$PID_FILE"
    ;;
  who)
    pids="$(port_pids || true)"
    if [[ -z "$pids" ]]; then
      echo "port $PORT is free"
    else
      for pid in $pids; do
        echo "port $PORT held by pid $pid: $(tr '\0' ' ' < /proc/$pid/cmdline 2>/dev/null)"
        echo "  cwd: $(readlink /proc/$pid/cwd 2>/dev/null)"
      done
    fi
    ;;
  takeover)
    # Stopping another study's server is destructive-ish, so it is never implicit:
    # this command records what it stops and how to bring it back.
    pids="$(port_pids || true)"
    if [[ -z "$pids" ]]; then
      echo "port $PORT is already free"
    else
      for pid in $pids; do
        echo "stopping pid $pid: $(tr '\0' ' ' < /proc/$pid/cmdline 2>/dev/null)"
        echo "  cwd: $(readlink /proc/$pid/cwd 2>/dev/null)"
        kill "$pid"
      done
      sleep 2
      echo "stopped. The stopped service kept its data on disk; restart it from its own"
      echo "project directory if you need it again (the command line is printed above)."
    fi
    "$SELF" start
    ;;
  status)
    "$PYTHON" -m reasondata.pref_app status
    ;;
  report)
    "$PYTHON" -m reasondata.pref_app report --print
    ;;
  *)
    echo "usage: $0 {sample [per-pairing] [raters]|start|stop|status|report}" >&2
    exit 2
    ;;
esac
