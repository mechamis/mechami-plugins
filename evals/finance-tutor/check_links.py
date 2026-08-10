#!/usr/bin/env python3
"""Check that every URL in a run's transcript.md actually resolves.

The skill's whole reference policy rests on links pointing at real pages, so a
200 check is the one assertion that cannot be graded by reading the text.

Usage: python3 check_links.py <path/to/transcript.md>
"""
import re
import sys
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"


def check(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, ""
    except urllib.error.HTTPError as e:
        return e.code, e.reason
    except Exception as e:
        return None, str(e)


def main():
    text = open(sys.argv[1], encoding="utf-8").read()
    urls = sorted(set(re.findall(r"\((https?://[^)\s]+)\)", text)))
    bad = 0
    for u in urls:
        status, note = check(u)
        good = status == 200
        bad += not good
        print(f"{'OK ' if good else 'BAD'}  {status or 'ERR':<5} {u}{'  ' + note if note else ''}")
    print(f"\n{len(urls) - bad}/{len(urls)} resolved")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
