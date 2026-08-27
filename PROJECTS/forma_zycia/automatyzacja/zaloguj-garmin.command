#!/bin/zsh

set -eu

script_dir=${0:A:h}
venv_dir="$HOME/Library/Application Support/KrystianOS/garmin/.venv-garmin"
token_dir="$HOME/.config/krystian-os/garmin"
token_file="$token_dir/garmin_tokens.json"

if [[ ! -x "$venv_dir/bin/python" ]]; then
  python3 -m venv "$venv_dir"
fi

"$venv_dir/bin/python" -m pip install --quiet --upgrade "garminconnect==0.3.4"
if [[ -f "$token_file" ]]; then
  echo "Wykorzystuję istniejący token Garmin; nie będzie ponownego logowania hasłem."
  "$venv_dir/bin/python" "$script_dir/synchronizuj_garmin.py" \
    --token-store "$token_dir" \
    --dry-run
else
  "$venv_dir/bin/python" "$script_dir/synchronizuj_garmin.py" \
    --initialize-auth \
    --token-store "$token_dir" \
    --dry-run
fi

if [[ ! -f "$token_file" ]]; then
  echo "Nie powstał lokalny plik tokenu Garmin."
  exit 1
fi

echo "Gotowe: token Garmin jest tylko lokalnie w $token_dir."

if ! command -v gh >/dev/null 2>&1; then
  echo "Brakuje GitHub CLI (gh). Zainstaluj je, a następnie uruchom ten plik ponownie."
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Zaloguj się teraz do GitHub w przeglądarce."
  gh auth login --hostname github.com --web
fi

repo_url=$(git -C "$script_dir/../../.." remote get-url origin 2>/dev/null || true)
repo_name=$(printf '%s' "$repo_url" | sed -E 's#^(git@github.com:|https://github.com/|ssh://git@github.com/)##; s#\.git$##')
if [[ -z "$repo_name" ]]; then
  echo "Nie udało się ustalić repozytorium GitHub z remote origin."
  exit 1
fi

base64 < "$token_file" | tr -d '\n' | gh secret set GARMIN_TOKENS_JSON_B64 --repo "$repo_name"
echo "Gotowe: token Garmin zapisano jako sekret GitHub. Workflow synchronizacji jest obecnie wyłączony i nie uruchomi się, dopóki nie zostanie ponownie włączony w GitHub Actions."
