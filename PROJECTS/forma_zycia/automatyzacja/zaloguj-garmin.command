#!/bin/zsh

set -eu

script_dir=${0:A:h}
repo_root=${script_dir:h:h:h}
venv_dir="$script_dir/.venv-garmin"
token_dir="$HOME/.config/krystian-os/garmin"
token_file="$token_dir/garmin_tokens.json"

if ! command -v gh >/dev/null 2>&1; then
  echo "Brakuje GitHub CLI (gh). Zainstaluj je, a następnie uruchom ten plik ponownie."
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Zaloguj się teraz do GitHub w przeglądarce."
  gh auth login --hostname github.com --web
fi

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
  echo "Nie powstał plik tokenu Garmin. Nic nie zostało wysłane do GitHub."
  exit 1
fi

repo_url=$(git -C "$repo_root" remote get-url origin 2>/dev/null || true)
repo_name=$(printf '%s' "$repo_url" | sed -E 's#^(git@github.com:|https://github.com/|ssh://git@github.com/)##; s#\.git$##')
if [[ -z "$repo_name" ]]; then
  echo "Nie udało się ustalić repozytorium GitHub z remote origin."
  exit 1
fi

base64 < "$token_file" | tr -d '\n' | gh secret set GARMIN_TOKENS_JSON_B64 --repo "$repo_name"
echo "Gotowe: token Garmin zapisano jako sekret GitHub, bez wyświetlania jego treści."
echo "Następnie wypchnij pliki automatyzacji i uruchom workflow ręcznie z GitHub Actions."
