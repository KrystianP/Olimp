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


if __name__ == "__main__":
    unittest.main()
