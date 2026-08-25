from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
import analizuj_wyniki as agent  # noqa: E402


class AnalizatorWynikowTest(unittest.TestCase):
    def test_parses_result_and_reference_range(self) -> None:
        analysis = agent.analyse_pages(
            [
                "Cholesterol LDL bezposredni\n135.486m g/dl powyzej normy\nnorma: <115",
            ],
            "/tmp/raport.pdf",
        )

        self.assertEqual(analysis["extraction"]["results_count"], 1)
        result = analysis["results"][0]
        self.assertEqual(result["parameter"], "Cholesterol LDL bezposredni")
        self.assertEqual(result["value"], 135.486)
        self.assertEqual(result["unit"], "mg/dl")
        self.assertEqual(result["reference_high"], 115.0)
        self.assertEqual(result["status_against_reference"], "powyzej zakresu")

    def test_carries_reference_range_to_next_page(self) -> None:
        analysis = agent.analyse_pages(
            [
                "Trójglicerydy\n148.673m g/dl powyżej normy",
                "norma: 35–100\nInterpretacja",
            ],
            "/tmp/raport.pdf",
        )

        result = analysis["results"][0]
        self.assertEqual(result["page"], 1)
        self.assertEqual(result["reference_low"], 35.0)
        self.assertEqual(result["reference_high"], 100.0)

    def test_rejects_cid_corrupted_pdf_as_low_quality(self) -> None:
        analysis = agent.analyse_pages(
            ["(cid:22)(cid:10)(cid:11) (cid:9)(cid:18)(cid:5)" * 80],
            "/tmp/raport.pdf",
        )

        self.assertEqual(analysis["extraction"]["overall_quality"], "niska")
        self.assertEqual(analysis["results"], [])
        self.assertTrue(any("OCR" in warning for warning in analysis["warnings"]))

    def test_report_contains_safety_boundary_and_page_source(self) -> None:
        analysis = agent.analyse_pages(
            ["Glukoza\n84.78 mg/dl w normie\nnorma: 70–99.99"],
            "/tmp/raport.pdf",
        )

        report = agent.render_markdown(analysis)
        self.assertIn("nie diagnoza", report)
        self.assertIn("s. 1", report)

    def test_keeps_source_date_separate_from_print_date(self) -> None:
        analysis = agent.analyse_pages(
            ["Data wydruku: 25.08.2026"],
            "/tmp/raport.pdf",
            source_date="2026-08-24",
        )

        self.assertEqual(analysis["document"]["source_date"], "2026-08-24")
        self.assertEqual(analysis["document"]["print_date"], "2026-08-25")

    def test_ignores_numbers_in_explanatory_text_without_lab_status(self) -> None:
        analysis = agent.analyse_pages(
            [
                "Wykonuj aktywnosc przez 150 minut tygodniowo.\n"
                "cholesterol HDL powyzej 40 mg/dl jest celem, nie wynikiem.",
            ],
            "/tmp/raport.pdf",
        )

        self.assertEqual(analysis["results"], [])


if __name__ == "__main__":
    unittest.main()
