#!/usr/bin/env python3
"""Przegląd tygodniowy: liczby potrzebne do decyzji, bez rekomendacji.

Skrypt nie planuje i nie ocenia. Wypisuje stan celów mierzalnych, tempo
wymagane do terminu oraz jakość danych, żeby przegląd trwał kwadrans, a nie
godzinę. Wybór działań pozostaje decyzją Krystiana i zapada poza tym plikiem.

Statusy i terminy pochodzą z `CORE/cele.md`, a nie z tego pliku. Skrypt zna
tylko sposób pomiaru każdego celu i milczy o celu, który przestał być aktywny.

Użycie:
    python3 przeglad.py
"""

from __future__ import annotations

import csv
import re
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
CELE = ROOT / "CORE" / "cele.md"
WAGA = ROOT / "DATA" / "waga.csv"
AKTYWNOSCI = ROOT / "DATA" / "garmin" / "aktywnosci.csv"

BIEG = ("running", "treadmill_running", "trail_running", "indoor_running")
SILA = ("strength_training", "indoor_cardio_strength")


@dataclass
class Cel:
    """Cel odczytany z `CORE/cele.md`."""

    identyfikator: str
    status: str
    tresc: str
    pola: dict[str, str] = field(default_factory=dict)

    @property
    def termin(self) -> date | None:
        return parse_date(self.pola.get("Termin osiągnięcia", ""))


def parse_date(value: str) -> date | None:
    match = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", value)
    if not match:
        return None
    day, month, year = (int(part) for part in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def read_goals(path: Path) -> dict[str, Cel]:
    """Czyta cele wraz ze statusem i polami podrzędnymi."""
    goals: dict[str, Cel] = {}
    current: Cel | None = None
    header = re.compile(r"^\s*\d+\.\s*\[([A-Z]{3}-\d{3})\]\s*\[(\w+)\]\s*(.*)$")
    field_line = re.compile(r"^\s+-\s+([^:]+):\s*(.*)$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = header.match(line)
        if match:
            current = Cel(match.group(1), match.group(2), match.group(3).strip())
            goals[current.identyfikator] = current
            continue
        if current is None:
            continue
        subfield = field_line.match(line)
        if subfield:
            current.pola.setdefault(subfield.group(1).strip(), subfield.group(2).strip())
        elif line.strip() and not line.startswith(" "):
            current = None
    return goals


def read_weights(path: Path) -> list[tuple[date, float]]:
    rows: list[tuple[date, float]] = []
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("typ_rekordu") != "pomiar_dzienny" or not row.get("waga_kg"):
                continue
            try:
                rows.append((date.fromisoformat(row["data"]), float(row["waga_kg"])))
            except ValueError:
                continue
    return sorted(rows)


def read_activities(path: Path) -> list[tuple[date, str]]:
    rows: list[tuple[date, str]] = []
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            stamp = (row.get("start_time_local") or "")[:10]
            try:
                rows.append((date.fromisoformat(stamp), row.get("activity_type", "")))
            except ValueError:
                continue
    return sorted(rows)


def last_body_fat(path: Path) -> date | None:
    latest: date | None = None
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if not row.get("tkanka_tluszczowa_proc"):
                continue
            try:
                day = date.fromisoformat(row["data"])
            except ValueError:
                continue
            if latest is None or day > latest:
                latest = day
    return latest


def average(values: list[float]) -> float | None:
    return round(mean(values), 2) if values else None


def window_average(rows: list[tuple[date, float]], end: date, days: int = 7) -> float | None:
    start = end - timedelta(days=days - 1)
    return average([weight for day, weight in rows if start <= day <= end])


def weeks_between(start: date, end: date) -> float:
    return max((end - start).days / 7, 0.01)


def line(label: str, value: str) -> str:
    return f"  {label:<26}{value}"


def report_weight(goals: dict[str, Cel], today: date) -> list[str]:
    cel = goals.get("ZDR-001")
    if cel is None or cel.status != "aktywne":
        return ["ZDR-001 nie jest aktywny w CORE/cele.md — pomijam."]
    rows = read_weights(WAGA)
    if not rows:
        return ["ZDR-001: brak pomiarów masy ciała."]
    target = 85.0
    now = window_average(rows, today)
    earlier = window_average(rows, today - timedelta(days=28))
    out = [f"ZDR-001 — masa ciała do {target:.0f} kg (termin: {cel.termin:%d.%m.%Y})"]
    if now is None:
        return out + [line("stan", "brak pomiarów z ostatnich 7 dni")]
    out.append(line("średnia 7 dni", f"{now:.2f} kg"))
    if earlier is not None:
        tempo = (now - earlier) / 4
        out.append(line("tempo z 4 tygodni", f"{tempo:+.2f} kg/tydzień"))
    if cel.termin:
        weeks = weeks_between(today, cel.termin)
        wymagane = (now - target) / weeks
        out.append(line("wymagane tempo", f"{wymagane:.2f} kg/tydzień"))
        out.append(line("pozostało", f"{now - target:.1f} kg w {weeks:.0f} tygodni"))
    return out


def report_training(
    goals: dict[str, Cel], today: date, identyfikator: str, nazwa: str,
    typy: tuple[str, ...], start: date, target: int,
) -> list[str]:
    cel = goals.get(identyfikator)
    if cel is None or cel.status != "aktywne":
        return [f"{identyfikator} nie jest aktywny w CORE/cele.md — pomijam."]
    rows = read_activities(AKTYWNOSCI)
    done = [day for day, kind in rows if kind in typy and start <= day <= today]
    out = [f"{identyfikator} — {nazwa}: {target} do {cel.termin:%d.%m.%Y}"]
    out.append(line("wykonane", f"{len(done)} od {start:%d.%m.%Y}"))
    out.append(line("tempo dotychczas", f"{len(done) / weeks_between(start, today):.2f}/tydzień"))
    if cel.termin:
        weeks = weeks_between(today, cel.termin)
        brakuje = max(target - len(done), 0)
        out.append(line("wymagane tempo", f"{brakuje / weeks:.2f}/tydzień"))
        out.append(line("pozostało", f"{brakuje} w {weeks:.0f} tygodni"))
    return out


def report_data_quality(today: date) -> list[str]:
    out = ["Jakość danych"]
    weights = read_weights(WAGA)
    measured = {day for day, _ in weights}
    missing = [
        today - timedelta(days=offset)
        for offset in range(14)
        if today - timedelta(days=offset) not in measured
    ]
    out.append(line("pomiary wagi (14 dni)", f"{14 - len(missing)}/14"))
    if missing:
        out.append(line("brakujące dni", ", ".join(d.isoformat() for d in sorted(missing))))
    activities = read_activities(AKTYWNOSCI)
    if activities:
        out.append(line("ostatnia aktywność", activities[-1][0].isoformat()))
    fat = last_body_fat(WAGA)
    out.append(
        line("ostatni pomiar tkanki", fat.isoformat() if fat else "brak w całej historii")
    )
    return out


def report_abstinence(goals: dict[str, Cel], today: date) -> list[str]:
    """Licznik abstynencji. Podstawą jest deklaracja Krystiana, nie pomiar."""
    cel = goals.get("ZDR-004")
    if cel is None or cel.status != "aktywne":
        return ["ZDR-004 nie jest aktywny w CORE/cele.md — pomijam."]
    start = parse_date(cel.pola.get("Data rozpoczęcia", ""))
    if start is None:
        return ["ZDR-004 — brak daty rozpoczęcia w CORE/cele.md."]
    return [
        "ZDR-004 — abstynencja (deklaracja, nie pomiar)",
        line("dni od", f"{(today - start).days} dni od {start:%d.%m.%Y}"),
    ]


def report_unmeasured(goals: dict[str, Cel], today: date, horyzont: int = 180) -> list[str]:
    """Cele aktywne bez liczby w danych, z terminem w zasięgu decyzji.

    Pełna lista ma ponad dwadzieścia pozycji i zamieniłaby kwadrans przeglądu w
    kolejne planowanie. Widoczne są tylko cele z terminem w najbliższych
    miesiącach; reszta jest policzona, żeby nie zniknęła z pola widzenia.
    """
    mierzone = {"ZDR-001", "ZDR-004", "SPR-001", "SPR-002"}
    brak = [
        cel
        for cel in goals.values()
        if cel.status == "aktywne" and cel.identyfikator not in mierzone
    ]
    granica = today + timedelta(days=horyzont)
    bliskie = [cel for cel in brak if cel.termin and today <= cel.termin <= granica]
    out = [
        f"Cele bez miernika z terminem do {granica:%d.%m.%Y}: "
        f"{len(bliskie)} z {len(brak)} aktywnych"
    ]
    for cel in sorted(bliskie, key=lambda item: (item.termin or granica, item.identyfikator)):
        tresc = cel.tresc.rstrip(".").strip()
        out.append(f"  {cel.identyfikator}  {cel.termin:%d.%m.%Y}  {tresc[:56]}")
    if not bliskie:
        out.append("  (brak — żaden nie ma terminu w tym oknie)")
    dalsze = len(brak) - len(bliskie)
    out.append(f"  pozostałe {dalsze} mają termin dalej albo nieustalony")
    return out


def main() -> int:
    for path in (CELE, WAGA, AKTYWNOSCI):
        if not path.is_file():
            print(f"Brak pliku: {path}", file=sys.stderr)
            return 1
    today = date.today()
    goals = read_goals(CELE)
    blocks = [
        [f"Przegląd tygodniowy — {today:%d.%m.%Y}", "=" * 60],
        report_weight(goals, today),
        report_training(
            goals, today, "SPR-001", "treningi biegowe", BIEG, date(2026, 8, 6), 50
        ),
        report_training(
            goals, today, "SPR-002", "treningi siłowe", SILA, date(2026, 8, 6), 40
        ),
        report_abstinence(goals, today),
        report_data_quality(today),
        report_unmeasured(goals, today),
        [
            "-" * 60,
            "Wyjście przeglądu: maksymalnie 3 zadania w Todoist",
            "oraz jedno zdanie w status.md właściwego projektu.",
        ],
    ]
    print("\n\n".join("\n".join(block) for block in blocks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
