"""Process-worker example: uv run python examples/worker.py a.md b.md -o output.

This uses ordinary local jobs; a queue consumer can call print_job identically.
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from typoprint import render_files, write_pdf


def print_job(source: Path, destination: Path) -> str:
    result = render_files([source])
    return str(write_pdf(result, destination))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="+", type=Path)
    parser.add_argument("-o", "--output-dir", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be positive")
    destinations = [args.output_dir / f"{source.stem}.pdf" for source in args.sources]
    if len({path.resolve() for path in destinations}) != len(destinations):
        parser.error("Source stems must be unique within one output directory")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        jobs = [
            pool.submit(print_job, source, destination)
            for source, destination in zip(args.sources, destinations, strict=True)
        ]
        for job in jobs:
            print(job.result())
