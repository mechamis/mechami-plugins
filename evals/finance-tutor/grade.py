#!/usr/bin/env python3
"""Grade finance-tutor eval runs.

Most assertions in evals.json are mechanically checkable against the files the
skill produced plus the run's tool_log.md. Those are checked here. Assertions
that need judgment (tone, "stays educational", narrative vs. transcript copy)
return None and are left for a reviewer, so the script never guesses a pass.

Usage: python3 grade.py <iteration-dir>
Writes grading.json into each eval's with_skill/ directory.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

DISCLAIMER = ("**DISCLAIMER:** This information is for educational purposes only and "
              "should not be considered financial advice. For decisions involving your "
              "specific financial situation, please consult a licensed financial advisor.")

TS = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} (?:AM|PM) [A-Z]{2,5}"


class Run:
    """The files and logs one eval run produced."""

    def __init__(self, outputs: Path):
        self.outputs = outputs
        self.transcript = self._read("transcript.md")
        self.prompt_log = self._read("prompt_log.md")
        self.report = self._read("report.md")
        self.replies = self._read("chat_replies.md")
        self.tools = self._read("tool_log.md")

    def _read(self, name):
        p = self.outputs / name
        return p.read_text(encoding="utf-8") if p.exists() else None

    def reply(self, n):
        """Text of the nth turn's reply, from chat_replies.md."""
        if not self.replies:
            return None
        parts = re.split(r"^##\s+Turn\s+(\d+)\s+reply.*$", self.replies, flags=re.M)
        for i in range(1, len(parts) - 1, 2):
            if int(parts[i]) == n:
                return parts[i + 1].strip()
        return None

    def files_present(self):
        return sorted(p.name for p in self.outputs.iterdir() if p.is_file())


def ok(cond, evidence):
    return (bool(cond), evidence)


MANUAL = (None, "needs reviewer judgment")


# ---- shared checks -------------------------------------------------------

def has_transcript_header(r):
    if not r.transcript:
        return ok(False, "transcript.md missing")
    head = r.transcript.lstrip().split("\n\n")[0:2]
    starts = r.transcript.lstrip().startswith("# ")
    return ok(starts and DISCLAIMER in r.transcript,
              f"starts with title: {starts}; disclaimer present: {DISCLAIMER in (r.transcript or '')}")


def prompt_log_header(r):
    if not r.prompt_log:
        return ok(False, "prompt_log.md missing")
    starts = r.prompt_log.lstrip().startswith("# Prompt Log")
    m = re.search(rf"^## Session start: {TS}\s*$", r.prompt_log, re.M)
    return ok(starts and m, f"'# Prompt Log' first: {starts}; session heading: {m.group(0) if m else 'NOT FOUND'}")


def numbered_entries(text):
    return re.findall(r"^(\d+)\.\s+(.*)$", text or "", re.M)


def single_blank_separation(r):
    if not r.prompt_log:
        return ok(False, "prompt_log.md missing")
    doubled = re.findall(r"\n\n\n+", r.prompt_log.rstrip() + "\n")
    return ok(not doubled, f"{len(doubled)} run(s) of 2+ blank lines found")


def transcript_entry_shape(r):
    if not r.transcript:
        return ok(False, "transcript.md missing")
    qs = re.findall(r"^## Q: .+$", r.transcript, re.M)
    tss = re.findall(rf"^_{TS}_\s*$", r.transcript, re.M)
    refs = re.findall(r"^\*\*References\*\*\s*$", r.transcript, re.M)
    divs = re.findall(r"^---\s*$", r.transcript, re.M)
    good = len(qs) > 0 and len(tss) >= len(qs) and len(refs) >= len(qs) and len(divs) >= len(qs)
    return ok(good, f"{len(qs)} Q headings, {len(tss)} timestamps, {len(refs)} References, {len(divs)} dividers")


def date_cmd_used(r):
    if r.tools is None:
        return ok(False, "tool_log.md missing")
    return ok("date +" in r.tools, "found `date +` in tool log" if "date +" in r.tools else "no `date` call logged")


# Runs narrate their own logs ("No Write or Edit call touched transcript.md"),
# so a bare keyword match reports the disclaimer as a violation. Drop lines that
# are describing the absence of a call rather than recording one.
NEGATED = re.compile(r"(?i)\b(no|not|never|didn't|did not|without|rather than|instead of)\b")


def write_calls_on_protected(tools):
    """Lines that actually record a Write/Edit against a protected file.

    Case-sensitive on the tool name, because eval directory names such as
    `eval-9-guard-rejection-does-not-fall-back-to-write` appear inside every
    logged `cd` path and match case-insensitively. Lines that invoke append.py
    are skipped for the same reason: the target file name is on that line.
    """
    hits = []
    for line in (tools or "").splitlines():
        if "append.py" in line or NEGATED.search(line):
            continue
        if not re.search(r"\b(Write|Edit)\b", line):
            continue
        if not re.search(r"(transcript|prompt_log)\.md", line):
            continue
        hits.append(line.strip()[:120])
    return hits


def used_append_not_write(r):
    if r.tools is None:
        return ok(False, "tool_log.md missing")
    appended = len(re.findall(r"append\.py", r.tools))
    bad = write_calls_on_protected(r.tools)
    return ok(appended > 0 and not bad,
              f"{appended} append.py call(s); {len(bad)} Write/Edit on protected files: {bad[:3]}")


def quoted_heredoc(r):
    """Only real append commands count - runs also narrate 'None used bare <<EOF'."""
    if r.tools is None:
        return ok(False, "tool_log.md missing")
    cmds = [ln for ln in r.tools.splitlines() if "append.py" in ln]
    unquoted = [ln for ln in cmds if re.search(r"<<\s*[A-Z]", ln)]
    quoted = [ln for ln in cmds if re.search(r"<<\s*'", ln)]
    return ok(quoted and not unquoted,
              f"{len(quoted)} quoted / {len(unquoted)} unquoted, across {len(cmds)} append command(s)")


CONDITIONAL_DISCLAIMER = re.compile(
    r"^>?\s*\*\*Disclaimer:\*\*.*$", re.M | re.I)

# Ratios below these count as a violation. Coverage is the strict one: it is what
# catches an entry whose content was never shown. Precision is looser because a
# reply may legitimately carry a sentence of framing around the answer.
COVERAGE_MIN = 0.75
PRECISION_MIN = 0.50


def content_tokens(text):
    """Content words, with the noise that legitimately differs between the two sides removed.

    The transcript entry carries a heading, timestamp, and footnote markers the
    chat reply does not, and either side may wrap the same words in different
    emphasis characters. Words shorter than four characters are dropped so that
    articles and prepositions cannot prop up the overlap.
    """
    t = re.sub(r"```.*?```", " ", text or "", flags=re.S)
    t = re.sub(r"\(https?://[^)\s]+\)", " ", t)
    t = re.sub(r"\[\^\d+\]:?", " ", t)
    t = re.sub(r"[^\w\s]", " ", t)
    return Counter(w for w in t.lower().split() if len(w) >= 4)


def answer_body(text):
    """An entry or reply stripped to its answer: no references block, no disclaimers."""
    body = re.split(r"^\*\*References\*\*", text or "", flags=re.M)[0]
    body = body.replace(DISCLAIMER, " ")
    body = CONDITIONAL_DISCLAIMER.sub(" ", body)
    return re.sub(rf"^_{TS}_\s*$", " ", body, flags=re.M)


def transcript_entries(text):
    """(question, answer-body) per entry, in the order they were appended."""
    out = []
    for chunk in re.split(r"^## Q: ", text or "", flags=re.M)[1:]:
        question, _, rest = chunk.partition("\n")
        out.append((question.strip(), answer_body(rest).strip()))
    return out


def detail_parity(r, turn, entry=None):
    """The chat answer and the transcript entry it produced must be the same text.

    Deliberately not a length comparison. A reply that narrates progress
    ("appended that to the transcript") while composing the real answer straight
    into the heredoc can match a long entry on size while sharing almost none of
    its content - which is exactly the failure this exists to catch. Comparing
    content-word multisets catches it in both directions: coverage is the share of
    the stored entry that was actually shown to the user, precision the share of
    the chat text that was actually written to the file.

    `entry` is the 1-based index of the transcript entry this turn produced. When
    omitted, the best-matching entry is used - fine for single-question evals,
    but pass it explicitly in multi-turn runs so a turn cannot be scored against
    a different turn's entry.
    """
    reply = r.reply(turn)
    if not reply or not r.transcript:
        return ok(False, "missing chat_replies.md or transcript.md")
    entries = transcript_entries(r.transcript)
    if not entries:
        return ok(False, "no transcript entries")

    chat = content_tokens(answer_body(reply))
    if not chat:
        return ok(False, f"turn {turn} reply has no content words")

    def score(stored):
        shared = sum((chat & stored).values())
        return (shared / max(sum(stored.values()), 1),
                shared / max(sum(chat.values()), 1))

    if entry is not None:
        if entry > len(entries):
            return ok(False, f"turn {turn} expects transcript entry {entry}, only {len(entries)} present")
        question, body = entries[entry - 1]
        coverage, precision = score(content_tokens(body))
    else:
        scored = [(score(content_tokens(b)), q) for q, b in entries]
        (coverage, precision), question = max(scored, key=lambda s: s[0][0])

    return ok(coverage >= COVERAGE_MIN and precision >= PRECISION_MIN,
              f"coverage {coverage:.2f} / precision {precision:.2f} "
              f"vs entry '{question[:45]}' (chat {len(reply)} chars)")


def detail_parity_all(r, pairs):
    """One assertion covering every Q&A turn of a multi-turn run.

    `pairs` maps turn number to the transcript entry that turn produced.
    """
    results = [(t, detail_parity(r, t, e)) for t, e in pairs]
    return ok(all(passed for _, (passed, _) in results),
              "; ".join(f"turn {t} {'ok' if p else 'FAIL'}: {ev}" for t, (p, ev) in results))


def urls_in(text):
    return re.findall(r"\((https?://[^)\s]+)\)", text or "")


def no_escaped_dollars(r):
    """Backslash-escaping inside a quoted heredoc leaves the backslash in the file.

    Markdown renders `\\$7,500` as `$7,500`, so this survives a visual check while
    the stored text is wrong - and the file is append-only, so it stays wrong.
    """
    escaped = re.findall(r"\\\$[\d,]+", r.transcript or "")
    # Same root cause, opposite tell: avoiding "$" entirely rather than escaping it.
    spelled = re.findall(r"\b[\d][\d,]* dollars\b", r.transcript or "")
    return ok(not escaped and not spelled,
              f"{len(escaped)} escaped {sorted(set(escaped))[:3]}, "
              f"{len(spelled)} spelled-out {sorted(set(spelled))[:3]}")


# ---- per-eval assertion checks -------------------------------------------

def eval_0(r):
    t1 = r.reply(1) or ""
    # Verbatim, not merely disclaimer-shaped: SKILL.md carries a second
    # educational-purposes string as a banner describing the skill to whoever
    # reads its source, and a run that sends that one instead has not followed
    # the rule. A keyword match cannot tell the two apart.
    disclaimer_only = (DISCLAIMER in t1 and len(t1) < 900
                       and "treasury" not in t1.lower())
    entries = numbered_entries(r.prompt_log or "")
    return [
        ok(disclaimer_only,
           f"turn 1 reply is {len(t1)} chars, verbatim DISCLAIMER: {DISCLAIMER in t1}, "
           f"mentions Treasury: {'treasury' in t1.lower()}"),
        has_transcript_header(r),
        prompt_log_header(r),
        ok(len(entries) == 1 and not entries[0][1].startswith("/finance-tutor"),
           f"{len(entries)} numbered entries: {[e[1][:40] for e in entries]}"),
        transcript_entry_shape(r),
        date_cmd_used(r),
        used_append_not_write(r),
        detail_parity(r, 2),
    ]


def eval_1(r):
    t1 = r.reply(1) or ""
    first_chunk = t1[:800].lower()
    leads = "educational purposes only" in first_chunk
    dupes = t1.lower().count("educational purposes only")
    answered = "i bond" in t1.lower() or "i-bond" in t1.lower()
    return [
        ok(leads, f"disclaimer in first 800 chars: {leads}"),
        ok(dupes <= 1, f"'educational purposes only' appears {dupes} time(s)"),
        ok(answered and len(t1) > 600, f"reply {len(t1)} chars, discusses I-Bonds: {answered}"),
        ok(r.transcript and r.prompt_log, f"files: {r.files_present()}"),
        ok(bool(entries_1 := numbered_entries(r.prompt_log or "")) and
           not entries_1[0][1].lstrip().startswith("/finance-tutor"),
           f"entry 1: {entries_1[0][1][:60] if entries_1 else 'NONE'}"),
    ]


def eval_2(r):
    tr = r.transcript or ""
    literals = {s: s in tr for s in ["$10,000", "$1", "$2"]}
    orphan = re.findall(r"(?<!\$)(?<!\d),000\b", tr)
    return [
        ok(all(literals.values()), f"literal presence: {literals}"),
        ok(not orphan, f"{len(orphan)} orphaned ',000' occurrence(s)"),
        quoted_heredoc(r),
        MANUAL,
        used_append_not_write(r),
        no_escaped_dollars(r),
    ]


def eval_3(r):
    t2 = r.reply(2) or ""
    phrase = "not personalized financial advice"
    return [
        ok(t2.lstrip().startswith(">") and phrase in t2[:600],
           f"turn 2 starts with blockquote: {t2.lstrip()[:1]!r}; phrase in first 600: {phrase in t2[:600]}"),
        MANUAL,
        ok(phrase in (r.transcript or ""), f"conditional disclaimer in transcript: {phrase in (r.transcript or '')}"),
        ok(len(r.reply(1) or "") > 0 and "money market" not in (r.reply(1) or "").lower(),
           f"turn 1 reply is standalone disclaimer ({len(r.reply(1) or '')} chars)"),
        no_escaped_dollars(r),
    ]


def eval_4(r):
    tr = r.transcript or ""
    t2 = r.reply(2) or ""
    urls = urls_in(t2)
    deep = [u for u in urls if len(u.rstrip("/").split("/")) > 3]
    frac = len(deep) / len(urls) if urls else 0
    warns = t2.count("Unable to verify this specific URL")
    emojis = t2.count("⚠")
    return [
        ok("**References**" in t2 and len(urls) >= 3, f"{len(urls)} links in References"),
        ok(frac >= 0.8, f"{len(deep)}/{len(urls)} deep links ({frac:.0%}); shallow: {[u for u in urls if u not in deep]}"),
        ok(r.tools and re.search(r"(?i)websearch|webfetch", r.tools),
           "web verification logged" if r.tools and re.search(r"(?i)websearch|webfetch", r.tools) else "no web calls logged"),
        ok((emojis == 0 and warns == 0) or (emojis > 0 and warns == 1),
           f"{emojis} warning emoji, {warns} warning line"),
        ok(not (emojis == 0 and warns > 0), f"{emojis} emoji / {warns} warning line"),
        MANUAL,  # live-URL check runs separately
        ok(set(urls) == set(urls_in(tr)), f"chat URLs {len(set(urls))} vs transcript URLs {len(set(urls_in(tr)))}"),
    ]


def eval_5(r):
    entries = numbered_entries(r.prompt_log or "")
    nums = [int(n) for n, _ in entries]
    meta = any("transcript so far" in e[1].lower() for e in entries)
    sessions = re.findall(r"^## Session start:", r.prompt_log or "", re.M)
    qs = re.findall(r"^## Q: (.+)$", r.transcript or "", re.M)
    match_q = any("employer match" in q.lower() or "matching" in q.lower() for q in qs)
    return [
        ok(len(entries) == 3 and len(sessions) == 1,
           f"{len(entries)} entries under {len(sessions)} session heading(s): {[e[1][:35] for e in entries]}"),
        ok(meta, f"meta-request logged: {meta}"),
        single_blank_separation(r),
        ok(match_q, f"transcript Q headings: {qs}"),
        MANUAL,
        ok(nums == list(range(1, len(nums) + 1)), f"numbering: {nums}"),
    ]


def eval_6(r):
    rp = r.report or ""
    inline = [int(n) for n in re.findall(r"\[\^(\d+)\](?!:)", rp)]
    defs = [int(n) for n in re.findall(r"^\[\^(\d+)\]:", rp, re.M)]
    no_space = re.findall(r"\S(?<!\s)\[\^\d+\]", rp)
    entries = numbered_entries(r.prompt_log or "")
    return [
        ok(rp.lstrip().startswith("# ") and DISCLAIMER in rp,
           f"report exists: {bool(r.report)}; title+disclaimer ok: {rp.lstrip().startswith('# ') and DISCLAIMER in rp}"),
        ok(bool(inline), f"{len(inline)} inline [^N] markers"),
        ok(not no_space, f"{len(no_space)} marker(s) without a preceding space: {no_space[:3]}"),
        ok("## Footnotes" in rp and set(inline) <= set(defs),
           f"Footnotes section: {'## Footnotes' in rp}; inline {sorted(set(inline))} vs defined {sorted(set(defs))}"),
        ok(set(defs) <= set(inline), f"orphaned definitions: {sorted(set(defs) - set(inline))}"),
        MANUAL,
        ok(any("report" in e[1].lower() for e in entries), f"prompt log entries: {[e[1][:40] for e in entries]}"),
        MANUAL,
        no_escaped_dollars(r),
    ]


def eval_7(r):
    entries = numbered_entries(r.prompt_log or "")
    last = entries[-1][1].lower() if entries else ""
    log_text = (r.prompt_log or "").lower()
    tr = (r.transcript or "").lower()
    t3 = r.reply(3) or ""
    note = "stay loaded in context" in t3
    t4 = r.reply(4) or ""
    return [
        ok(note and ("transcript.md" in t3), f"closing note present: {note}; lists files: {'transcript.md' in t3}"),
        ok("end session" in last, f"last prompt_log entry: {entries[-1][1][:60] if entries else 'NONE'}"),
        ok("expense ratio" not in log_text and "fix the wording" not in log_text,
           f"post-session prompts leaked into log: {'expense ratio' in log_text or 'fix the wording' in log_text}"),
        ok("expense ratio" not in tr, f"expense-ratio entry in transcript: {'expense ratio' in tr}"),
        MANUAL,  # ordering of tool calls relative to turn 3
        ok(len(t4) > 300 and "expense ratio" in t4.lower(), f"turn 4 reply {len(t4)} chars, on topic: {'expense ratio' in t4.lower()}"),
        MANUAL,
    ]


SEED_DIR = Path(__file__).parent / "seed"


def eval_8(r):
    seed_t = (SEED_DIR / "transcript.md").read_text(encoding="utf-8")
    seed_p = (SEED_DIR / "prompt_log.md").read_text(encoding="utf-8")
    tr, pl = r.transcript or "", r.prompt_log or ""
    sessions = re.findall(rf"^## Session start: ({TS})\s*$", pl, re.M)
    tail = pl[len(seed_p):] if pl.startswith(seed_p) else pl
    tail_nums = [int(n) for n, _ in numbered_entries(tail)]
    new_q = re.findall(r"^## Q: .*(?:ETF|mutual fund).*$", tr, re.M | re.I)
    seed_end = tr.find(seed_t) + len(seed_t) if seed_t in tr else -1
    return [
        ok(tr.startswith(seed_t), f"seeded transcript intact at head: {tr.startswith(seed_t)}"),
        ok(pl.startswith(seed_p), f"seeded prompt log intact at head: {pl.startswith(seed_p)}"),
        ok(len(sessions) == 2, f"session headings: {sessions}"),
        ok(tail_nums[:1] == [1], f"new-session numbering: {tail_nums}"),
        # >= because appending directly onto the seed's trailing blank line puts
        # the new heading at exactly seed_end, which is correct, not a clobber.
        ok(bool(new_q) and seed_end != -1 and tr.find(new_q[0]) >= seed_end,
           f"new ETF entry at {tr.find(new_q[0]) if new_q else None}, seed ends at {seed_end}: {new_q}"),
        ok(tr.count(DISCLAIMER) == 1, f"DISCLAIMER appears {tr.count(DISCLAIMER)} time(s)"),
        ok(not re.search(r"---\n(?!\n)## Q:", tr) and not re.search(r"---\n\n\n## Q:", tr),
           "exactly one blank line between --- and next ## Q:"),
    ]


def eval_9(r):
    files = r.files_present()
    entries = numbered_entries(r.prompt_log or "")
    # Check the filesystem, not the log: the run is *supposed* to attempt the
    # rejected path, so ~/Desktop appearing in the log is expected. What matters
    # is that the guard stopped anything from landing there.
    stray = sorted(str(p) for p in Path.home().glob("Desktop/finance/*.md"))
    redirect = any("desktop" in e[1].lower() or "finance_notes" in e[1].lower() for e in entries)
    return [
        ok("finance_notes.md" not in files, f"files present: {files}"),
        ok(not stray, f"files under ~/Desktop/finance: {stray or 'none (directory absent)'}"),
        ok(not write_calls_on_protected(r.tools),
           f"Write/Edit on protected files: {write_calls_on_protected(r.tools) or 'none'}"),
        MANUAL,
        ok("bond ladder" in (r.transcript or "").lower(),
           f"bond ladder entry present: {'bond ladder' in (r.transcript or '').lower()}"),
        ok(redirect, f"redirect request logged: {redirect}; entries: {[e[1][:40] for e in entries]}"),
    ]


def eval_10(r):
    entries = numbered_entries(r.prompt_log or "")
    py_logged = any("python" in e[1].lower() for e in entries)
    t3 = r.reply(3) or ""
    has_fn = "def " in t3
    return [
        ok(py_logged, f"prompt log entries: {[e[1][:50] for e in entries]}"),
        ok(has_fn, f"turn 3 defines a function: {has_fn}"),
        MANUAL,
        ok("compound interest" in (r.transcript or "").lower(),
           f"compound interest entry intact: {'compound interest' in (r.transcript or '').lower()}"),
    ]


def eval_11(r):
    """Report regeneration: the second report must replace the first, not accrete onto it."""
    rp = r.report or ""
    heads = re.findall(r"^##+ .+$", rp, re.M)
    dupe_heads = sorted({h for h in heads if heads.count(h) > 1})

    inline = [int(n) for n in re.findall(r"\[\^(\d+)\](?!:)", rp)]
    defs = [int(n) for n in re.findall(r"^\[\^(\d+)\]:", rp, re.M)]
    dupe_defs = sorted({n for n in defs if defs.count(n) > 1})

    topics = {"traditional vs roth": r"roth", "rmd": r"required minimum|RMD",
              "backdoor/pro-rata": r"backdoor|pro-?rata", "inherited 10-year": r"inherit|10-year"}
    missing = [k for k, pat in topics.items() if not re.search(pat, rp, re.I)]

    entries = numbered_entries(r.prompt_log or "")
    gen = sum(1 for _, e in entries if "report" in e.lower())
    qs = re.findall(r"^## Q: ", r.transcript or "", re.M)
    appended_report = re.search(r"append\.py\s+\S*report\.md", r.tools or "")
    esc = re.findall(r"\\\$[\d,]+", rp)
    spelled = re.findall(r"\b[\d][\d,]* dollars\b", rp)

    return [
        ok(rp.lstrip().startswith("# ") and rp.count(DISCLAIMER) == 1,
           f"title lines: {len(re.findall(r'^# ', rp, re.M))}, DISCLAIMER count: {rp.count(DISCLAIMER)}"),
        ok(not dupe_heads, f"duplicated headings: {dupe_heads[:4] or 'none'}"),
        ok(not missing, f"topics missing from report: {missing or 'none'}"),
        ok(set(inline) == set(defs) and not dupe_defs,
           f"inline {sorted(set(inline))} vs defined {sorted(set(defs))}; duplicate defs: {dupe_defs or 'none'}"),
        ok(sorted(set(defs)) == list(range(1, len(set(defs)) + 1)),
           f"footnote numbers: {sorted(set(defs))}"),
        ok(set(defs) <= set(inline), f"orphaned definitions: {sorted(set(defs) - set(inline)) or 'none'}"),
        ok(not appended_report,
           f"append.py on report.md: {appended_report.group(0) if appended_report else 'never (correct)'}"),
        ok(gen >= 2, f"{gen} report-related prompt_log entries: {[e[1][:40] for e in entries]}"),
        ok(len(qs) == 4, f"{len(qs)} transcript Q&A entries"),
        ok(not esc and not spelled, f"{len(esc)} escaped, {len(spelled)} spelled-out"),
        # Turns 1, 4 and 7 are the invocation and the two report requests - they
        # produce no transcript entry, so only the four question turns are paired.
        detail_parity_all(r, [(2, 1), (3, 2), (5, 3), (6, 4)]),
    ]


CHECKS = {0: eval_0, 1: eval_1, 2: eval_2, 3: eval_3, 4: eval_4, 5: eval_5,
          6: eval_6, 7: eval_7, 8: eval_8, 9: eval_9, 10: eval_10, 11: eval_11}


def main():
    iteration = Path(sys.argv[1]).resolve()
    summary = []
    for d in sorted(iteration.glob("eval-*"), key=lambda p: int(p.name.split("-")[1])):
        meta = json.loads((d / "eval_metadata.json").read_text())
        run_dir = d / "with_skill"
        outputs = run_dir / "outputs"
        # chat_replies.md is written last, so its absence means the run is still
        # in flight - grading it now would score a partial run as a failure.
        if not (outputs / "chat_replies.md").exists():
            print(f"skipping {d.name}: run incomplete")
            continue
        r = Run(outputs)
        results = CHECKS[meta["eval_id"]](r)
        expectations = []
        for text, (passed, evidence) in zip(meta["assertions"], results):
            expectations.append({"text": text, "passed": passed, "evidence": evidence})
        auto = [e for e in expectations if e["passed"] is not None]
        passed = sum(1 for e in auto if e["passed"])
        grading = {
            "eval_id": meta["eval_id"],
            "eval_name": meta["eval_name"],
            "expectations": expectations,
            "auto_graded": len(auto),
            "auto_passed": passed,
            "manual_pending": len(expectations) - len(auto),
        }
        (run_dir / "grading.json").write_text(json.dumps(grading, indent=2) + "\n")
        summary.append((meta["eval_id"], meta["eval_name"], passed, len(auto), len(expectations) - len(auto)))

    print(f"{'id':>3}  {'eval':<52} {'auto':>9}  manual")
    for eid, name, p, n, m in summary:
        flag = "" if p == n else "  <-- FAILURES"
        print(f"{eid:>3}  {name:<52} {p:>4}/{n:<4}  {m:>3}{flag}")
    tot_p = sum(s[2] for s in summary)
    tot_n = sum(s[3] for s in summary)
    print(f"\nauto-graded pass rate: {tot_p}/{tot_n} ({tot_p / tot_n:.0%})" if tot_n else "no runs graded")


if __name__ == "__main__":
    main()
