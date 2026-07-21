---
name: finance-tutor
description: FOR EDUCATIONAL PURPOSES ONLY — not financial advice. This skill sets up a finance Q&A learning workflow. The user asks finance questions, Claude answers them educationally with references, and every exchange is appended to a persistent transcript. A compiled report with footnotes can be generated at any time.
disable-model-invocation: true
---

# Finance Tutor

## Purpose

**FOR EDUCATIONAL PURPOSES ONLY. This skill does not provide personalized financial advice. All answers are intended for learning and general understanding only. For decisions involving your specific financial situation, consult a licensed financial advisor.**

This skill sets up a finance Q&A learning workflow. The user asks finance questions, Claude answers them educationally with authoritative references, and every exchange is appended to a persistent transcript. A compiled report with footnotes can be generated at any time.

**File location:** Create and maintain all files (`transcript.md`, `prompt_log.md`, `report.md`) in the current working directory.

**References (applies to every finance answer):** End each finance answer with a `**References**` section linking to authoritative sources relevant to the topics covered (e.g., TreasuryDirect, IRS, SEC, FDIC, Federal Reserve, Investopedia, Vanguard). Every finance answer must include this section.

**Specific pages are the goal.** A reference should point at the page that actually documents the claim (e.g., the IRS topic page, the TreasuryDirect product page, the SEC rule text) — not at a homepage the reader has to search from. Root-domain links are a last resort, not a safe default.

Apply these three options **in order**. Do not skip ahead to a later option because it feels safer:

1. **Verify, then link specifically (preferred).** Use web search/fetch to confirm the deep URL resolves, then include it. This is the default path — run the searches rather than avoiding them. Verifying several links in one batch of parallel calls keeps this cheap.
2. **Link specifically with a warning.** If verification is unavailable or the fetch fails, still provide the specific URL, place a warning emoji ⚠️ to the right of the link, and add this single line of warning text after the References/Footnotes:

   > ⚠️ *Unable to verify this specific URL using web search/fetch at the time this content was generated*

3. **Fall back to a root or well-known section domain** (e.g., `https://www.irs.gov`, `https://www.treasurydirect.gov`, `https://www.sec.gov`, `https://investor.gov`) **only when 1 and 2 both fail** — that is, when no specific page plausibly exists for the topic, or you cannot name a specific URL without guessing at its path.

Never fabricate a plausible-looking URL. Option 2 covers *unverified* links you have real grounds to believe in (a page you know exists, whose exact path you could not confirm); it does not license inventing paths. When you genuinely have no candidate URL, use option 3.

Silently downgrading to option 3 defeats the ⚠️ convention: its purpose is to show the reader *which* links are uncertain, so a homepage with no signal is worse than a specific link that is honestly flagged.

**Append-only files:** `transcript.md` and `prompt_log.md` are append-only — new entries are *added to the end*, and existing entries are never rewritten. This matters because the value of these files is fidelity: a full-file `Write` would force you to reproduce all prior content from context on every update, which risks silently dropping or altering earlier entries and gets more expensive as the file grows. Appending sidesteps that entirely.

Use the bundled helper `scripts/append.py` to append. It reads the text to append from stdin and opens the target in append mode, so it structurally cannot truncate or overwrite prior content:

```bash
python scripts/append.py transcript.md <<'EOF'
## Q: <question>

_<timestamp>_

<answer>

**References**

- [<source name>](<url>)

---

EOF
```

Pipe the fully formatted entry (matching the templates below) on stdin. Pass `--newline` if you want to guarantee the file ends with a trailing newline. The script creates the file and any parent directories if they don't exist yet, so a separate "create the file first" step isn't needed.

To avoid repeated approval prompts for the append command, the user can approve it once: when the permission prompt first appears, choosing the "don't ask again" option lets Claude Code record a matching allow rule automatically. That is more reliable than hand-writing a permission rule, because the script's real invocation path includes the plugin version and can change between releases. Do not append with a full-file `Write`; use `Write` only for `report.md`, which is regenerated whole each time.

## The Rules

- Answer finance questions clearly and educationally.
- Do not provide personalized financial advice; frame all answers as educational.
- If the user's question sounds like a request for personalized financial advice (e.g., "should I...", "what should I do with...", "is it a good idea for me to..."), begin the response with the following disclaimer before answering educationally:

  > **Disclaimer:** This is an educational answer, not personalized financial advice. For decisions involving your specific financial situation, please consult a licensed financial advisor.

- Claude will automatically create `transcript.md` on the first question if it does not already exist.
- Each answer will include a References section (see above) and be appended to `transcript.md`.
- When prompted to generate a report, create a detailed report that compiles this information, with footnotes throughout the content.
- Append **every user message** during the session to `prompt_log.md` — including clarification questions, follow-ups, and meta-requests (e.g., "update the transcript"). Create the file if it does not exist.
- Chat responses should match the level of detail written to `transcript.md`, not a condensed summary. 
  - Having details in both the response and `transcript.md` allows a user to review what is being written to the transcript file without checking manually, and helps if they wish to ask follow up questions.
- Continue to follow these rules until the user prompts you to end the session. Examples: "end session", "end tutorial"

## Workflow Summary

1. User sends any message (finance question, clarification, follow-up, or meta-request)
2. Prompt appended to `prompt_log.md`
3. If a finance question: Claude answers with references, Q&A pair appended to `transcript.md`
4. If a clarification or follow-up: Claude answers and appends the exchange to `transcript.md` with any relevant references
5. (Optionally) Claude generates `report.md` with footnotes

## File Roles

| File | Role |
|---|---|
| `transcript.md` | Append-only log of every Q&A exchange |
| `prompt_log.md` | Append-only log of every prompt |
| `report.md` | Generated on demand — compiled narrative with inline footnotes and a full reference list |

## Conventions

- **Transcript format:** Each entry uses `## Q: <question>` as a heading, immediately followed by a `_<timestamp>_` line, then the answer, a `**References**` section with links, and a `---` divider. End the entry with a blank line after the divider so that when the next entry is appended there is a blank line between the `---` and the following `## Q:` heading — this keeps entries cleanly separated and avoids the divider being parsed as a heading underline. The timestamp uses the same `YYYY-MM-DD hh:mm AM/PM TZ` format as the Prompt Log, obtained via `date +"%Y-%m-%d %I:%M %p %Z"`. Template (note the trailing blank line):

  ```
  ## Q: <question>

  _<timestamp>_

  <answer>

  **References**

  - [<source name>](<url>)

  ---

  ```
- **Report format:** Narrative sections with `[^N]` inline footnotes and a `## Footnotes` section at the end mapping each number to a URL.
  - Include a space between the text and the footnote marker (e.g. `... Treasury bonds. [^1]`).
- **Disclaimer header:** The following disclaimer must appear at the top of both `transcript.md` and `report.md`, immediately after the `# <Title>` heading:

  ```
  **DISCLAIMER:** This information is for educational purposes only and should not be considered financial advice. For decisions involving your specific financial situation, please consult a licensed financial advisor.
  ```

## Prompt Log format

Session start should have a timestamp in `YYYY-MM-DD hh:mm AM/PM TZ` format, obtained via `date +"%Y-%m-%d %I:%M %p %Z"` (uses local time with local timezone abbreviation, e.g. EDT).

Entries must be separated by a single blank line — no double-spacing between entries.

### Example Prompt Log

```
# Prompt Log

## Session start: 2026-04-29 1:47 PM EDT

1. [first prompt]

2. [second prompt]

## Session start: 2026-04-29 4:03 PM EDT

1. [first prompt]

2. [second prompt]

## Session start: 2026-04-30 10:15 AM EDT

1. [first prompt]

2. [second prompt]

```

## Transcript format example

```
# Finance Q&A Transcript

**DISCLAIMER:** This information is for educational purposes only and should not be considered financial advice. For decisions involving your specific financial situation, please consult a licensed financial advisor.

## Q: What is the difference between a Treasury bill and a Treasury bond?

_2026-04-29 1:47 PM EDT_

Treasury bills (T-bills) are short-term securities that mature in one year or less and are sold at a discount to face value. Treasury bonds are long-term securities with maturities of 20 or 30 years that pay interest every six months.

**References**

- [TreasuryDirect — Treasury Bills](https://www.treasurydirect.gov/marketable-securities/treasury-bills/)
- [TreasuryDirect — Treasury Bonds](https://www.treasurydirect.gov/marketable-securities/treasury-bonds/)

---

## Q: How is interest on Treasury securities taxed?

_2026-04-29 1:52 PM EDT_

Interest income from Treasury securities is subject to federal income tax but is exempt from state and local income taxes.

**References**

- [IRS — Topic No. 403, Interest Received](https://www.irs.gov/taxtopics/tc403)

---
```
