from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
import synchronizuj_garmin as sync  # noqa: E402


HEADERS = list(sync.REQUIRED_COLUMNS)


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
            HEADERS,
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

        weekly_changed = sync.update_last_completed_week(rows, HEADERS, date(2026, 8, 16))

        self.assertEqual(changed, 1)
        self.assertEqual(weekly_changed, 1)
        weekly_row = rows[-1]
        self.assertEqual(weekly_row["typ_rekordu"], "srednia_tygodniowa")
        self.assertEqual(weekly_row["okres_od"], "2026-08-09")
        self.assertEqual(weekly_row["okres_do"], "2026-08-15")
        self.assertEqual(weekly_row["waga_kg"], "101.9")

    def test_write_weight_rows_preserves_csv_schema(self) -> None:
        row = {header: "" for header in HEADERS}
        row.update({"data": "2026-08-16", "waga_kg": "101.4", "typ_rekordu": "pomiar_dzienny"})
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "waga.csv"
            sync.write_weight_rows(path, HEADERS, [row])
            headers, rows = sync.read_weight_rows(path)

        self.assertEqual(headers, HEADERS)
        self.assertEqual(rows, [row])

    def test_rate_limit_error_has_an_actionable_message(self) -> None:
        message = sync.describe_error(Exception("Mobile login returned 429 — IP rate limited"))

        self.assertIn("odczekaj co najmniej godzinę", message)

    def test_normalise_activity_extracts_future_application_fields(self) -> None:
        activity = sync.normalise_activity(
            {
                "activityId": 123,
                "activityName": "Wieczorny bieg",
                "activityType": {"typeKey": "running"},
                "startTimeLocal": "2026-08-20 20:30:00",
                "duration": 1800,
                "distance": 5000,
                "calories": 480,
                "averageSpeed": 2.5,
                "averageRunningCadence": 164,
                "averageHR": 145,
                "maxHR": 168,
                "elevationGain": 42,
            }
        )

        self.assertEqual(activity["activity_id"], 123)
        self.assertEqual(activity["typ"], "running")
        self.assertEqual(activity["srednie_tempo_s_km"], 400)
        self.assertEqual(activity["srednia_kadencja_rpm"], 164)

    def test_database_saves_raw_details_and_activity_summary(self) -> None:
        class Client:
            def get_activity_details(self, activity_id: int) -> dict[str, object]:
                return {"activityId": activity_id, "activityDetailMetrics": ["fake"]}

            class ActivityDownloadFormat:
                ORIGINAL = "original"

            def download_activity(self, activity_id: str, dl_fmt: str) -> bytes:
                assert dl_fmt == "original"
                return b"fake-original"

        activity = {
            "activityId": 123,
            "activityName": "Spacer",
            "activityType": {"typeKey": "walking"},
            "startTimeLocal": "2026-08-20 20:30:00",
            "duration": 1800,
            "distance": 2500,
            "calories": 180,
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            connection = sync.initialise_database(directory / "garmin.sqlite")
            saved = sync.save_activities_to_database(
                Client(),
                connection,
                [activity],
                directory / "raw",
                directory / "original",
                "2026-08-20T23:45:00+02:00",
            )
            result = connection.execute(
                "SELECT activity_id, kalorie, szczegoly_json_plik FROM aktywnosci"
            ).fetchone()
            connection.close()

            self.assertEqual(saved, 1)
            self.assertEqual(result[0], 123)
            self.assertEqual(result[1], 180)
            self.assertTrue((directory / "raw" / "123.json").is_file())
            self.assertEqual((directory / "original" / "123.zip").read_bytes(), b"fake-original")


if __name__ == "__main__":
    unittest.main()
