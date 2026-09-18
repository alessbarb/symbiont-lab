#!/usr/bin/env bash
set -Eeuo pipefail

# Launch a local Observatory server and a configurable number of residents.
# Usage: ./scripts/run-ecosystem.sh [COUNT] [PORT]

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
if [[ -n "${SYMBIONT_PYTHON:-}" ]]; then
  PYTHON_BIN="$SYMBIONT_PYTHON"
elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
  PYTHON_BIN="$(command -v python3 || true)"
fi
if [[ "$PYTHON_BIN" != */* ]]; then
  PYTHON_BIN="$(command -v "$PYTHON_BIN" || true)"
fi
STATE_DIR="${SYMBIONT_STATE_DIR:-${HOME}/.local/state/symbiont}"
OBS_DIR="${SYMBIONT_OBSERVATORY_DIR:-${STATE_DIR}/observatory}"
COUNT="${1:-4}"
PORT="${2:-8899}"
INTERVAL="${SYMBIONT_INTERVAL:-}"
CHECKPOINT_EVERY="${SYMBIONT_CHECKPOINT_EVERY:-}"
MAX_POPULATION="${SYMBIONT_MAX_POPULATION:-6}"
ENABLE_SLM="${SYMBIONT_ENABLE_SLM:-1}"

usage() {
  cat <<EOF
Uso: $(basename "$0") [NUMERO_DE_SYMBIOTS] [PUERTO]

Ejemplos:
  $(basename "$0") 5
  $(basename "$0") 10 8900

Variables opcionales:
  SYMBIONT_STATE_DIR, SYMBIONT_OBSERVATORY_DIR
  SYMBIONT_INTERVAL (opcional; por defecto usa el valor del CLI)
  SYMBIONT_CHECKPOINT_EVERY (opcional; por defecto usa el valor del CLI)
  SYMBIONT_ENABLE_SLM (opcional; 1 para activar Private SLM, por defecto 1)
  SYMBIONT_PYTHON (opcional: interprete Python a utilizar)
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ ! "$COUNT" =~ ^[1-9][0-9]*$ ]]; then
  echo "Error: el numero de symbiots debe ser un entero positivo: $COUNT" >&2
  exit 2
fi
if [[ ! "$PORT" =~ ^[1-9][0-9]*$ || "$PORT" -gt 65535 ]]; then
  echo "Error: el puerto debe estar entre 1 y 65535: $PORT" >&2
  exit 2
fi
if [[ -z "$PYTHON_BIN" || ! -x "$PYTHON_BIN" ]]; then
  echo "Error: no se encontro un interprete Python ejecutable: ${PYTHON_BIN:-<vacio>}" >&2
  exit 1
fi
if [[ -n "${INTERVAL:-}" || -n "${CHECKPOINT_EVERY:-}" ]]; then
  if ! "$PYTHON_BIN" - "${INTERVAL:-15.0}" "${CHECKPOINT_EVERY:-20}" <<'PY'
import math
import sys

try:
    interval = float(sys.argv[1])
    checkpoint_every = int(sys.argv[2])
except (TypeError, ValueError, OverflowError):
    raise SystemExit(1)
if not math.isfinite(interval) or interval <= 0 or checkpoint_every <= 0:
    raise SystemExit(1)
PY
  then
    echo "Error: SYMBIONT_INTERVAL debe ser finito y positivo, y SYMBIONT_CHECKPOINT_EVERY un entero positivo." >&2
    exit 2
  fi
fi

if ! "$PYTHON_BIN" - "$PORT" <<'PY'
import socket
import sys

try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", int(sys.argv[1])))
except OSError:
    sys.exit(1)
PY
then
  echo "Error: el puerto $PORT ya esta ocupado o no puede reservarse." >&2
  echo "Ejecuta el script con otro puerto, por ejemplo: $0 $COUNT $((PORT + 1))" >&2
  exit 1
fi

mkdir -p "$OBS_DIR" "$STATE_DIR"

resident_pids=()
server_pid=""
failure_status=0

cleanup() {
  local status=$?
  trap '' EXIT INT TERM
  echo
  echo "Deteniendo el ecosistema..."

  # Enviar SIGTERM a los residentes para que guarden su checkpoint y finalicen limpiamente
  for pid in "${resident_pids[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill -TERM "$pid" 2>/dev/null || true
    fi
  done

  if [[ -n "$server_pid" ]] && kill -0 "$server_pid" 2>/dev/null; then
    kill -TERM "$server_pid" 2>/dev/null || true
  fi

  # Esperar hasta 5 segundos para que los procesos terminen ordenadamente
  local timeout=5
  local deadline=$((SECONDS + timeout))
  for pid in "${resident_pids[@]}"; do
    while kill -0 "$pid" 2>/dev/null && (( SECONDS < deadline )); do
      sleep 0.1
    done
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
    fi
  done

  if [[ -n "$server_pid" ]]; then
    while kill -0 "$server_pid" 2>/dev/null && (( SECONDS < deadline )); do
      sleep 0.1
    done
    if kill -0 "$server_pid" 2>/dev/null; then
      kill -9 "$server_pid" 2>/dev/null || true
    fi
  fi

  wait 2>/dev/null || true
  if (( status == 130 || status == 143 )); then
    status=0
  fi
  if (( status == 0 && failure_status != 0 )); then
    status=$failure_status
  fi
  if (( status == 0 )); then
    echo "Ecosistema detenido correctamente."
  else
    echo "Ecosistema detenido con errores (codigo $status)." >&2
  fi
  return "$status"
}
trap cleanup EXIT
trap 'exit 0' INT TERM

cd "$ROOT_DIR"
echo "Iniciando ecosistema de $COUNT organismos..."
echo "Observatory: http://127.0.0.1:$PORT/"
echo "Estado: $STATE_DIR"
echo "Logs: $STATE_DIR/<nombre>.log"
echo "Python: $PYTHON_BIN"
echo "Pulsa Ctrl-C para detener todos los procesos."

for ((index = 1; index <= COUNT; index++)); do
  name="symbiont-$(printf '%03d' "$index")"
  cmd=("$PYTHON_BIN" observatory/resident.py \
    --display-id "$name" \
    --state-file "$STATE_DIR/$name.json" \
    --observatory-dir "$OBS_DIR" \
    --no-stdout)
  if [[ -n "$INTERVAL" ]]; then
    cmd+=(--interval "$INTERVAL")
  fi
  if [[ -n "$CHECKPOINT_EVERY" ]]; then
    cmd+=(--checkpoint-every "$CHECKPOINT_EVERY")
  fi
  if [[ "$ENABLE_SLM" == "1" || "$ENABLE_SLM" == "true" ]]; then
    cmd+=(--enable-slm)
  fi
  "${cmd[@]}" >> "$STATE_DIR/$name.log" 2>&1 &
  resident_pids+=("$!")
  echo "Organismo [$name] lanzado con PID ${resident_pids[-1]}"
done

server_cmd=("$PYTHON_BIN" observatory/server.py --observatory-dir "$OBS_DIR")
if [[ -n "${2:-}" ]]; then
  server_cmd+=(--port "$PORT")
fi
"${server_cmd[@]}" &
server_pid="$!"
echo "Servidor del Observatory lanzado con PID $server_pid"

# Mantener este shell como dueño del ciclo de vida para que Ctrl-C detenga toda la flota.
while true; do
  if [[ -n "$server_pid" ]] && ! kill -0 "$server_pid" 2>/dev/null; then
    echo "Aviso: El servidor del Observatory se ha detenido."
    wait "$server_pid" || failure_status=3
    break
  fi

  any_resident_alive=false
  for pid in "${resident_pids[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      any_resident_alive=true
      break
    fi
  done
  if ! $any_resident_alive; then
    echo "Aviso: Todos los organismos han finalizado."
    for pid in "${resident_pids[@]}"; do
      wait "$pid" 2>/dev/null || true
    done
    break
  fi

  # Vigilar el directorio incubator para nuevos nacimientos (brotación / budding)
  incubator_dir="$STATE_DIR/habitat/incubator"
  if [[ -d "$incubator_dir" ]]; then
    shopt -s nullglob
    embryos=("$incubator_dir"/*.json)
    shopt -u nullglob
    for embryo in "${embryos[@]}"; do
      [[ -f "$embryo" ]] || continue
      alive_count=0
      for pid in "${resident_pids[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
          ((alive_count++))
        fi
      done
      if (( alive_count < MAX_POPULATION )); then
        child_filename="$(basename "$embryo")"
        child_name="${child_filename%.json}"
        mv "$embryo" "$STATE_DIR/$child_filename"
        child_cmd=("$PYTHON_BIN" observatory/resident.py \
          --display-id "$child_name" \
          --state-file "$STATE_DIR/$child_filename" \
          --observatory-dir "$OBS_DIR" \
          --no-stdout)
        if [[ -n "$INTERVAL" ]]; then
          child_cmd+=(--interval "$INTERVAL")
        fi
        if [[ -n "$CHECKPOINT_EVERY" ]]; then
          child_cmd+=(--checkpoint-every "$CHECKPOINT_EVERY")
        fi
        if [[ "$ENABLE_SLM" == "1" || "$ENABLE_SLM" == "true" ]]; then
          child_cmd+=(--enable-slm)
        fi
        "${child_cmd[@]}" >> "$STATE_DIR/$child_name.log" 2>&1 &
        new_pid="$!"
        resident_pids+=("$new_pid")
        echo "Brote incubado: [$child_name] lanzado con PID $new_pid (poblacion viva: $((alive_count + 1)))"
      fi
    done
  fi

  sleep 1 &
  wait $! 2>/dev/null || true
done
