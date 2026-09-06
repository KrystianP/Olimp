"""Testy wyboru zakresu synchronizacji w workflow GitHub Actions.

Testy uruchamiają prawdziwy blok bash wyjęty z pliku workflow, a nie jego
kopię. Dzięki temu rozjechanie się listy wpisów crona z instrukcją `case`
kończy się czerwonym testem, a nie biegiem, który po cichu nic nie pobiera.

Przesunięcie strefy pochodzi z `date +%z`, więc test podstawia własne `date`
na początku `PATH`. Pozwala to sprawdzić czas letni i zimowy niezależnie od
tego, kiedy test jest uruchamiany.

Statyczne sprawdzenia umowy między skryptem a workflow — liczba wpisów crona,
pokrycie każdego z nich w `case` i brak porównania zegara z rozkładem — należą
do `test_synchronizuj_garmin.py::WorkflowGarminTest`. Tutaj są wyłącznie testy,
które ten blok naprawdę wykonują.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

WORKFLOW = (
    Path(__file__).resolve().parents[3] / ".github" / "workflows" / "synchronizuj-garmin.yml"
)
SUMMER = "+0200"
WINTER = "+0100"


def read_workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def declared_crons(text: str) -> list[str]:
    """Wpisy crona zadeklarowane w wyzwalaczu `schedule`."""
    return re.findall(r'^\s*- cron:\s*"([^"]+)"', text, flags=re.MULTILINE)


def scope_script(text: str) -> str:
    """Blok `run` kroku wybierającego zakres, bez wcięcia z YAML-a."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if "id: scope" in line)
    run_at = next(i for i in range(start, len(lines)) if lines[i].strip() == "run: |")
    indent = len(lines[run_at]) - len(lines[run_at].lstrip()) + 2
    body: list[str] = []
    for line in lines[run_at + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) < indent:
            break
        body.append(line[indent:] if len(line) >= indent else line)
    return "\n".join(body)


def case_labels(script: str) -> set[tuple[str, str]]:
    """Pary (przesunięcie, cron) obsłużone w instrukcji `case`."""
    return {
        (offset, cron)
        for offset, cron in re.findall(r'"([+-]\d{4})\|([^"]+)"\)', script)
    }


class ScopeRunner:
    """Uruchamia blok bash z podstawionym `date` i przechwyconym GITHUB_OUTPUT."""

    def __init__(self, script: str) -> None:
        self.script = script

    def run(self, cron: str, offset: str, event: str = "schedule") -> dict[str, str]:
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            shim = root / "bin"
            shim.mkdir()
            date_shim = shim / "date"
            # Podstawiamy tylko `date +%z`; pozostałe wywołania trafiają do
            # systemowego `date`, żeby test nie zmieniał reszty zachowania.
            date_shim.write_text(
                '#!/bin/sh\n'
                'if [ "$1" = "+%z" ]; then printf "%s\\n" "' + offset + '"; exit 0; fi\n'
                'exec /bin/date "$@"\n',
                encoding="utf-8",
            )
            date_shim.chmod(0o755)
            output = root / "github_output"
            output.touch()
            environment = dict(os.environ)
            environment.update(
                {
                    "PATH": f"{shim}:{environment['PATH']}",
                    "EVENT_NAME": event,
                    "SCHEDULE": cron,
                    "GITHUB_OUTPUT": str(output),
                    "REQUESTED_MODE": "",
                    "REQUESTED_ACTIVITY_DAYS": "",
                    "REQUESTED_WEIGHT_DAYS": "",
                }
            )
            completed = subprocess.run(
                ["bash", "-e", "-c", self.script],
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
            )
            result = dict(
                line.split("=", 1)
                for line in output.read_text(encoding="utf-8").splitlines()
                if "=" in line
            )
            result["_returncode"] = str(completed.returncode)
            result["_stdout"] = completed.stdout
            result["_stderr"] = completed.stderr
            return result


class HarmonogramTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = read_workflow()
        cls.crons = declared_crons(cls.text)
        cls.script = scope_script(cls.text)
        cls.runner = ScopeRunner(cls.script)

    def test_case_nie_ma_wpisow_bez_crona(self) -> None:
        """Etykieta bez wyzwalacza to martwy kod sugerujący nieistniejący bieg."""
        handled = {cron for _, cron in case_labels(self.script)}
        self.assertEqual(handled - set(self.crons), set())

    def test_kazdy_cron_uruchamia_sie_dokladnie_w_jednej_strefie(self) -> None:
        for cron in self.crons:
            with self.subTest(cron=cron):
                summer = self.runner.run(cron, SUMMER)
                winter = self.runner.run(cron, WINTER)
                uruchomione = [
                    result for result in (summer, winter) if result.get("run") == "true"
                ]
                self.assertEqual(
                    len(uruchomione),
                    1,
                    f"cron '{cron}' powinien działać w dokładnie jednej strefie",
                )

    def test_pominiecie_konczy_sie_sukcesem_i_wyjasnieniem(self) -> None:
        """Pominięcie drugiej połowy pary jest poprawne, ale musi być widoczne."""
        cron = "30 4 * * *"  # 06:30 czasu letniego
        result = self.runner.run(cron, WINTER)
        self.assertEqual(result["_returncode"], "0")
        self.assertEqual(result.get("run"), "false")
        self.assertIn("Pominięto", result["_stdout"])

    def test_rozklad_trybow_zgadza_sie_z_zalozeniem(self) -> None:
        """Cztery synchronizacje aktywności i dwie wagi na dobę."""
        tryby: list[str] = []
        for cron in self.crons:
            for offset in (SUMMER, WINTER):
                result = self.runner.run(cron, offset)
                if result.get("run") == "true":
                    tryby.append(result["mode"])
        self.assertEqual(tryby.count("activities"), 8)
        self.assertEqual(tryby.count("weight"), 4)

    def test_bieg_z_harmonogramu_ma_stale_okno_dni(self) -> None:
        result = self.runner.run("0 8 * * *", SUMMER)
        self.assertEqual(result["mode"], "weight")
        self.assertEqual(result["activity_days"], "14")
        self.assertEqual(result["weight_days"], "14")

    def test_nieznane_przesuniecie_konczy_bieg_bledem(self) -> None:
        """Cicha zmiana reguł strefy nie może przejść jako poprawny bieg."""
        result = self.runner.run("0 8 * * *", "+0300")
        self.assertEqual(result["_returncode"], "2")
        self.assertIn("przesunięcie", result["_stderr"])

    def test_reczne_uruchomienie_ignoruje_harmonogram(self) -> None:
        script = self.script
        runner = ScopeRunner(script)
        with tempfile.TemporaryDirectory():
            environment_result = runner.run("", SUMMER, event="workflow_dispatch")
        # Bez podanych wejść ręczne uruchomienie musi odmówić, a nie zgadywać.
        self.assertEqual(environment_result["_returncode"], "2")


if __name__ == "__main__":
    unittest.main()
