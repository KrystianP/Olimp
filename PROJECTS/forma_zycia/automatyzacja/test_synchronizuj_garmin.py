from __future__ import annotations

import contextlib
import csv
import io
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
import synchronizuj_garmin as sync  # noqa: E402


WEIGHT_HEADERS = list(sync.WEIGHT_COLUMNS)


class StubInnerGarminClient:
    """Minimalny odpowiednik klienta biblioteki: serializuje i zapisuje token."""

    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.dumped: str | None = None

    def dumps(self) -> str:
        return self.payload

    def dump(self, path: str) -> None:
        self.dumped = path


class StubGarminClient:
    def __init__(self, payload: str) -> None:
        self.client = StubInnerGarminClient(payload)



def daily(day: str, weight: str) -> dict[str, str]:
    """Wiersz pomiaru dziennego wypełniony tak, jak zapisuje go synchronizacja."""
    row = {header: "" for header in WEIGHT_HEADERS}
    row.update({"data": day, "waga_kg": weight, "typ_rekordu": "pomiar_dzienny"})
    return row


class SynchronizacjaGarminTest(unittest.TestCase):
    def test_extract_measurements_keeps_the_latest_measurement_per_day(self) -> None:
        measurements, problems = sync.extract_measurements(
            {
                "dateWeightList": [
                    {
                        "dateTimestampLocal": "2026-08-16T06:15:00",
                        "weight": 101600,
                        "bodyFat": 30.0,
                        "bmi": 30.0,
                    },
                    {
                        "dateTimestampLocal": "2026-08-16T06:25:00",
                        "weight": 101400,
                        "bodyFat": 29.9,
                        "bmi": 29.9,
                    },
                ]
            }
        )

        self.assertEqual(problems, [])
        self.assertEqual(len(measurements), 1)
        self.assertEqual(measurements[0]["data"], "2026-08-16")
        self.assertEqual(measurements[0]["waga_kg"], 101.4)

    def test_extract_measurements_supports_current_garmin_summary_format(self) -> None:
        measurements, _ = sync.extract_measurements(
            {
                "dailyWeightSummaries": [
                    {
                        "summaryDate": "2026-08-16",
                        "latestWeight": {
                            "weight": 101400,
                            "bodyFat": 29.9,
                            "bmi": 29.9,
                        },
                    }
                ]
            }
        )

        self.assertEqual(len(measurements), 1)
        self.assertEqual(measurements[0]["data"], "2026-08-16")
        self.assertEqual(measurements[0]["waga_kg"], 101.4)

    def test_updates_a_daily_row_and_completes_last_week(self) -> None:
        rows = [
            {
                "data": "2026-08-09",
                "waga_kg": "103",
                "tkanka_tluszczowa_proc": "",
                "bmi": "",
                "typ_rekordu": "srednia_tygodniowa",
                "okres_od": "2026-08-03",
                "okres_do": "2026-08-09",
                "zmiana_kg": "",
            },
            *[
                {
                    "data": f"2026-08-{day:02}",
                    "waga_kg": "102",
                    "tkanka_tluszczowa_proc": "",
                    "bmi": "",
                    "typ_rekordu": "pomiar_dzienny",
                    "okres_od": "",
                    "okres_do": "",
                    "zmiana_kg": "",
                }
                for day in range(10, 16)
            ],
        ]
        changed = sync.update_daily_rows(
            rows,
            WEIGHT_HEADERS,
            [
                {
                    "data": "2026-08-15",
                    "timestamp": None,
                    "waga_kg": 101.5,
                    "tkanka_tluszczowa_proc": 30.1,
                    "bmi": 30.0,
                }
            ],
        )
        weekly_changed = sync.update_weekly_averages(
            rows, WEIGHT_HEADERS, date(2026, 8, 16), 14
        )

        self.assertEqual(changed, 1)
        self.assertEqual(weekly_changed, 1)
        weekly_row = [
            row
            for row in rows
            if row["typ_rekordu"] == "srednia_tygodniowa"
            and row["okres_do"] == "2026-08-15"
        ][0]
        self.assertEqual(weekly_row["waga_kg"], "101.9")

    def test_daily_update_rounds_weight_and_preserves_missing_garmin_fields(self) -> None:
        row = {header: "" for header in WEIGHT_HEADERS}
        row.update(
            {
                "data": "2026-09-05",
                "waga_kg": "98.8",
                "bmi": "29.2",
                "typ_rekordu": "pomiar_dzienny",
            }
        )
        changed = sync.update_daily_rows(
            [row],
            WEIGHT_HEADERS,
            [
                {
                    "data": "2026-09-05",
                    "timestamp": None,
                    "waga_kg": 98.78,
                    "tkanka_tluszczowa_proc": None,
                    "bmi": None,
                }
            ],
        )

        self.assertEqual(changed, 0)
        self.assertEqual(row["waga_kg"], "98.8")
        self.assertEqual(row["bmi"], "29.2")

    def test_write_weight_rows_preserves_csv_schema(self) -> None:
        row = {header: "" for header in WEIGHT_HEADERS}
        row.update(
            {"data": "2026-08-16", "waga_kg": "101.4", "typ_rekordu": "pomiar_dzienny"}
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "waga.csv"
            sync.write_weight_rows(path, WEIGHT_HEADERS, [row])
            headers, rows = sync.read_weight_rows(path)

        self.assertEqual(headers, WEIGHT_HEADERS)
        self.assertEqual(rows, [row])

    def test_write_weight_rows_preserves_existing_order(self) -> None:
        newer = {header: "" for header in WEIGHT_HEADERS}
        newer.update(
            {"data": "2026-09-06", "waga_kg": "98.6", "typ_rekordu": "pomiar_dzienny"}
        )
        older = {header: "" for header in WEIGHT_HEADERS}
        older.update(
            {"data": "2026-09-05", "waga_kg": "99.1", "typ_rekordu": "srednia_tygodniowa"}
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "waga.csv"
            sync.write_weight_rows(path, WEIGHT_HEADERS, [newer, older])
            _, rows = sync.read_weight_rows(path)

        self.assertEqual([row["data"] for row in rows], ["2026-09-06", "2026-09-05"])

    def test_rate_limit_error_has_an_actionable_message(self) -> None:
        message = sync.describe_error(Exception("Mobile login returned 429 — IP rate limited"))
        self.assertIn("odczekaj co najmniej godzinę", message)

    def test_normalise_activity_keeps_only_the_allowlisted_fields(self) -> None:
        activity = sync.normalise_activity(
            {
                "activityId": 123,
                "activityType": {"typeKey": "running"},
                "startTimeLocal": "2026-08-20 20:30:00",
                "duration": 1800,
                "distance": 5000,
                "calories": 480,
                "averageHR": 145,
                "maxHR": 168,
                "elevationGain": 42,
                "activityTrainingLoad": 83.25,
                "startLatitude": 50.0,
                "deviceId": 999,
                "fit_file_path": "/private/file.fit",
            }
        )

        self.assertEqual(list(activity), list(sync.ACTIVITY_COLUMNS))
        self.assertEqual(activity["activity_id"], "123")
        self.assertEqual(activity["activity_type"], "running")
        self.assertEqual(activity["training_load"], "83.25")
        self.assertNotIn("startLatitude", activity)
        self.assertNotIn("deviceId", activity)
        self.assertNotIn("fit_file_path", activity)

    def test_merge_activities_is_idempotent_and_updates_by_id(self) -> None:
        record = {
            "activityId": 123,
            "activityType": {"typeKey": "running"},
            "startTimeLocal": "2026-08-20 20:30:00",
            "duration": 1800,
        }
        rows: dict[str, dict[str, str]] = {}

        self.assertEqual(sync.merge_activities(rows, [record]), (1, []))
        self.assertEqual(sync.merge_activities(rows, [record]), (0, []))
        self.assertEqual(
            sync.merge_activities(rows, [{**record, "duration": 1900}]), (1, [])
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows["123"]["duration_seconds"], "1900")

    def test_merge_activities_does_not_erase_optional_existing_metrics(self) -> None:
        original = sync.normalise_activity(
            {
                "activityId": 123,
                "activityType": "running",
                "startTimeLocal": "2026-08-20 20:30:00",
                "activityTrainingLoad": 42,
            }
        )
        rows = {"123": original}
        changed, problems = sync.merge_activities(
            rows,
            [
                {
                    "activityId": 123,
                    "activityType": "running",
                    "startTimeLocal": "2026-08-20 20:30:00",
                }
            ],
        )

        self.assertEqual((changed, problems), (0, []))
        self.assertEqual(rows["123"]["training_load"], "42")

    def test_weight_format_keeps_one_decimal_place(self) -> None:
        self.assertEqual(sync.format_fixed(100.04, 1), "100.0")

    def test_write_and_read_activities_preserves_unique_sorted_rows(self) -> None:
        first = sync.normalise_activity(
            {
                "activityId": 1,
                "activityType": "walking",
                "startTimeLocal": "2026-08-19 10:00:00",
            }
        )
        second = sync.normalise_activity(
            {
                "activityId": 2,
                "activityType": "running",
                "startTimeLocal": "2026-08-20 10:00:00",
            }
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "aktywnosci.csv"
            sync.write_activities(path, {"2": second, "1": first})
            rows = sync.read_activities(path)
            with path.open(encoding="utf-8") as file:
                ordered_ids = [row["activity_id"] for row in csv.DictReader(file)]

        self.assertEqual(set(rows), {"1", "2"})
        self.assertEqual(ordered_ids, ["1", "2"])

    def test_bootstrap_combines_summary_with_allowlisted_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "pobrane_treningi"
            metadata = source / "metadata"
            metadata.mkdir(parents=True)
            (source / "activities_summary.json").write_text(
                json.dumps(
                    [
                        {
                            "activityId": "123",
                            "activityType": "running",
                            "startTimeLocal": "2026-08-20 20:30:00",
                            "fit_file_path": "/private/file.fit",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            (metadata / "123.json").write_text(
                json.dumps(
                    {
                        "activityId": "123",
                        "activityType": {"typeKey": "running"},
                        "startTimeLocal": "2026-08-20 20:30:00",
                        "activityTrainingLoad": 42,
                        "startLatitude": 50.0,
                    }
                ),
                encoding="utf-8",
            )
            target = root / "aktywnosci.csv"

            total, changed, problems = sync.bootstrap_activities(source, target, False)
            rows = sync.read_activities(target)

        self.assertEqual((total, changed, problems), (1, 1, []))
        self.assertEqual(rows["123"]["training_load"], "42")
        self.assertEqual(list(rows["123"]), list(sync.ACTIVITY_COLUMNS))

    # -- odporność na pojedynczy wadliwy rekord ------------------------------

    def test_one_broken_measurement_does_not_lose_the_healthy_ones(self) -> None:
        measurements, problems = sync.extract_measurements(
            {
                "dateWeightList": [
                    {"dateTimestampLocal": "2026-08-16T06:15:00", "weight": 101400},
                    {"dateTimestampLocal": "2026-08-17T06:15:00", "weight": 4200},
                    {"dateTimestampLocal": "2026-08-18T06:15:00", "weight": 101200},
                ]
            }
        )

        self.assertEqual([item["data"] for item in measurements], ["2026-08-16", "2026-08-18"])
        self.assertEqual(len(problems), 1)
        self.assertIn("pominięto pomiar wagi", problems[0])

    def test_only_broken_measurements_are_reported_as_a_failure(self) -> None:
        with self.assertRaises(RuntimeError) as raised:
            sync.extract_measurements(
                {"dateWeightList": [{"dateTimestampLocal": "2026-08-17T06:15:00", "weight": 4200}]}
            )

        self.assertIn("nie nadawał się do zapisu", str(raised.exception))

    def test_an_empty_garmin_window_is_not_an_error(self) -> None:
        self.assertEqual(sync.extract_measurements({"dateWeightList": []}), ([], []))

    def test_one_broken_activity_does_not_lose_the_healthy_ones(self) -> None:
        rows: dict[str, dict[str, str]] = {}
        changed, problems = sync.merge_activities(
            rows,
            [
                {"activityId": 1, "activityType": "running", "startTimeLocal": "2026-08-20 20:30:00"},
                {"activityType": "running", "startTimeLocal": "2026-08-21 20:30:00"},
                {"activityId": 3, "activityType": "walking", "startTimeLocal": "2026-08-22 20:30:00"},
            ],
        )

        self.assertEqual(changed, 2)
        self.assertEqual(set(rows), {"1", "3"})
        self.assertEqual(len(problems), 1)
        self.assertIn("pominięto aktywność", problems[0])

    # -- średnie tygodniowe ---------------------------------------------------

    def test_completed_week_ends_cover_the_whole_window(self) -> None:
        self.assertEqual(
            sync.completed_week_ends(date(2026, 9, 6), 14),
            [date(2026, 8, 29), date(2026, 9, 5)],
        )
        self.assertEqual(
            sync.completed_week_ends(date(2026, 9, 6), 1), [date(2026, 9, 5)]
        )

    def test_a_late_measurement_completes_a_week_that_was_skipped_before(self) -> None:
        rows = [
            daily(f"2026-08-{day:02}", weight)
            for day, weight in (
                (23, "100.0"), (24, "100.0"), (25, "100.0"),
                (30, "99.0"), (31, "99.0"),
            )
        ]
        rows.append(daily("2026-09-01", "99.0"))

        changed = sync.update_weekly_averages(rows, WEIGHT_HEADERS, date(2026, 9, 6), 14)
        weekly = {
            row["okres_do"]: row for row in rows if row["typ_rekordu"] == "srednia_tygodniowa"
        }

        self.assertEqual(changed, 2)
        self.assertEqual(weekly["2026-08-29"]["waga_kg"], "100.0")
        self.assertEqual(weekly["2026-09-05"]["waga_kg"], "99.0")
        self.assertEqual(weekly["2026-09-05"]["zmiana_kg"], "-1.0")

    def test_weekly_change_stays_empty_when_the_previous_week_is_missing(self) -> None:
        rows = [
            daily("2026-08-16", "103.0"),
            *[daily(f"2026-08-{day:02}", "99.0") for day in (30, 31)],
            daily("2026-09-01", "99.0"),
        ]

        sync.update_weekly_averages(rows, WEIGHT_HEADERS, date(2026, 9, 6), 14)
        weekly = [row for row in rows if row["typ_rekordu"] == "srednia_tygodniowa"]

        self.assertEqual(len(weekly), 1)
        self.assertEqual(weekly[0]["okres_do"], "2026-09-05")
        self.assertEqual(weekly[0]["zmiana_kg"], "")

    def test_weekly_change_uses_the_adjacent_week_not_the_last_row_in_the_file(self) -> None:
        older = {header: "" for header in WEIGHT_HEADERS}
        older.update(
            {
                "data": "2026-08-29",
                "waga_kg": "100.0",
                "typ_rekordu": "srednia_tygodniowa",
                "okres_od": "2026-08-23",
                "okres_do": "2026-08-29",
            }
        )
        stray = {header: "" for header in WEIGHT_HEADERS}
        stray.update(
            {
                "data": "2026-07-04",
                "waga_kg": "90.0",
                "typ_rekordu": "srednia_tygodniowa",
                "okres_od": "2026-06-28",
                "okres_do": "2026-07-04",
            }
        )
        rows = [
            older,
            *[daily(f"2026-08-{day:02}", "99.0") for day in (30, 31)],
            daily("2026-09-01", "99.0"),
            stray,
        ]

        sync.update_weekly_averages(rows, WEIGHT_HEADERS, date(2026, 9, 6), 7)
        weekly = [
            row
            for row in rows
            if row["typ_rekordu"] == "srednia_tygodniowa" and row["okres_do"] == "2026-09-05"
        ]

        self.assertEqual(weekly[0]["zmiana_kg"], "-1.0")

    # -- dzienna zmiana masy --------------------------------------------------

    def test_daily_change_is_filled_for_consecutive_days_only(self) -> None:
        rows = [
            daily("2026-09-01", "99.0"),
            daily("2026-09-04", "99.4"),
            daily("2026-09-05", "98.8"),
            daily("2026-09-06", "98.6"),
        ]

        changed = sync.refresh_daily_changes(rows, date(2026, 9, 6), 14)

        self.assertEqual(changed, 2)
        self.assertEqual([row["zmiana_kg"] for row in rows], ["", "", "-0.6", "-0.2"])

    def test_daily_change_outside_the_window_is_left_alone(self) -> None:
        rows = [daily("2026-08-01", "99.0"), daily("2026-08-02", "98.5")]

        self.assertEqual(sync.refresh_daily_changes(rows, date(2026, 9, 6), 14), 0)
        self.assertEqual([row["zmiana_kg"] for row in rows], ["", ""])

    def test_no_change_is_written_without_a_negative_zero(self) -> None:
        self.assertEqual(sync.format_change(-0.04), "0.0")
        self.assertEqual(sync.format_change(0.0), "0.0")
        self.assertEqual(sync.format_change(-0.65), "-0.7")

    # -- token ----------------------------------------------------------------

    def test_token_fingerprint_ignores_key_order_and_hides_the_token(self) -> None:
        first = sync.fingerprint_payload('{"di_token": "sekret", "di_refresh_token": "b"}')
        second = sync.fingerprint_payload('{"di_refresh_token": "b", "di_token": "sekret"}')

        self.assertEqual(first, second)
        self.assertEqual(len(str(first)), 12)
        self.assertNotIn("sekret", str(first))
        self.assertNotEqual(
            first, sync.fingerprint_payload('{"di_token": "inny", "di_refresh_token": "b"}')
        )
        self.assertIsNone(sync.fingerprint_payload("nie-json"))

    def test_a_refreshed_token_is_saved_and_reported_once(self) -> None:
        client = StubGarminClient('{"di_token": "nowy", "di_refresh_token": "nowy"}')
        with tempfile.TemporaryDirectory() as temporary_directory:
            token_store = Path(temporary_directory) / "garmin"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                sync.report_token_state(client, token_store, "odcisk-sprzed")

            self.assertEqual(client.client.dumped, str(token_store))
            self.assertIn(sync.TOKEN_REFRESHED_MARKER, output.getvalue())
            self.assertNotIn("nowy", output.getvalue())

    def test_an_unchanged_token_is_neither_saved_nor_reported(self) -> None:
        payload = '{"di_token": "ten-sam"}'
        client = StubGarminClient(payload)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            sync.report_token_state(client, Path("/nieistotne"), sync.fingerprint_payload(payload))

        self.assertIsNone(client.client.dumped)
        self.assertEqual(output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
