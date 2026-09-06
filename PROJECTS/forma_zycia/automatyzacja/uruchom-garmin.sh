#!/bin/zsh

set -eu

if [[ $# -ne 1 || ( "$1" != "activities" && "$1" != "weight" ) ]]; then
  echo "Użycie: $0 activities|weight" >&2
  exit 2
fi

mode=$1
script_dir=${0:A:h}
runtime_dir="$HOME/Library/Application Support/KrystianOS/garmin"
python_bin="$runtime_dir/.venv-garmin/bin/python"
token_dir="$HOME/.config/krystian-os/garmin"
log_dir="$HOME/Library/Logs/KrystianOS/garmin"
stdout_log="$log_dir/$mode.log"
stderr_log="$log_dir/$mode-error.log"

mkdir -p "$log_dir"
chmod 700 "$log_dir"

for log_file in "$stdout_log" "$stderr_log"; do
  if [[ -f "$log_file" && $(stat -f %z "$log_file") -gt 1048576 ]]; then
    tail -n 2000 "$log_file" > "$log_file.tmp"
    mv "$log_file.tmp" "$log_file"
  fi
done

if [[ ! -x "$python_bin" ]]; then
  echo "Brakuje środowiska Garmin. Uruchom zaloguj-garmin.command." >&2
  exit 1
fi
if [[ ! -f "$token_dir/garmin_tokens.json" ]]; then
  echo "Brakuje tokenu Garmin. Uruchom zaloguj-garmin.command." >&2
  exit 1
fi

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S %z')] start mode=$mode"
  set +e
  "$python_bin" -B "$script_dir/synchronizuj_garmin.py" \
    --mode "$mode" \
    --token-store "$token_dir" \
    --days 14 \
    --activity-days 14
  exit_code=$?
  set -e
  echo "[$(date '+%Y-%m-%d %H:%M:%S %z')] end mode=$mode exit=$exit_code"
  exit "$exit_code"
} >> "$stdout_log" 2>> "$stderr_log"
