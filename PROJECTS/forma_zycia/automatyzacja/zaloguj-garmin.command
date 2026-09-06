#!/bin/zsh

set -eu

script_dir=${0:A:h}
runtime_dir="$HOME/Library/Application Support/KrystianOS/garmin"
venv_dir="$runtime_dir/.venv-garmin"
token_dir="$HOME/.config/krystian-os/garmin"
token_file="$token_dir/garmin_tokens.json"

mkdir -p "$runtime_dir" "$token_dir"
chmod 700 "$runtime_dir" "$token_dir"

if [[ ! -x "$venv_dir/bin/python" ]]; then
  python3 -m venv "$venv_dir"
fi

"$venv_dir/bin/python" -m pip install \
  --disable-pip-version-check \
  --quiet \
  --requirement "$script_dir/requirements-garmin.txt"

if [[ -f "$token_file" ]]; then
  echo "Sprawdzam istniejącą lokalną sesję Garmin."
  "$venv_dir/bin/python" -B "$script_dir/synchronizuj_garmin.py" \
    --mode auth \
    --token-store "$token_dir"
else
  echo "Tworzę lokalną sesję Garmin. Hasło nie zostanie zapisane."
  "$venv_dir/bin/python" -B "$script_dir/synchronizuj_garmin.py" \
    --mode auth \
    --initialize-auth \
    --token-store "$token_dir"
fi

chmod 700 "$token_dir"
find "$token_dir" -maxdepth 1 -type f -exec chmod 600 {} \;
echo "Gotowe: działający token Garmin znajduje się wyłącznie w $token_dir."
