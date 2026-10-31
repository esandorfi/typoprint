"""Run the delivered local HTTP and process-worker examples end to end."""

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.request import Request, urlopen

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class ExampleTests(unittest.TestCase):
    def test_local_http_example_returns_pdf_and_generic_render_errors(self):
        process = subprocess.Popen(
            [sys.executable, str(EXAMPLES / "api.py"), "--port", "0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            assert process.stdout is not None
            address = process.stdout.readline().strip().removeprefix("POST JSON to ")
            self.assertTrue(address.startswith("http://127.0.0.1:"), address)
            request = Request(
                address,
                data=json.dumps({"markdown": "# Fictional API"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=15) as response:
                self.assertEqual(response.headers.get_content_type(), "application/pdf")
                self.assertTrue(response.read().startswith(b"%PDF-"))
            request.data = json.dumps(
                {"markdown": "```mermaid\nPRIVATE_INVALID_DIAGRAM\n```"}
            ).encode()
            with self.assertRaises(HTTPError) as error:
                urlopen(request, timeout=15)
            self.assertEqual(error.exception.code, 422)
            self.assertNotIn(b"PRIVATE_INVALID_DIAGRAM", error.exception.read())
        finally:
            process.terminate()
            process.communicate(timeout=15)

    def test_process_workers_write_independent_pdfs(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = [root / "first.md", root / "second.md"]
            for source in sources:
                source.write_text(
                    f"# {source.stem}\n\nFictional job.", encoding="utf-8"
                )
            before = [source.read_bytes() for source in sources]
            result = subprocess.run(
                [
                    sys.executable,
                    str(EXAMPLES / "worker.py"),
                    *map(str, sources),
                    "--output-dir",
                    str(root / "output"),
                    "--workers",
                    "2",
                ],
                capture_output=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            for source in sources:
                self.assertTrue(
                    (root / "output" / f"{source.stem}.pdf")
                    .read_bytes()
                    .startswith(b"%PDF-")
                )
            self.assertEqual(before, [source.read_bytes() for source in sources])
