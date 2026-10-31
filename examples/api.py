"""Local HTTP example: uv run python examples/api.py --port 8766.

POST JSON {"markdown": "# Hello"} to /pdf. Production applications own
authentication, request limits, deadlines, and deployment policy.
"""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from pydantic import BaseModel, ConfigDict, ValidationError

from typoprint import TypoprintError, render


class PrintRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    markdown: str


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/pdf":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400)
            return
        if not 0 < length <= 1_048_576:
            self.send_error(413)
            return
        try:
            request = PrintRequest.model_validate_json(self.rfile.read(length))
            result = render(request.markdown)
        except (ValidationError, TypoprintError):
            self.send_error(422, "The document could not be rendered")
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Length", str(len(result.content)))
        self.send_header("Content-Disposition", 'attachment; filename="document.pdf"')
        self.end_headers()
        self.wfile.write(result.content)

    def log_message(self, format: str, *args: object) -> None:
        # Do not log document bodies, request paths, or compiler diagnostics.
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
        print(f"POST JSON to http://127.0.0.1:{server.server_port}/pdf", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
