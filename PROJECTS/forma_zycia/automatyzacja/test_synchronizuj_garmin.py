from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
import synchronizuj_garmin as sync  # noqa: E402


WEIGHT_HEADERS = list(sync.WEIGHT_COLUMNS)


class SynchronizacjaGarminTest(unittest.TestCase):
    def test_extract_measurements_keeps_the_latest_measurement_per_day(self) -> None:
        measurements = sync.extract_measurements(
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

        self.assertEqual(len(measurements), 1)
        self.assertEqual(measurements[0]["data"], "2026-08-16")
        self.assertEqual(measurements[0]["waga_kg"], 101.4)

    def test_extract_measurements_supports_current_garmin_summary_format(self) -> None:
        measurements = sync.extract_measurements(
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
        weekly_changed = sync.update_last_completed_week(
            rows, WEIGHT_HEADERS, date(2026, 8, 16)
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

        self.assertEqual(sync.merge_activities(rows, [record]), 1)
        self.assertEqual(sync.merge_activities(rows, [record]), 0)
        self.assertEqual(sync.merge_activities(rows, [{**record, "duration": 1900}]), 1)
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
        changed = sync.merge_activities(
            rows,
            [
                {
                    "activityId": 123,
                    "activityType": "running",
                    "startTimeLocal": "2026-08-20 20:30:00",
                }
            ],
        )

        self.assertEqual(changed, 0)
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

            total, changed = sync.bootstrap_activities(source, target, False)
            rows = sync.read_activities(target)

        self.assertEqual((total, changed), (1, 1))
        self.assertEqual(rows["123"]["training_load"], "42")
        self.assertEqual(list(rows["123"]), list(sync.ACTIVITY_COLUMNS))


if __name__ == "__main__":
    unittest.main()
