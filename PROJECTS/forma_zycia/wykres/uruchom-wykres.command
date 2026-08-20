#!/bin/zsh

set -eu

script_dir=${0:A:h}
repo_root=${script_dir:h:h:h}

if git -C "$repo_root" diff --quiet -- DATA/waga.csv \
  && git -C "$repo_root" diff --cached --quiet -- DATA/waga.csv; then
  if git -C "$repo_root" pull --ff-only --quiet; then
    echo "Odświeżono dane wykresu z synchronizacji Garmin w repozytorium."
  else
    echo "Nie udało się pobrać aktualizacji. Wykres użyje bieżących danych lokalnych."
  fi
else
  echo "DATA/waga.csv ma lokalne zmiany, więc nie pobrano aktualizacji, aby ich nie nadpisać."
fi

server_log=$(mktemp -t forma-zycia-wykres.XXXXXX)
python3 "$script_dir/serwer-wykresu.py" 0 >"$server_log" 2>&1 &
server_pid=$!

cleanup() {
  kill "$server_pid" >/dev/null 2>&1 || true
  rm -f "$server_log"
}
trap cleanup EXIT HUP INT TERM

for attempt in {1..30}; do
  chart_url=$(sed -n 's|^Wykres jest dostępny pod adresem \(http://127\.0\.0\.1:[0-9][0-9]*/\)$|\1|p' "$server_log" | head -n 1)
  if [[ -n "$chart_url" ]]; then
    if curl --fail --silent --show-error --max-time 1 "$chart_url" >/dev/null 2>&1; then
      open "$chart_url"
      echo "Wykres został otwarty w przeglądarce pod adresem $chart_url"
      echo "To okno utrzymuje lokalny serwer. Zamknij je lub naciśnij Ctrl+C, aby go zatrzymać."
      wait "$server_pid"
      exit $?
    fi
  fi

  if ! kill -0 "$server_pid" >/dev/null 2>&1; then
    echo "Nie udało się uruchomić wykresu. Szczegóły:"
    sed -n '1,20p' "$server_log"
    exit 1
  fi

  sleep 0.1
done

echo "Serwer nie uruchomił się w oczekiwanym czasie."
exit 1