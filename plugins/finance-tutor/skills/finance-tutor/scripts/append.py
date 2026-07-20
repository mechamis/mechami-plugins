#!/usr/bin/env python3
"""Append text from stdin to a file (append-only).

Generic helper: it knows nothing about this skill's formats. It only ever opens
the target in append mode ("a"), which physically cannot truncate or rewrite
existing content — so prior entries are safe no matter how large the file grows.
The caller supplies the fully formatted text on stdin.

Usage:
    python append.py <target_file> [--newline] < text
    python append.py transcript.md <<'EOF'
    ## Q: ...
    ---
    EOF
"""
import argparse
import os
import sys


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

    parent = os.path.dirname(os.path.abspath(args.target))
    os.makedirs(parent, exist_ok=True)

    # "a" = append-only: writes always go to the end, existing bytes are never touched.
    with open(args.target, "a", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    main()
