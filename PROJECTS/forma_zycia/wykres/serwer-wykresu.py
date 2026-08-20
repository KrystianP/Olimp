"""Lokalnie udostępnia wyłącznie wykres Forma Życia i dane wagi."""

from __future__ import annotations

import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


PROJECT_DIRECTORY = Path(__file__).resolve().parent
REPOSITORY_ROOT = PROJECT_DIRECTORY.parents[2]
CHART_FILE = PROJECT_DIRECTORY / "wykres-tempo-redukcji.html"
WEIGHT_DATA = REPOSITORY_ROOT / "DATA" / "waga.csv"

ROUTES = {
    "/": (CHART_FILE, "text/html; charset=utf-8"),
    "/wykres-tempo-redukcji.html": (CHART_FILE, "text/html; charset=utf-8"),
    "/data/waga.csv": (WEIGHT_DATA, "text/csv; charset=utf-8"),
}


class ChartRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        route = urlsplit(self.path).path
        resource = ROUTES.get(route)
        if resource is None:
            self.send_error(404)
            return

        path, content_type = resource
        try:
            content = path.read_bytes()
        except OSError:
            self.send_error(500)
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), ChartRequestHandler)
    actual_port = server.server_address[1]
    print(
        f"Wykres jest dostępny pod adresem http://127.0.0.1:{actual_port}/",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
