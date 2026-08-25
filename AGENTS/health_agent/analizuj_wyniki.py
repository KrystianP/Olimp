#!/usr/bin/env python3
"""Lokalne MVP do bezpiecznego odczytu wynikow badan z PDF.

Skrypt wykonuje ekstrakcje i kontrole techniczna. Nie diagnozuje, nie ustala
leczenia i nie zapisuje niczego do CORE ani Todoist.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


STATUS_PATTERNS = (
    ("powyzej normy", "powyzej zakresu"),
    ("ponizej normy", "ponizej zakresu"),
    ("w normie", "w zakresie"),
)
STATUS_ONLY_NAMES = {"egfr", "eGFR".lower()}
FOOTER_PREFIXES = (
    "raport zdrowia",
    "strona ",
    "data wydruku",
    "labplus",
    "ul. ",
    "polska",
)
UNIT_RE = re.compile(
    r"(?P<unit>(?:µ?iu|iu|mg|ng|pg|µg|g|tys|fl|u|%|ml|mmol|µmol)"
    r"(?:\s*/\s*[a-zA-Zµ%]+)?)",
    re.IGNORECASE,
)
NUMBER_RE = re.compile(r"(?<![A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż])(-?\d+(?:[.,]\d+)?)")
RANGE_RE = re.compile(r"(?P<low>-?\d+(?:[.,]\d+)?)\s*[-–—]\s*(?P<high>-?\d+(?:[.,]\d+)?)")
BOUND_RE = re.compile(r"(?P<operator><|>|≤|≥)\s*(?P<value>-?\d+(?:[.,]\d+)?)")


@dataclass
class LabResult:
    parameter: str
    value: float | None
    raw_value: str | None
    unit: str | None
    lab_status: str | None
    reference_text: str | None
    reference_low: float | None
    reference_high: float | None
    status_against_reference: str
    source_pdf: str
    page: int
    extraction_confidence: str


def normalise_number(value: str) -> float:
    return float(value.replace(",", "."))


def strip_icons(text: str) -> str:
    text = re.sub(r"\(cid:\d+\)", " ", text)
    text = re.sub(r"[\ue000-\uf8ff]", " ", text)
    return text


def repair_text(text: str) -> str:
    """Naprawia tylko bezpieczne, czesto spotykane artefakty ekstrakcji."""
    text = unicodedata.normalize("NFC", strip_icons(text))
    text = text.replace("\u00a0", " ")
    replacements = (
        (r"m\s*g\s*/\s*d\s*l", "mg/dl"),
        (r"n\s*g\s*/\s*m\s*l", "ng/ml"),
        (r"p\s*g\s*/\s*m\s*l", "pg/ml"),
        (r"µ\s*I\s*U\s*/\s*m\s*l", "µIU/ml"),
        (r"I\s*U\s*/\s*m\s*l", "IU/ml"),
        (r"µ\s*m\s*o\s*l\s*/\s*l", "µmol/l"),
        (r"t\s*y\s*s\s*/\s*µ\s*l", "tys/µl"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def polish_status(text: str) -> str:
    simplified = (
        text.lower()
        .replace("ą", "a")
        .replace("ę", "e")
        .replace("ł", "l")
        .replace("ń", "n")
        .replace("ó", "o")
        .replace("ś", "s")
        .replace("ź", "z")
        .replace("ż", "z")
    )
    return (
        simplified.replace("powy z ej", "powyzej")
        .replace("poni z ej", "ponizej")
        .replace("norm ie", "normie")
    )


def status_from_line(line: str) -> tuple[str | None, str | None]:
    simplified = polish_status(line)
    for marker, status in STATUS_PATTERNS:
        if marker in simplified:
            return marker, status
    return None, None


def parse_reference(text: str) -> tuple[float | None, float | None]:
    text = repair_text(text)
    range_match = RANGE_RE.search(text)
    if range_match:
        return (
            normalise_number(range_match.group("low")),
            normalise_number(range_match.group("high")),
        )
    bound_match = BOUND_RE.search(text)
    if not bound_match:
        return None, None
    value = normalise_number(bound_match.group("value"))
    if bound_match.group("operator") in ("<", "≤"):
        return None, value
    return value, None


def evaluate_against_reference(
    value: float | None,
    reference_text: str | None,
    explicit_status: str | None,
) -> str:
    if explicit_status:
        return explicit_status
    if value is None or not reference_text:
        return "nie mozna ocenic"
    low, high = parse_reference(reference_text)
    if low is not None and value < low:
        return "ponizej zakresu"
    if high is not None and value > high:
        return "powyzej zakresu"
    return "w zakresie"


def plausible_parameter(text: str, *, allow_digits: bool = False) -> bool:
    text = text.strip()
    if not text or len(text) > 80:
        return False
    lowered = text.lower()
    if lowered.startswith(FOOTER_PREFIXES):
        return False
    if text[0].isdigit() or "wrocław" in lowered or "kraków" in lowered:
        return False
    if lowered.startswith(("interpretacja", "norma:", "badania", "lekarz")):
        return False
    return allow_digits or not any(char.isdigit() for char in text)


def parse_value_line(line: str, previous_line: str) -> tuple[str, float | None, str | None, str | None, str | None] | None:
    line = repair_text(line)
    status_marker, lab_status = status_from_line(line)
    number_match = NUMBER_RE.search(line)

    if not number_match:
        if polish_status(line).strip() == "w normie" and previous_line.strip().lower() in STATUS_ONLY_NAMES:
            return previous_line.strip(), None, None, None, lab_status
        return None

    # W tej wersji wynik musi zaczynać wiersz. Liczby w opisach i poradach
    # występują później w zdaniu i nie są bezpiecznym kandydatem do ekstrakcji.
    if number_match.start() > 0:
        return None

    # MVP akceptuje tylko wiersze jednoznacznie oznaczone przez raport jako
    # wynik (np. "w normie" albo "powyzej normy"). Dzieki temu liczby z
    # opisow, porad i ankiety nie trafiaja omylkowo do historii badan.
    if not status_marker:
        return None

    value_text = number_match.group(1)
    value = normalise_number(value_text)
    tail = line[number_match.end() :]
    unit_match = UNIT_RE.search(tail)
    unit = unit_match.group("unit") if unit_match else None
    parameter = previous_line.strip()
    if not plausible_parameter(parameter, allow_digits=True):
        return None
    return parameter, value, value_text, unit, lab_status


def page_quality(raw_text: str) -> str:
    if not raw_text.strip():
        return "brak tekstu"
    cid_count = raw_text.count("(cid:")
    visible = strip_icons(raw_text)
    alphanumeric = sum(char.isalnum() for char in visible)
    cid_ratio = cid_count / max(len(raw_text), 1)
    if alphanumeric < 80 or cid_ratio > 0.02:
        return "niska"
    if alphanumeric < 250:
        return "srednia"
    return "wysoka"


def extract_date(text: str, fallback: str | None) -> str | None:
    if fallback:
        return fallback
    match = re.search(r"(?:Data badania|Data pobrania|Data wydruku)\s*:\s*(\d{2}\.\d{2}\.\d{4})", text)
    if match:
        day, month, year = match.group(1).split(".")
        return f"{year}-{month}-{day}"
    return fallback


def extract_print_date(text: str) -> str | None:
    match = re.search(r"Data wydruku\s*:\s*(\d{2}\.\d{2}\.\d{4})", text)
    if not match:
        return None
    day, month, year = match.group(1).split(".")
    return f"{year}-{month}-{day}"


def analyse_pages(page_texts: Iterable[str], source_pdf: str, source_date: str | None = None) -> dict[str, object]:
    pages = list(page_texts)
    results: list[LabResult] = []
    page_qualities: list[dict[str, object]] = []
    pending: LabResult | None = None
    document_date = source_date
    print_date = None
    previous_line = ""

    for page_number, raw_text in enumerate(pages, start=1):
        page_qualities.append(
            {
                "page": page_number,
                "quality": page_quality(raw_text),
                "characters": len(raw_text),
            }
        )
        document_date = extract_date(raw_text, document_date)
        print_date = print_date or extract_print_date(raw_text)
        for raw_line in raw_text.splitlines():
            line = repair_text(raw_line)
            if not line:
                continue

            if line.lower().startswith("norma:"):
                if pending is not None:
                    pending.reference_text = line[6:].strip()
                    pending.reference_low, pending.reference_high = parse_reference(pending.reference_text)
                    pending.status_against_reference = evaluate_against_reference(
                        pending.value, pending.reference_text, pending.lab_status
                    )
                    pending = None
                previous_line = line
                continue

            parsed = parse_value_line(line, previous_line)
            if parsed is not None:
                if pending is not None:
                    pending = None
                parameter, value, raw_value, unit, lab_status = parsed
                result = LabResult(
                    parameter=parameter,
                    value=value,
                    raw_value=raw_value,
                    unit=unit,
                    lab_status=lab_status,
                    reference_text=None,
                    reference_low=None,
                    reference_high=None,
                    status_against_reference=evaluate_against_reference(value, None, lab_status),
                    source_pdf=source_pdf,
                    page=page_number,
                    extraction_confidence="wysoka" if page_quality(raw_text) == "wysoka" else "srednia",
                )
                results.append(result)
                # Zakres moze znajdowac sie w kolejnym wierszu albo na kolejnej
                # stronie, dlatego zawsze przechowujemy ostatni rekord bez
                # zakresu do czasu jego uzupelnienia.
                pending = result
                previous_line = line
                continue

            if plausible_parameter(line, allow_digits=True):
                previous_line = line

    low_quality_pages = [page["page"] for page in page_qualities if page["quality"] in ("niska", "brak tekstu")]
    if results and not low_quality_pages:
        overall_quality = "wysoka"
    elif results:
        overall_quality = "srednia"
    else:
        overall_quality = "niska"

    warnings: list[str] = []
    if not results:
        warnings.append("Nie znaleziono pewnych wynikow. PDF wymaga OCR albo recznego potwierdzenia.")
    if low_quality_pages:
        pages_text = ", ".join(str(page) for page in low_quality_pages)
        warnings.append(f"Niska jakosc ekstrakcji na stronach: {pages_text}.")
    warnings.append("Odczyt techniczny nie jest diagnoza ani interpretacja lekarska.")

    return {
        "schema_version": "0.1",
        "document": {
            "source_pdf": source_pdf,
            "source_date": document_date,
            "print_date": print_date,
            "pages": len(pages),
        },
        "extraction": {
            "overall_quality": overall_quality,
            "pages": page_qualities,
            "results_count": len(results),
        },
        "warnings": warnings,
        "results": [asdict(result) for result in results],
    }


def analyse_pdf(pdf_path: Path) -> dict[str, object]:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError("Brakuje pakietu pypdf. Uzyj bundlowanego srodowiska Pythona.") from error

    reader = PdfReader(str(pdf_path))
    page_texts = [(page.extract_text() or "") for page in reader.pages]
    fallback_date = None
    folder_date = re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})", pdf_path.parent.name)
    if folder_date:
        day, month, year = folder_date.groups()
        fallback_date = f"{year}-{month}-{day}"
    return analyse_pages(page_texts, str(pdf_path.resolve()), fallback_date)


def render_markdown(analysis: dict[str, object]) -> str:
    document = analysis["document"]
    extraction = analysis["extraction"]
    results = analysis["results"]
    warnings = analysis["warnings"]
    lines = [
        "# MVP - analiza techniczna wynikow badan",
        "",
        "## Granica bezpieczenstwa",
        "",
        "To jest techniczny odczyt danych z PDF, a nie diagnoza ani zalecenie leczenia.",
        "Wyniki wymagaja potwierdzenia i interpretacji w kontekscie medycznym.",
        "",
        "## Dokument",
        "",
        f"- Zrodlo: `{document['source_pdf']}`",
        f"- Data przypisana do źródła: `{document['source_date'] or 'brak'}`",
        f"- Data wydruku raportu: `{document['print_date'] or 'brak'}`",
        f"- Liczba stron: `{document['pages']}`",
        f"- Jakosc ekstrakcji: **{extraction['overall_quality']}**",
        f"- Odczytane rekordy: `{extraction['results_count']}`",
        "",
        "## Ostrzezenia",
        "",
    ]
    lines.extend(f"- {warning}" for warning in warnings)
    lines.extend(
        [
            "",
            "## Odczytane wyniki",
            "",
            "| Parametr | Wynik | Jednostka | Zakres laboratorium | Ocena techniczna | Zrodlo |",
            "|---|---:|---|---|---|---|",
        ]
    )
    if not results:
        lines.append("| Brak pewnych rekordow |  |  |  | Wymaga recznej weryfikacji |  |")
    else:
        for result in results:
            reference = result["reference_text"] or "brak"
            value = result["raw_value"] or "brak"
            unit = result["unit"] or ""
            status = result["status_against_reference"]
            source = f"s. {result['page']}"
            lines.append(f"| {result['parameter']} | {value} | {unit} | {reference} | {status} | {source} |")
    lines.extend(
        [
            "",
            "## Co dalej",
            "",
            "1. Ręcznie potwierdzić rekordy o średniej lub niskiej pewności.",
            "2. Dopiero potem zapisać zatwierdzone dane do historii badań.",
            "3. Porównywać kolejne pomiary dopiero po ujednoliceniu dat, jednostek i laboratoriów.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Odczyt wynikow badan z PDF bez diagnozowania.")
    parser.add_argument("pdf", type=Path, help="Sciezka do zrodlowego pliku PDF.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Katalog wyjsciowy. Bez opcji raport jest wypisywany na stdout.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    if not arguments.pdf.is_file():
        raise SystemExit(f"Nie znaleziono pliku PDF: {arguments.pdf}")
    analysis = analyse_pdf(arguments.pdf)
    markdown = render_markdown(analysis)
    if arguments.output:
        arguments.output.mkdir(parents=True, exist_ok=True)
        (arguments.output / "analiza.md").write_text(markdown, encoding="utf-8")
        (arguments.output / "ekstrakcja.json").write_text(
            json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Zapisano raport: {arguments.output / 'analiza.md'}")
        print(f"Zapisano dane ekstrakcji: {arguments.output / 'ekstrakcja.json'}")
    else:
        print(markdown, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
