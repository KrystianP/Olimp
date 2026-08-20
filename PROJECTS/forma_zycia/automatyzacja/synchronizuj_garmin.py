#!/usr/bin/env python3
"""Synchronizuje pomiary z Garmin Connect do DATA/waga.csv.

Skrypt nie przechowuje hasła. W trybie automatycznym korzysta wyłącznie z
odświeżalnego tokenu Garmin przekazanego przez ``--token-store``.
"""

from __future__ import annotations

import argparse
import csv
import getpass
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from statistics import mean
from tempfile import NamedTemporaryFile
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_DIRECTORY = Path(__file__).resolve().parent
REPOSITORY_ROOT = PROJECT_DIRECTORY.parents[2]
WEIGHT_DATA = REPOSITORY_ROOT / "DATA" / "waga.csv"
WARSAW = ZoneInfo("Europe/Warsaw")
REQUIRED_COLUMNS = (
    "data",
    "waga_kg",
    "tkanka_tluszczowa_proc",
    "bmi",
    "typ_rekordu",
    "okres_od",
    "okres_do",
    "zmiana_kg",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pobiera ostatnie pomiary z Garmin i aktualizuje DATA/waga.csv."
    )
    parser.add_argument(
        "--token-store",
        type=Path,
        required=True,
        help="Katalog zawierający garmin_tokens.json.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=14,
        help="Liczba ostatnich dni do ponownego sprawdzenia (domyślnie: 14).",
    )
    parser.add_argument(
        "--initialize-auth",
        action="store_true",
        help="Jednorazowo poproś lokalnie o dane Garmin i kod MFA, aby utworzyć token.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Sprawdź dane bez zapisywania CSV.",
    )
    arguments = parser.parse_args()
    if arguments.days < 1 or arguments.days > 90:
        parser.error("--days musi być liczbą od 1 do 90.")
    return arguments


def connect_to_garmin(token_store: Path, initialize_auth: bool) -> Any:
    """Zwraca zalogowany klient Garmin bez wypisywania danych uwierzytelniających."""
    try:
        from garminconnect import Garmin
    except ImportError as error:
        raise RuntimeError(
            "Brakuje pakietu garminconnect. Uruchom logowanie przez plik "
            "zaloguj-garmin.command."
        ) from error

    token_store.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not initialize_auth:
        client = Garmin()
        client.login(str(token_store))
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
        prompt_mfa=lambda: input("Kod MFA Garmin (jeśli zostanie wymagany): ").strip(),
    )
    client.login(str(token_store))
    return client


def first_value(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


def parse_local_date(value: Any) -> tuple[date, datetime]:
    """Normalizuje kilka znanych formatów znacznika czasu Garmin do Warszawy."""
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
        seconds = float(value)
        if seconds > 10_000_000_000:
            seconds /= 1000
        timestamp = datetime.fromtimestamp(seconds, tz=WARSAW)
        return timestamp.date(), timestamp

    text = str(value).strip()
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
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

    raise ValueError(f"Nieznany format daty Garmin: {value!r}")


def optional_number(value: Any, *, minimum: float, maximum: float, name: str) -> float | None:
    if value in (None, ""):
        return None
    number = float(value)
    if not minimum <= number <= maximum:
        raise ValueError(f"Nieprawidłowa wartość {name}: {number}.")
    return number


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
    assert weight is not None

    body_fat = optional_number(
        first_value(record, "bodyFat", "bodyFatPercent", "percentFat"),
        minimum=2,
        maximum=70,
        name="tkanki tłuszczowej",
    )
    bmi = optional_number(first_value(record, "bmi", "BMI"), minimum=12, maximum=60, name="BMI")
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
        headers = reader.fieldnames
        missing_columns = set(REQUIRED_COLUMNS) - set(headers)
        if missing_columns:
            raise RuntimeError(
                "DATA/waga.csv nie zawiera wymaganych kolumn: "
                + ", ".join(sorted(missing_columns))
            )
        return headers, list(reader)


def format_number(value: float, decimals: int) -> str:
    return f"{value:.{decimals}f}".rstrip("0").rstrip(".")


def update_daily_rows(rows: list[dict[str, str]], headers: list[str], measurements: list[dict[str, Any]]) -> int:
    changed = 0
    for measurement in measurements:
        matching_rows = [
            row
            for row in rows
            if row["typ_rekordu"] == "pomiar_dzienny" and row["data"] == measurement["data"]
        ]
        if len(matching_rows) > 1:
            raise RuntimeError(
                f"DATA/waga.csv ma więcej niż jeden pomiar dzienny dla {measurement['data']}."
            )
        row = matching_rows[0] if matching_rows else {header: "" for header in headers}
        if not matching_rows:
            row.update({"data": measurement["data"], "typ_rekordu": "pomiar_dzienny"})
            rows.append(row)

        updated = {
            "waga_kg": format_number(measurement["waga_kg"], 2),
            "typ_rekordu": "pomiar_dzienny",
            "okres_od": "",
            "okres_do": "",
        }
        if measurement["tkanka_tluszczowa_proc"] is not None:
            updated["tkanka_tluszczowa_proc"] = format_number(
                measurement["tkanka_tluszczowa_proc"], 1
            )
        if measurement["bmi"] is not None:
            updated["bmi"] = format_number(measurement["bmi"], 1)

        if any(row.get(key, "") != value for key, value in updated.items()):
            row.update(updated)
            changed += 1
    return changed


def update_last_completed_week(rows: list[dict[str, str]], headers: list[str], today: date) -> int:
    week_end = today - timedelta(days=(today.weekday() - 5) % 7)
    week_start = week_end - timedelta(days=6)
    daily_weights = [
        float(row["waga_kg"])
        for row in rows
        if row["typ_rekordu"] == "pomiar_dzienny"
        and week_start.isoformat() <= row["data"] <= week_end.isoformat()
        and row["waga_kg"]
    ]
    if len(daily_weights) < 3:
        return 0

    weekly_weight = round(mean(daily_weights), 1)
    matching_rows = [
        row
        for row in rows
        if row["typ_rekordu"] == "srednia_tygodniowa"
        and row["okres_od"] == week_start.isoformat()
        and row["okres_do"] == week_end.isoformat()
    ]
    if len(matching_rows) > 1:
        raise RuntimeError(
            f"DATA/waga.csv ma więcej niż jedną średnią dla tygodnia do {week_end}."
        )
    row = matching_rows[0] if matching_rows else {header: "" for header in headers}
    previous_weights = [
        float(candidate["waga_kg"])
        for candidate in rows
        if candidate["typ_rekordu"] == "srednia_tygodniowa"
        and candidate["data"] < week_end.isoformat()
        and candidate["waga_kg"]
    ]
    updated = {
        "data": week_end.isoformat(),
        "waga_kg": format_number(weekly_weight, 1),
        "typ_rekordu": "srednia_tygodniowa",
        "okres_od": week_start.isoformat(),
        "okres_do": week_end.isoformat(),
        "zmiana_kg": (
            format_number(round(weekly_weight - previous_weights[-1], 1), 1)
            if previous_weights
            else ""
        ),
    }
    if not matching_rows:
        rows.append(row)
    if any(row.get(key, "") != value for key, value in updated.items()):
        row.update(updated)
        return 1
    return 0


def write_weight_rows(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    with NamedTemporaryFile("w", newline="", encoding="utf-8", dir=path.parent, delete=False) as file:
        writer = csv.DictWriter(file, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        temporary_path = Path(file.name)
    temporary_path.replace(path)


def describe_error(error: Exception) -> str:
    message = str(error)
    if "429" in message or "rate limited" in message.lower():
        return (
            "Garmin chwilowo zablokował logowanie z tego adresu IP (HTTP 429). "
            "Nie ponawiaj próby teraz; odczekaj co najmniej godzinę i uruchom ją tylko raz."
        )
    return message


def main() -> int:
    arguments = parse_arguments()
    try:
        client = connect_to_garmin(arguments.token_store, arguments.initialize_auth)
        today = datetime.now(WARSAW).date()
        response = client.get_weigh_ins(
            (today - timedelta(days=arguments.days - 1)).isoformat(), today.isoformat()
        )
        measurements = extract_measurements(response)
        headers, rows = read_weight_rows(WEIGHT_DATA)
        updated_daily = update_daily_rows(rows, headers, measurements)
        updated_weekly = update_last_completed_week(rows, headers, today)
        if updated_daily + updated_weekly and not arguments.dry_run:
            write_weight_rows(WEIGHT_DATA, headers, rows)
        print(
            "Garmin: sprawdzono "
            f"{len(measurements)} pomiarów; zmieniono {updated_daily} dziennych i "
            f"{updated_weekly} tygodniowych rekordów."
        )
    except Exception as error:
        print(
            f"Synchronizacja Garmin nie została wykonana: {describe_error(error)}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
