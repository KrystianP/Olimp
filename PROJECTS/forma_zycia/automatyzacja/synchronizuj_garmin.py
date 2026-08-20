#!/usr/bin/env python3
"""Synchronizuje pomiary z Garmin Connect do DATA/waga.csv.

Skrypt nie przechowuje hasła. W trybie automatycznym korzysta wyłącznie z
odświeżalnego tokenu Garmin przekazanego przez ``--token-store``.
"""

from __future__ import annotations

import argparse
import csv
import getpass
import json
import os
import sqlite3
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
GARMIN_DATA_DIRECTORY = REPOSITORY_ROOT / "DATA" / "garmin"
DATABASE_PATH = GARMIN_DATA_DIRECTORY / "garmin.sqlite"
RAW_ACTIVITY_DIRECTORY = GARMIN_DATA_DIRECTORY / "surowe" / "aktywnosci"
ORIGINAL_ACTIVITY_DIRECTORY = GARMIN_DATA_DIRECTORY / "surowe" / "oryginalne"
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
        "--activity-days",
        type=int,
        default=30,
        help="Liczba dni aktywności do ponownego sprawdzenia (domyślnie: 30).",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DATABASE_PATH,
        help="Lokalna baza SQLite z danymi Garmin.",
    )
    parser.add_argument(
        "--weight-data",
        type=Path,
        default=WEIGHT_DATA,
        help="CSV z historią wagi do aktualizacji.",
    )
    parser.add_argument(
        "--raw-activity-directory",
        type=Path,
        default=RAW_ACTIVITY_DIRECTORY,
        help="Katalog niezmienionych odpowiedzi Garmin dla aktywności.",
    )
    parser.add_argument(
        "--original-activity-directory",
        type=Path,
        default=ORIGINAL_ACTIVITY_DIRECTORY,
        help="Katalog oryginalnych archiwów aktywności Garmin.",
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
    if arguments.days < 1 or arguments.days > 3650:
        parser.error("--days musi być liczbą od 1 do 3650.")
    if arguments.activity_days < 1 or arguments.activity_days > 3650:
        parser.error("--activity-days musi być liczbą od 1 do 3650.")
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


def initialise_database(path: Path) -> sqlite3.Connection:
    """Tworzy niewielką, przenośną bazę lokalną bez serwera."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS synchronizacje (
            nazwa TEXT PRIMARY KEY,
            wartosc TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS pomiary_wagi (
            data TEXT PRIMARY KEY,
            zmierzono_o TEXT,
            waga_kg REAL NOT NULL,
            tkanka_tluszczowa_proc REAL,
            bmi REAL,
            zrodlo_json TEXT NOT NULL,
            zsynchronizowano_o TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS aktywnosci (
            activity_id INTEGER PRIMARY KEY,
            nazwa TEXT,
            typ TEXT,
            rozpoczecie_lokalne TEXT,
            czas_s REAL,
            dystans_m REAL,
            kalorie REAL,
            srednia_predkosc_m_s REAL,
            srednie_tempo_s_km REAL,
            srednia_kadencja_rpm REAL,
            srednie_tetno_bpm REAL,
            maksymalne_tetno_bpm REAL,
            przewyzszenie_m REAL,
            podsumowanie_json TEXT NOT NULL,
            szczegoly_json_plik TEXT NOT NULL,
            zsynchronizowano_o TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS aktywnosci_rozpoczecie_idx
            ON aktywnosci(rozpoczecie_lokalne);
        """
    )
    return connection


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def save_measurements_to_database(
    connection: sqlite3.Connection, measurements: list[dict[str, Any]], synced_at: str
) -> None:
    for measurement in measurements:
        connection.execute(
            """
            INSERT INTO pomiary_wagi (
                data, zmierzono_o, waga_kg, tkanka_tluszczowa_proc, bmi, zrodlo_json,
                zsynchronizowano_o
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(data) DO UPDATE SET
                zmierzono_o = excluded.zmierzono_o,
                waga_kg = excluded.waga_kg,
                tkanka_tluszczowa_proc = excluded.tkanka_tluszczowa_proc,
                bmi = excluded.bmi,
                zrodlo_json = excluded.zrodlo_json,
                zsynchronizowano_o = excluded.zsynchronizowano_o
            """,
            (
                measurement["data"],
                measurement["timestamp"].isoformat(),
                measurement["waga_kg"],
                measurement["tkanka_tluszczowa_proc"],
                measurement["bmi"],
                json_text(measurement),
                synced_at,
            ),
        )


def value_from(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


def normalise_activity(record: dict[str, Any]) -> dict[str, Any]:
    activity_id = value_from(record, "activityId", "activity_id", "id")
    if activity_id is None:
        raise ValueError("Aktywność Garmin nie zawiera activityId.")
    activity_type = value_from(record, "activityType")
    if isinstance(activity_type, dict):
        activity_type = value_from(activity_type, "typeKey", "typeId", "displayName")
    speed = value_from(record, "averageSpeed", "avgSpeed")
    speed_number = float(speed) if speed not in (None, "") else None
    cadence = value_from(record, "averageRunningCadence", "averageBikeCadence", "averageCadence")
    return {
        "activity_id": int(activity_id),
        "nazwa": value_from(record, "activityName", "name"),
        "typ": str(activity_type) if activity_type is not None else None,
        "rozpoczecie_lokalne": value_from(record, "startTimeLocal", "startTimeGMT"),
        "czas_s": value_from(record, "duration", "movingDuration"),
        "dystans_m": value_from(record, "distance"),
        "kalorie": value_from(record, "calories", "activeKilocalories"),
        "srednia_predkosc_m_s": speed_number,
        "srednie_tempo_s_km": 1000 / speed_number if speed_number and speed_number > 0 else None,
        "srednia_kadencja_rpm": cadence,
        "srednie_tetno_bpm": value_from(record, "averageHR", "avgHR"),
        "maksymalne_tetno_bpm": value_from(record, "maxHR"),
        "przewyzszenie_m": value_from(record, "elevationGain", "elevationGainMeters"),
    }


def get_activities(client: Any, start: date, end: date) -> list[dict[str, Any]]:
    """Pobiera aktywności z zakresu dat przez aktualny interfejs biblioteki."""
    activities = client.get_activities_by_date(start.isoformat(), end.isoformat())
    if not isinstance(activities, list):
        raise RuntimeError("Odpowiedź Garmin nie zawiera listy aktywności.")
    return [activity for activity in activities if isinstance(activity, dict)]


def write_private_json(path: Path, data: Any) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        file = os.fdopen(descriptor, "w", encoding="utf-8")
    except Exception:
        os.close(descriptor)
        raise
    with file:
        json.dump(data, file, ensure_ascii=False, indent=2, default=str)


def write_private_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        file = os.fdopen(descriptor, "wb")
    except Exception:
        os.close(descriptor)
        raise
    with file:
        file.write(data)


def save_activities_to_database(
    client: Any,
    connection: sqlite3.Connection,
    activities: list[dict[str, Any]],
    raw_directory: Path,
    original_directory: Path,
    synced_at: str,
) -> int:
    saved = 0
    for activity in activities:
        normalised = normalise_activity(activity)
        details = client.get_activity_details(normalised["activity_id"])
        details_path = raw_directory / f"{normalised['activity_id']}.json"
        write_private_json(details_path, {"podsumowanie": activity, "szczegoly": details})
        original_path = original_directory / f"{normalised['activity_id']}.zip"
        if not original_path.exists():
            original = client.download_activity(
                str(normalised["activity_id"]), client.ActivityDownloadFormat.ORIGINAL
            )
            write_private_bytes(original_path, original)
        try:
            details_path_for_database = str(details_path.relative_to(REPOSITORY_ROOT))
        except ValueError:
            details_path_for_database = str(details_path)
        connection.execute(
            """
            INSERT INTO aktywnosci VALUES (
                :activity_id, :nazwa, :typ, :rozpoczecie_lokalne, :czas_s, :dystans_m,
                :kalorie, :srednia_predkosc_m_s, :srednie_tempo_s_km,
                :srednia_kadencja_rpm, :srednie_tetno_bpm, :maksymalne_tetno_bpm,
                :przewyzszenie_m, :podsumowanie_json, :szczegoly_json_plik,
                :zsynchronizowano_o
            ) ON CONFLICT(activity_id) DO UPDATE SET
                nazwa=excluded.nazwa, typ=excluded.typ,
                rozpoczecie_lokalne=excluded.rozpoczecie_lokalne, czas_s=excluded.czas_s,
                dystans_m=excluded.dystans_m, kalorie=excluded.kalorie,
                srednia_predkosc_m_s=excluded.srednia_predkosc_m_s,
                srednie_tempo_s_km=excluded.srednie_tempo_s_km,
                srednia_kadencja_rpm=excluded.srednia_kadencja_rpm,
                srednie_tetno_bpm=excluded.srednie_tetno_bpm,
                maksymalne_tetno_bpm=excluded.maksymalne_tetno_bpm,
                przewyzszenie_m=excluded.przewyzszenie_m,
                podsumowanie_json=excluded.podsumowanie_json,
                szczegoly_json_plik=excluded.szczegoly_json_plik,
                zsynchronizowano_o=excluded.zsynchronizowano_o
            """,
            {
                **normalised,
                "podsumowanie_json": json_text(activity),
                "szczegoly_json_plik": details_path_for_database,
                "zsynchronizowano_o": synced_at,
            },
        )
        saved += 1
    return saved


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
        headers, rows = read_weight_rows(arguments.weight_data)
        updated_daily = update_daily_rows(rows, headers, measurements)
        updated_weekly = update_last_completed_week(rows, headers, today)
        synced_at = datetime.now(WARSAW).isoformat(timespec="seconds")
        activities = get_activities(
            client, today - timedelta(days=arguments.activity_days - 1), today
        )
        if updated_daily + updated_weekly and not arguments.dry_run:
            write_weight_rows(arguments.weight_data, headers, rows)
        if not arguments.dry_run:
            connection = initialise_database(arguments.database)
            try:
                save_measurements_to_database(connection, measurements, synced_at)
                saved_activities = save_activities_to_database(
                    client,
                    connection,
                    activities,
                    arguments.raw_activity_directory,
                    arguments.original_activity_directory,
                    synced_at,
                )
                connection.execute(
                    """
                    INSERT INTO synchronizacje(nazwa, wartosc) VALUES ('ostatnia_udana', ?)
                    ON CONFLICT(nazwa) DO UPDATE SET wartosc=excluded.wartosc
                    """,
                    (synced_at,),
                )
                connection.commit()
            finally:
                connection.close()
        else:
            saved_activities = 0
        print(
            "Garmin: sprawdzono "
            f"{len(measurements)} pomiarów; zmieniono {updated_daily} dziennych i "
            f"{updated_weekly} tygodniowych rekordów; "
            f"pobrano {len(activities)} aktywności, zapisano {saved_activities}."
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
