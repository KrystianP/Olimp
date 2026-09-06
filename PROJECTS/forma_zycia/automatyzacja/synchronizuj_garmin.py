#!/usr/bin/env python3
"""Synchronizuje lekki indeks aktywności i wagę z Garmin Connect.

Hasło nie jest przechowywane. Automatyczne uruchomienia korzystają wyłącznie
z tokenu Garmina zapisanego poza repozytorium. Surowe pliki FIT, współrzędne
GPS i identyfikatory urządzeń nie trafiają do Olimpu.
"""

from __future__ import annotations

import argparse
import csv
import fcntl
import getpass
import json
import os
import sys
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from pathlib import Path
from statistics import mean
from tempfile import NamedTemporaryFile
from typing import Any, Iterator, TextIO
from zoneinfo import ZoneInfo


PROJECT_DIRECTORY = Path(__file__).resolve().parent
REPOSITORY_ROOT = PROJECT_DIRECTORY.parents[2]
WEIGHT_DATA = REPOSITORY_ROOT / "DATA" / "waga.csv"
ACTIVITIES_DATA = REPOSITORY_ROOT / "DATA" / "garmin" / "aktywnosci.csv"
DEFAULT_TOKEN_STORE = Path.home() / ".config" / "krystian-os" / "garmin"
DEFAULT_LOCK_FILE = (
    Path.home() / "Library" / "Application Support" / "KrystianOS" / "garmin" / "sync.lock"
)
WARSAW = ZoneInfo("Europe/Warsaw")

WEIGHT_COLUMNS = (
    "data",
    "waga_kg",
    "tkanka_tluszczowa_proc",
    "bmi",
    "typ_rekordu",
    "okres_od",
    "okres_do",
    "zmiana_kg",
)

ACTIVITY_COLUMNS = (
    "activity_id",
    "start_time_local",
    "activity_type",
    "duration_seconds",
    "distance_meters",
    "calories",
    "average_hr_bpm",
    "max_hr_bpm",
    "elevation_gain_m",
    "training_load",
    "aerobic_training_effect",
    "anaerobic_training_effect",
)


class AlreadyRunningError(RuntimeError):
    """Inna synchronizacja korzysta już z tego samego magazynu danych."""


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Synchronizuje aktywności i wagę z Garmin Connect."
    )
    parser.add_argument(
        "--mode",
        choices=("activities", "weight", "all", "auth", "bootstrap"),
        default="all",
        help="Zakres pracy (domyślnie: all).",
    )
    parser.add_argument(
        "--token-store",
        type=Path,
        default=DEFAULT_TOKEN_STORE,
        help="Katalog z lokalnym tokenem Garmin.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=14,
        help="Okno ponownego sprawdzania wagi (domyślnie: 14 dni).",
    )
    parser.add_argument(
        "--activity-days",
        type=int,
        default=14,
        help="Okno ponownego sprawdzania aktywności (domyślnie: 14 dni).",
    )
    parser.add_argument(
        "--weight-data",
        type=Path,
        default=WEIGHT_DATA,
        help="Kanoniczny CSV z historią wagi.",
    )
    parser.add_argument(
        "--activities-data",
        type=Path,
        default=ACTIVITIES_DATA,
        help="Lekki CSV z aktywnościami.",
    )
    parser.add_argument(
        "--bootstrap-from",
        type=Path,
        help="Katalog pobrane_treningi używany tylko przez tryb bootstrap.",
    )
    parser.add_argument(
        "--initialize-auth",
        action="store_true",
        help="Jednorazowo poproś o dane Garmin i MFA, aby utworzyć token.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Pobierz i zweryfikuj dane bez zapisywania CSV.",
    )
    parser.add_argument(
        "--lock-file",
        type=Path,
        default=DEFAULT_LOCK_FILE,
        help="Wspólna blokada zapobiegająca równoległym uruchomieniom.",
    )
    arguments = parser.parse_args()
    if not 1 <= arguments.days <= 3650:
        parser.error("--days musi być liczbą od 1 do 3650.")
    if not 1 <= arguments.activity_days <= 3650:
        parser.error("--activity-days musi być liczbą od 1 do 3650.")
    if arguments.mode == "bootstrap" and arguments.bootstrap_from is None:
        parser.error("Tryb bootstrap wymaga --bootstrap-from.")
    return arguments


@contextmanager
def exclusive_lock(path: Path) -> Iterator[None]:
    path = path.expanduser().resolve()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        path.parent.relative_to(Path.home())
    except ValueError:
        pass
    else:
        path.parent.chmod(0o700)
    lock: TextIO = path.open("a+", encoding="utf-8")
    path.chmod(0o600)
    try:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise AlreadyRunningError("inna synchronizacja Garmin nadal trwa") from error
        lock.seek(0)
        lock.truncate()
        lock.write(f"pid={os.getpid()} started={datetime.now(WARSAW).isoformat()}\n")
        lock.flush()
        yield
    finally:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        finally:
            lock.close()


def secure_token_store(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.chmod(0o700)
    for token_file in path.iterdir():
        if token_file.is_file():
            token_file.chmod(0o600)


def connect_to_garmin(token_store: Path, initialize_auth: bool) -> Any:
    """Zwraca klienta Garmin bez wypisywania danych uwierzytelniających."""
    try:
        from garminconnect import Garmin
    except ImportError as error:
        raise RuntimeError(
            "Brakuje pakietu garminconnect. Uruchom zaloguj-garmin.command."
        ) from error

    token_store = token_store.expanduser().resolve()
    secure_token_store(token_store)
    if not initialize_auth:
        client = Garmin()
        client.login(tokenstore=str(token_store))
        secure_token_store(token_store)
        return client

    email = input("E-mail do Garmin Connect: ").strip()
    if not email:
        raise RuntimeError("E-mail Garmin nie może być pusty.")
    password = getpass.getpass("Hasło Garmin Connect (nie będzie wyświetlone): ")
    if not password:
        raise RuntimeError("Hasło Garmin nie może być puste.")
    client = Garmin(
        email=email,
        password=password,
        prompt_mfa=lambda: input("Kod MFA Garmin (jeśli wymagany): ").strip(),
    )
    client.login(tokenstore=str(token_store))
    secure_token_store(token_store)
    return client


def first_value(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


def optional_number(
    value: Any,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    name: str,
) -> float | None:
    if value in (None, ""):
        return None
    number = float(value)
    if minimum is not None and number < minimum:
        raise ValueError(f"Nieprawidłowa wartość {name}: {number}.")
    if maximum is not None and number > maximum:
        raise ValueError(f"Nieprawidłowa wartość {name}: {number}.")
    return number


def format_number(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return ""
    return f"{float(value):.{decimals}f}".rstrip("0").rstrip(".")


def format_fixed(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return ""
    return f"{float(value):.{decimals}f}"


def normalise_activity(record: dict[str, Any]) -> dict[str, str]:
    activity_id = first_value(record, "activityId", "activity_id", "id")
    if activity_id is None:
        raise ValueError("Aktywność Garmin nie zawiera activityId.")
    activity_type = first_value(record, "activityType", "activity_type", "typ")
    if isinstance(activity_type, dict):
        activity_type = first_value(activity_type, "typeKey", "typeId", "displayName")
    start_time = first_value(
        record, "startTimeLocal", "start_time_local", "rozpoczecie_lokalne", "startTimeGMT"
    )
    if start_time is None:
        raise ValueError(f"Aktywność Garmin {activity_id} nie zawiera czasu rozpoczęcia.")
    start_time_text = str(start_time).replace("T", " ")
    if len(start_time_text) >= 19:
        start_time_text = start_time_text[:19]

    numeric_fields = {
        "duration_seconds": first_value(record, "duration", "duration_seconds", "czas_s"),
        "distance_meters": first_value(record, "distance", "distance_meters", "dystans_m"),
        "calories": first_value(record, "calories", "activeKilocalories"),
        "average_hr_bpm": first_value(record, "averageHR", "average_hr", "srednie_tetno_bpm"),
        "max_hr_bpm": first_value(record, "maxHR", "max_hr", "maksymalne_tetno_bpm"),
        "elevation_gain_m": first_value(record, "elevationGain", "elevation_gain_m", "przewyzszenie_m"),
        "training_load": first_value(record, "activityTrainingLoad", "training_load"),
        "aerobic_training_effect": first_value(record, "aerobicTrainingEffect", "aerobic_training_effect"),
        "anaerobic_training_effect": first_value(record, "anaerobicTrainingEffect", "anaerobic_training_effect"),
    }
    row = {
        "activity_id": str(activity_id),
        "start_time_local": start_time_text,
        "activity_type": str(activity_type or "unknown"),
    }
    row.update(
        {
            key: format_number(optional_number(value, name=key))
            for key, value in numeric_fields.items()
        }
    )
    return {column: row.get(column, "") for column in ACTIVITY_COLUMNS}


def read_activities(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != list(ACTIVITY_COLUMNS):
            raise RuntimeError(
                f"{path} ma nieprawidłowy schemat: {reader.fieldnames}."
            )
        rows: dict[str, dict[str, str]] = {}
        for row in reader:
            activity_id = row["activity_id"]
            if activity_id in rows:
                raise RuntimeError(f"{path} zawiera duplikat activity_id={activity_id}.")
            rows[activity_id] = row
        return rows


def merge_activities(
    existing: dict[str, dict[str, str]], records: list[dict[str, Any]]
) -> int:
    changed = 0
    for record in records:
        row = normalise_activity(record)
        activity_id = row["activity_id"]
        previous = existing.get(activity_id)
        if previous is not None:
            for column in ACTIVITY_COLUMNS:
                if row[column] in ("", "unknown") and previous.get(column):
                    row[column] = previous[column]
        if previous != row:
            existing[activity_id] = row
            changed += 1
    return changed


def atomic_write_csv(
    path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w", newline="", encoding="utf-8", dir=path.parent, delete=False
    ) as temporary:
        writer = csv.DictWriter(temporary, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def write_activities(path: Path, rows: dict[str, dict[str, str]]) -> None:
    ordered = sorted(
        rows.values(), key=lambda row: (row["start_time_local"], row["activity_id"])
    )
    atomic_write_csv(path, ACTIVITY_COLUMNS, ordered)


def load_bootstrap_records(directory: Path) -> list[dict[str, Any]]:
    summary_path = directory / "activities_summary.json"
    metadata_directory = directory / "metadata"
    with summary_path.open(encoding="utf-8") as file:
        summary = json.load(file)
    if not isinstance(summary, list):
        raise RuntimeError(f"{summary_path} nie zawiera listy aktywności.")

    records: list[dict[str, Any]] = []
    for item in summary:
        if not isinstance(item, dict):
            continue
        merged = dict(item)
        activity_id = item.get("activityId")
        metadata_path = metadata_directory / f"{activity_id}.json"
        if metadata_path.is_file():
            with metadata_path.open(encoding="utf-8") as file:
                metadata = json.load(file)
            if isinstance(metadata, dict):
                merged.update(metadata)
        records.append(merged)
    return records


def bootstrap_activities(source: Path, target: Path, dry_run: bool) -> tuple[int, int]:
    records = load_bootstrap_records(source)
    activities = read_activities(target)
    changed = merge_activities(activities, records)
    if changed and not dry_run:
        write_activities(target, activities)
    return len(records), changed


def parse_local_date(value: Any) -> tuple[date, datetime]:
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
        seconds = float(value)
        if seconds > 10_000_000_000:
            seconds /= 1000
        timestamp = datetime.fromtimestamp(seconds, tz=WARSAW)
        return timestamp.date(), timestamp
    text = str(value)
    local_day = date.fromisoformat(text[:10])
    try:
        timestamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=WARSAW)
        else:
            timestamp = timestamp.astimezone(WARSAW)
    except ValueError:
        timestamp = datetime.combine(local_day, time.min, tzinfo=WARSAW)
    return local_day, timestamp


def normalise_measurement(record: dict[str, Any]) -> dict[str, Any]:
    date_source = first_value(
        record, "dateTimestampLocal", "calendarDate", "timestamp", "dateTimestamp"
    )
    if date_source is None:
        raise ValueError("Pomiar Garmin nie zawiera daty.")
    measurement_date, timestamp = parse_local_date(date_source)
    raw_weight = first_value(record, "weight", "weightKg", "value")
    if raw_weight is None:
        raise ValueError(f"Pomiar Garmin z {measurement_date} nie zawiera wagi.")
    weight = float(raw_weight)
    if weight > 300:
        weight /= 1000
    weight = optional_number(weight, minimum=40, maximum=250, name="wagi")
    body_fat = optional_number(
        first_value(record, "bodyFat", "bodyFatPercent", "percentFat"),
        minimum=2,
        maximum=70,
        name="tkanki tłuszczowej",
    )
    bmi = optional_number(
        first_value(record, "bmi", "BMI"), minimum=12, maximum=60, name="BMI"
    )
    return {
        "data": measurement_date.isoformat(),
        "timestamp": timestamp,
        "waga_kg": weight,
        "tkanka_tluszczowa_proc": body_fat,
        "bmi": bmi,
    }


def extract_measurements(response: Any) -> list[dict[str, Any]]:
    if isinstance(response, list):
        records = response
    elif isinstance(response, dict):
        records = first_value(response, "dateWeightList", "weightList", "weights")
        if records is None and isinstance(response.get("dailyWeightSummaries"), list):
            records = []
            for summary in response["dailyWeightSummaries"]:
                if not isinstance(summary, dict):
                    continue
                latest_weight = summary.get("latestWeight")
                if not isinstance(latest_weight, dict):
                    continue
                record = dict(latest_weight)
                record.setdefault("calendarDate", summary.get("summaryDate"))
                records.append(record)
    else:
        records = None
    if not isinstance(records, list):
        raise RuntimeError("Odpowiedź Garmin nie zawiera listy pomiarów wagi.")

    by_date: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        measurement = normalise_measurement(record)
        existing = by_date.get(measurement["data"])
        if existing is None or measurement["timestamp"] > existing["timestamp"]:
            by_date[measurement["data"]] = measurement
    return [by_date[key] for key in sorted(by_date)]


def read_weight_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise RuntimeError("DATA/waga.csv nie zawiera nagłówka.")
        missing = set(WEIGHT_COLUMNS) - set(reader.fieldnames)
        if missing:
            raise RuntimeError(
                "DATA/waga.csv nie zawiera wymaganych kolumn: " + ", ".join(sorted(missing))
            )
        return list(reader.fieldnames), list(reader)


def update_daily_rows(
    rows: list[dict[str, str]],
    headers: list[str],
    measurements: list[dict[str, Any]],
) -> int:
    changed = 0
    for measurement in measurements:
        matching = [
            row
            for row in rows
            if row.get("typ_rekordu") == "pomiar_dzienny"
            and row.get("data") == measurement["data"]
        ]
        if len(matching) > 1:
            raise RuntimeError(
                f"DATA/waga.csv ma więcej niż jeden pomiar dzienny dla {measurement['data']}."
            )
        if matching:
            row = matching[0]
        else:
            row = {column: "" for column in headers}
            row.update({"data": measurement["data"], "typ_rekordu": "pomiar_dzienny"})
            rows.append(row)
        updated = {
            "waga_kg": format_fixed(measurement["waga_kg"], 1),
            "typ_rekordu": "pomiar_dzienny",
            "okres_od": "",
            "okres_do": "",
        }
        if measurement["tkanka_tluszczowa_proc"] is not None:
            updated["tkanka_tluszczowa_proc"] = format_fixed(
                measurement["tkanka_tluszczowa_proc"], 1
            )
        if measurement["bmi"] is not None:
            updated["bmi"] = format_fixed(measurement["bmi"], 1)
        if any(row.get(key, "") != value for key, value in updated.items()):
            row.update(updated)
            changed += 1
    return changed


def update_last_completed_week(
    rows: list[dict[str, str]], headers: list[str], today: date
) -> int:
    week_end = today - timedelta(days=(today.weekday() - 5) % 7)
    week_start = week_end - timedelta(days=6)
    daily_weights = [
        float(row["waga_kg"])
        for row in rows
        if row.get("typ_rekordu") == "pomiar_dzienny"
        and week_start.isoformat() <= row.get("data", "") <= week_end.isoformat()
        and row.get("waga_kg")
    ]
    if len(daily_weights) < 3:
        return 0
    matching = [
        row
        for row in rows
        if row.get("typ_rekordu") == "srednia_tygodniowa"
        and row.get("okres_do") == week_end.isoformat()
    ]
    if len(matching) > 1:
        raise RuntimeError(
            f"DATA/waga.csv ma więcej niż jedną średnią dla tygodnia do {week_end}."
        )
    previous = [
        float(row["waga_kg"])
        for row in rows
        if row.get("typ_rekordu") == "srednia_tygodniowa"
        and row.get("data", "") < week_end.isoformat()
        and row.get("waga_kg")
    ]
    weekly_weight = round(mean(daily_weights), 1)
    updated = {
        "data": week_end.isoformat(),
        "waga_kg": format_fixed(weekly_weight, 1),
        "tkanka_tluszczowa_proc": "",
        "bmi": "",
        "typ_rekordu": "srednia_tygodniowa",
        "okres_od": week_start.isoformat(),
        "okres_do": week_end.isoformat(),
        "zmiana_kg": format_fixed(weekly_weight - previous[-1], 1) if previous else "",
    }
    if matching:
        row = matching[0]
    else:
        row = {column: "" for column in headers}
        rows.append(row)
    if any(row.get(key, "") != value for key, value in updated.items()):
        row.update(updated)
        return 1
    return 0


def write_weight_rows(
    path: Path, headers: list[str], rows: list[dict[str, str]]
) -> None:
    atomic_write_csv(path, tuple(headers), rows)


def sync_activities(client: Any, days: int, path: Path, dry_run: bool) -> tuple[int, int]:
    today = datetime.now(WARSAW).date()
    start = today - timedelta(days=days - 1)
    records = client.get_activities_by_date(start.isoformat(), today.isoformat())
    if not isinstance(records, list):
        raise RuntimeError("Odpowiedź Garmin nie zawiera listy aktywności.")
    activities = read_activities(path)
    changed = merge_activities(activities, [item for item in records if isinstance(item, dict)])
    if changed and not dry_run:
        write_activities(path, activities)
    return len(records), changed


def sync_weight(client: Any, days: int, path: Path, dry_run: bool) -> tuple[int, int, int]:
    today = datetime.now(WARSAW).date()
    response = client.get_weigh_ins(
        (today - timedelta(days=days - 1)).isoformat(), today.isoformat()
    )
    measurements = extract_measurements(response)
    headers, rows = read_weight_rows(path)
    updated_daily = update_daily_rows(rows, headers, measurements)
    updated_weekly = update_last_completed_week(rows, headers, today)
    if updated_daily + updated_weekly and not dry_run:
        write_weight_rows(path, headers, rows)
    return len(measurements), updated_daily, updated_weekly


def describe_error(error: Exception) -> str:
    text = str(error)
    lowered = text.lower()
    if "429" in lowered or "too many" in lowered or "rate limit" in lowered:
        return f"Garmin ograniczył liczbę zapytań; odczekaj co najmniej godzinę. ({text})"
    if "401" in lowered or "token is not active" in lowered:
        return f"Token Garmin jest nieaktywny; wymagane jest ponowne logowanie. ({text})"
    return text or error.__class__.__name__


def main() -> int:
    arguments = parse_arguments()
    try:
        with exclusive_lock(arguments.lock_file):
            if arguments.mode == "bootstrap":
                total, changed = bootstrap_activities(
                    arguments.bootstrap_from.expanduser().resolve(),
                    arguments.activities_data,
                    arguments.dry_run,
                )
                print(
                    f"Garmin bootstrap: odczytano {total} aktywności; "
                    f"dodano lub zmieniono {changed}."
                )
                return 0

            client = connect_to_garmin(arguments.token_store, arguments.initialize_auth)
            if arguments.mode == "auth":
                activities = client.get_activities(start=0, limit=1)
                if not isinstance(activities, (list, dict)):
                    raise RuntimeError("Garmin zwrócił nieoczekiwany wynik testu sesji.")
                print("Garmin: sesja działa; token pozostaje wyłącznie lokalnie.")
                return 0

            if arguments.mode in ("activities", "all"):
                total, changed = sync_activities(
                    client,
                    arguments.activity_days,
                    arguments.activities_data,
                    arguments.dry_run,
                )
                print(
                    f"Garmin aktywności: sprawdzono {total}; "
                    f"dodano lub zmieniono {changed}."
                )
            if arguments.mode in ("weight", "all"):
                total, updated_daily, updated_weekly = sync_weight(
                    client, arguments.days, arguments.weight_data, arguments.dry_run
                )
                print(
                    f"Garmin waga: sprawdzono {total} pomiarów; zmieniono "
                    f"{updated_daily} dziennych i {updated_weekly} tygodniowych rekordów."
                )
    except AlreadyRunningError as error:
        print(f"Garmin: pominięto uruchomienie, bo {error}.")
        return 0
    except Exception as error:
        print(
            f"Synchronizacja Garmin nie została wykonana: {describe_error(error)}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
