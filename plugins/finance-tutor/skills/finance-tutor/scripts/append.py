#!/usr/bin/env python3
"""Append text from stdin to a file (append-only).

Generic helper: it knows nothing about this skill's formats. It only ever opens
the target in append mode ("a"), which physically cannot truncate or rewrite
existing content — so prior entries are safe no matter how large the file grows.
The caller supplies the fully formatted text on stdin.

Two guards keep writes where they belong: the file name must be one of
`allowed_file_names`, and the target must resolve to a location inside the
current working directory. Both failures exit non-zero with a message on stderr.

Usage:
    python3 append.py <target_file> [--newline] < text
    python3 append.py transcript.md <<'EOF'
    ## Q: ...
    ---
    EOF
"""
import argparse
import sys
from pathlib import Path

allowed_file_names = ['transcript.md', 'prompt_log.md', 'report.md']


def fail(message):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Append text read from stdin to a file (append-only)."
    )
    parser.add_argument("target", help="File to append to")
    parser.add_argument(
        "--newline",
        action="store_true",
        help="Ensure the appended text ends with a trailing newline",
    )
    args = parser.parse_args()

    text = sys.stdin.read()
    if args.newline and not text.endswith("\n"):
        text += "\n"

    working_dir = Path.cwd().resolve()
    target = Path(args.target).resolve()

    if target.name not in allowed_file_names:
        fail(
            f"'{target.name}' is not an allowed append target "
            f"(allowed: {', '.join(allowed_file_names)})"
        )

    if not target.is_relative_to(working_dir):
        fail(
            f"'{args.target}' resolves to {target}, outside the working "
            f"directory {working_dir}"
        )

    target.parent.mkdir(parents=True, exist_ok=True)

    # "a" = append-only: writes always go to the end, existing bytes are never touched.
    with open(target, "a", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    main()
