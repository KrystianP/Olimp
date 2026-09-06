#!/bin/zsh

set -eu

script_dir=${0:A:h}
repo_root=${script_dir:h:h:h}
typeset -a data_paths
data_paths=(
  "DATA/waga.csv"
  "DATA/garmin/aktywnosci.csv"
)

cd "$repo_root"

if [[ "$(git rev-parse --show-toplevel)" != "$repo_root" ]]; then
  echo "Nie znaleziono oczekiwanego repozytorium Olimp." >&2
  exit 1
fi

current_branch=$(git branch --show-current)
if [[ "$current_branch" != "main" ]]; then
  echo "Pominięto odświeżanie: bieżąca gałąź to '$current_branch', nie 'main'." >&2
  exit 2
fi

if ! git diff --quiet HEAD -- "${data_paths[@]}" || \
   [[ -n "$(git ls-files --others --exclude-standard -- "${data_paths[@]}")" ]]; then
  echo "Nie pobrano danych: lokalne pliki Garmin lub wagi mają niezapisane zmiany." >&2
  echo "Najpierw przejrzyj i zatwierdź te zmiany; skrypt niczego nie nadpisze." >&2
  exit 3
fi

echo "Sprawdzanie nowych danych w origin/main..."
git fetch --quiet origin main

local_head=$(git rev-parse HEAD)
remote_head=$(git rev-parse origin/main)

if [[ "$local_head" == "$remote_head" ]]; then
  echo "Dane lokalne są aktualne."
  exit 0
fi

if git merge-base --is-ancestor "$remote_head" "$local_head"; then
  echo "Lokalna gałąź zawiera już wszystkie zmiany z origin/main."
  exit 0
fi

if ! git merge-base --is-ancestor "$local_head" "$remote_head"; then
  echo "Nie pobrano danych: lokalny main i origin/main mają rozbieżne commity." >&2
  echo "Potrzebne jest świadome scalenie; skrypt nie wykona rebase ani force." >&2
  exit 4
fi

changed_data=$(git diff --name-only "$local_head" "$remote_head" -- "${data_paths[@]}")
if ! git merge --ff-only "$remote_head"; then
  echo "Fast-forward został bezpiecznie przerwany. Lokalne pliki nie zostały nadpisane." >&2
  exit 5
fi

if [[ -n "$changed_data" ]]; then
  echo "Pobrano aktualne dane:"
  print -r -- "$changed_data"
else
  echo "Pobrano origin/main; pliki Garmin i wagi nie wymagały zmiany."
fi
