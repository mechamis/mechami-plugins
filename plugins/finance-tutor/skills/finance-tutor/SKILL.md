---
name: finance-tutor
description: FOR EDUCATIONAL PURPOSES ONLY — not financial advice. This skill sets up a finance Q&A learning workflow. The user asks finance questions, Claude answers them educationally with references, and every exchange is appended to a persistent transcript. A compiled report with footnotes can be generated at any time.
disable-model-invocation: true
---

# Finance Tutor

## Purpose

**FOR EDUCATIONAL PURPOSES ONLY. This skill does not provide personalized financial advice. All answers are intended for learning and general understanding only. For decisions involving your specific financial situation, consult a licensed financial advisor.**

This skill sets up a finance Q&A learning workflow. The user asks finance questions, Claude answers them educationally with authoritative references, and every exchange is appended to a persistent transcript. A compiled report with footnotes can be generated at any time.

**File location:** Create and maintain all files (`transcript.md`, `prompt_log.md`, `report.md`) in the current working directory. For the two append-only files this is not just a convention — `scripts/append.py` enforces it, and rejects anything else (see "Where the script will write" below).

**References (applies to every finance answer):** End each finance answer with a `**References**` section linking to authoritative sources relevant to the topics covered (e.g., TreasuryDirect, IRS, SEC, FDIC, Federal Reserve, Investopedia, Vanguard). Every finance answer must include this section.

**Specific pages are the goal.** A reference should point at the page that actually documents the claim (e.g., the IRS topic page, the TreasuryDirect product page, the SEC rule text) — not at a homepage the reader has to search from. Root-domain links are a last resort, not a safe default.

Apply these three options **in order**. Do not skip ahead to a later option because it feels safer:

1. **Verify, then link specifically (preferred).** Use web search/fetch to confirm the deep URL resolves, then include it. This is the default path — run the searches rather than avoiding them. Verifying several links in one batch of parallel calls keeps this cheap.
2. **Link specifically with a warning.** If verification is unavailable or the fetch fails, still provide the specific URL, place a warning emoji ⚠️ to the right of the link, and add this single line of warning text after the References/Footnotes:

   > ⚠️ *Unable to verify this specific URL using web search/fetch at the time this content was generated*

   Use the ⚠️ character itself, not a text stand-in like `[WARN]`. The marker's whole job is to catch the reader's eye as they scan a list of links, which a bracketed word does not do.

   Before settling for a warning, distinguish the two ways verification fails, because they call for different responses:

   - **The page is gone (404).** The link is simply wrong. Search for the page that actually documents the claim and cite that instead — a verified correct link beats a flagged broken one, and shipping a known-404 under a warning misuses the convention.
   - **The fetch was refused (403, timeout, blocked domain).** The page likely exists and you just cannot reach it. This is what option 2 is for: keep the specific URL and flag it. A domain-scoped search that returns the same page and title is reasonable corroboration.

3. **Fall back to a root or well-known section domain** (e.g., `https://www.irs.gov`, `https://www.treasurydirect.gov`, `https://www.sec.gov`, `https://investor.gov`) **only when 1 and 2 both fail** — that is, when no specific page plausibly exists for the topic, or you cannot name a specific URL without guessing at its path.

Never fabricate a plausible-looking URL. Option 2 covers *unverified* links you have real grounds to believe in (a page you know exists, whose exact path you could not confirm); it does not license inventing paths. When you genuinely have no candidate URL, use option 3.

Silently downgrading to option 3 defeats the ⚠️ convention: its purpose is to show the reader *which* links are uncertain, so a homepage with no signal is worse than a specific link that is honestly flagged.

**Append-only files:** `transcript.md` and `prompt_log.md` are append-only — new entries are *added to the end*, and existing entries are never rewritten. This matters because the value of these files is fidelity: a full-file `Write` would force you to reproduce all prior content from context on every update, which risks silently dropping or altering earlier entries and gets more expensive as the file grows. Appending sidesteps that entirely.

Use the bundled helper `scripts/append.py` to append. It reads the text to append from stdin and opens the target in append mode, so it structurally cannot truncate or overwrite prior content:

```bash
python3 scripts/append.py transcript.md <<'EOF'
## Q: <question>

_<timestamp>_

<answer>

**References**

- [<source name>](<url>)

---

EOF
```

**Quote the heredoc delimiter.** Always write `<<'EOF'`, never `<<EOF`. The quotes stop the shell from expanding the body before the script sees it. Unquoted, `$10,000` becomes `,000`, `$1` and `$2` vanish entirely, and backticks execute as shell commands — and dollar amounts appear in nearly every finance answer. The command still exits `0`, so nothing signals the damage, and because the write is append-only the corrupted entry cannot be rewritten afterward.

**Once the delimiter is quoted, dollar signs are completely safe.** This is the part worth internalizing, because the warning above tends to breed defensive habits that quietly damage the transcript in their own right. All three of these are mistakes:

- `\$7,500` — the quotes already prevented expansion, so the backslash is passed through literally and the file stores `\$7,500`. Markdown renders that as `$7,500`, so it survives a visual check while the stored text is wrong.
- `7,500 dollars` — avoiding the character altogether. The transcript is meant to read like the answer you gave, and spelled-out amounts are worse writing.
- Switching to `Write` because the heredoc feels risky — that discards the append-only guarantee entirely.

With `<<'EOF'` in place, write the body exactly as it should appear in the finished file: plain `$7,500`, ordinary backticks, no escaping and no rephrasing. Quote the delimiter *or* escape the content, never both — and quoting the delimiter is the one to choose.

**Interpreter name is platform-specific.** The example above uses `python3`, which is correct on macOS and Linux. Windows has no `python3` — use `python`, or `py -3` if that is unavailable. Do not assume `python3` and retry blindly on failure: Windows registers an App Execution Alias for `python3.exe` that opens the Microsoft Store rather than reporting a missing command, so the failure can look like nothing happening at all. Pick the spelling that matches the platform you are running on.

Pipe the fully formatted entry (matching the templates below) on stdin. Pass `--newline` if you want to guarantee the file ends with a trailing newline. The script creates the file and any parent directories if they don't exist yet, so a separate "create the file first" step isn't needed.

**Where the script will write.** Two guards constrain the target, and both must pass or nothing is written:

1. The file name must be exactly `transcript.md` or `prompt_log.md`. Matching is case-sensitive. `report.md` is deliberately not accepted — it is regenerated whole each time, and a script that can only append would duplicate the previous report rather than replace it, so the rejection turns a silent content bug into an immediate error.
2. The target must resolve to a location inside the current working directory. Symlinks are followed before the check, so a link is judged by where it actually lands, not where it sits — a `transcript.md` symlinked to somewhere outside the working directory is rejected.

Either failure exits non-zero and prints a line beginning with `error:` on stderr explaining which guard tripped.

Treat that error as a signal that the *target* was wrong, and fix the path. Do not route around it by falling back to a full-file `Write`, by `cd`-ing elsewhere first, or by retrying under a different name — those defeat the append-only guarantee described above, which is the entire reason this helper exists.

To avoid repeated approval prompts for the append command, the user can approve it once: when the permission prompt first appears, choosing the "don't ask again" option lets Claude Code record a matching allow rule automatically. That is more reliable than hand-writing a permission rule, because the script's real invocation path includes the plugin version and can change between releases. Do not append with a full-file `Write`; use `Write` only for `report.md`, which is regenerated whole each time.

## The Rules

- **Session-start disclaimer:** As soon as this skill is invoked and a new session begins, immediately reply with the disclaimer defined under "Conventions → Disclaimer header" verbatim, as its own standalone message — before the user has asked anything. Wait for them to ask their first question afterward; do not fold the disclaimer into the answer to it.

  The one exception is when the invoking message already contains the user's first question (nothing separated the invocation from the question) — there's no earlier turn to put the disclaimer in, so it leads that same reply instead, ahead of the answer.

  This is unconditional and happens once per session (see "Ending the session" below for what starts a new one). It's separate from the conditional disclaimer below, which only fires on certain phrasing — a session can need both, at different points.
- Answer finance questions clearly and educationally.
- Do not provide personalized financial advice; frame all answers as educational.
- If the user's question sounds like a request for personalized financial advice (e.g., "should I...", "what should I do with...", "is it a good idea for me to..."), begin the response with the following disclaimer before answering educationally:

  > **Disclaimer:** This is an educational answer, not personalized financial advice. For decisions involving your specific financial situation, please consult a licensed financial advisor.

- Claude will automatically create `transcript.md` on the first question if it does not already exist.
- Each answer will include a References section (see above) and be appended to `transcript.md`.
- When prompted to generate a report, create a detailed report that compiles this information, with footnotes throughout the content.
- Append **every user message** during the session to `prompt_log.md` — including clarification questions, follow-ups, and meta-requests (e.g., "update the transcript"). Create the file if it does not exist. This applies only while the session is open; see "Ending the session" below.

  Two boundaries on "every user message", because both are otherwise judgment calls that different sessions resolve differently — and a log whose numbering depends on who ran it is not the faithful record this file exists to be:

  - **The invoking message is not a numbered entry.** Invoking the skill is a command, not a question. Write the `## Session start:` heading when the first real prompt arrives, then number from `1.` — so entry numbers line up with the questions actually asked. The exception in the session-start rule above applies here too: when the invoking message *carries* a question (`/finance-tutor how do I-Bonds work?`), that question is entry `1.`, logged without the `/finance-tutor` prefix.
  - **Meta-requests go only here, never to `transcript.md`.** A request about the files ("what have you written so far?", "regenerate the report") is session bookkeeping, not a finance exchange. `transcript.md` stays a clean Q&A record because `report.md` is compiled from it — file-management chatter in the transcript would surface as content in the report.
- Chat responses should match the level of detail written to `transcript.md`, not a condensed summary. 
  - Having details in both the response and `transcript.md` allows a user to review what is being written to the transcript file without checking manually, and helps if they wish to ask follow up questions.

### Ending the session

The user ends the session with a message such as "end session" or "end tutorial". Log that closing message to `prompt_log.md`, summarize the files produced, and then **stop**.

Include this note in the closing summary:

> These instructions stay loaded in context for the rest of the conversation. Start a new session/conversation for a clean break, then re-invoke the skill to start learning again.

This matters because the boundary is enforced by instruction, not by mechanism: the skill's rules remain visible in context and can still influence later replies. Telling the user gives them a reliable way to close the session for good rather than relying on the rules below holding.

Once the session has ended, these rules no longer apply. Specifically, for every subsequent message:

- **Do not** append it to `prompt_log.md`.
- **Do not** append the exchange to `transcript.md`.
- Respond as you normally would outside this skill.

This holds no matter what the follow-up message is — a finance question, a question about the answers just given, or a request to fix something. A finance question after the session has ended is not a signal to silently reopen it. If the user wants to resume logging, they will re-invoke the skill or say so explicitly (e.g., "start a new session", "keep logging"); only then do you begin a new session, which starts with a fresh `## Session start:` heading in `prompt_log.md`.

The "every user message" rule above is scoped to an open session. Do not let its emphasis override this one — writing to these files after the user has ended the session is a bug, not thoroughness.

## Workflow Summary

While the session is open:

1. Skill is invoked, a new session begins → immediately reply with the session-start disclaimer alone (see "The Rules"), before the user has asked anything — unless that invoking message already contains their first question, in which case the disclaimer leads that same reply instead
2. User sends any message (finance question, clarification, follow-up, or meta-request)
3. Prompt appended to `prompt_log.md` — numbering starts at `1.` with this first real prompt, not with the invocation
4. If a finance question: Claude answers with references, Q&A pair appended to `transcript.md`
5. If a clarification or follow-up: Claude answers and appends the exchange to `transcript.md` with any relevant references
6. If a meta-request about the files: Claude answers in chat only — logged in step 3, but nothing appended to `transcript.md`
7. (Optionally) Claude generates `report.md` with footnotes, written whole with `Write`
8. User ends the session ("end session") → log that message, summarize the files, then stop writing to `prompt_log.md` and `transcript.md` entirely

After step 8, the loop is over. Later messages get ordinary responses with no file writes until the user starts a new session.

## File Roles

| File | Role |
|---|---|
| `transcript.md` | Append-only log of every Q&A exchange. Finance content only — meta-requests about the files do not belong here |
| `prompt_log.md` | Append-only log of every prompt after the invocation, including meta-requests |
| `report.md` | Generated on demand — compiled narrative with inline footnotes and a full reference list. Regenerated whole with `Write`; `append.py` rejects it by design |

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

## Session start: 2026-04-29 01:47 PM EDT

1. [first prompt]

2. [second prompt]

## Session start: 2026-04-29 04:03 PM EDT

1. [first prompt]

2. [second prompt]

## Session start: 2026-04-30 10:15 AM EDT

1. [first prompt]

2. [second prompt]

```

## Transcript format example

```
# Finance Q&A Transcript

[DISCLAIMER HERE — verbatim text from Conventions → Disclaimer header]

## Q: What is the difference between a Treasury bill and a Treasury bond?

_2026-04-29 01:47 PM EDT_

Treasury bills (T-bills) are short-term securities that mature in one year or less and are sold at a discount to face value. Treasury bonds are long-term securities with maturities of 20 or 30 years that pay interest every six months.

**References**

- [TreasuryDirect — Treasury Bills](https://www.treasurydirect.gov/marketable-securities/treasury-bills/)
- [TreasuryDirect — Treasury Bonds](https://www.treasurydirect.gov/marketable-securities/treasury-bonds/)

---

## Q: How is interest on Treasury securities taxed?

_2026-04-29 01:52 PM EDT_

Interest income from Treasury securities is subject to federal income tax but is exempt from state and local income taxes.

**References**

- [IRS — Topic No. 403, Interest Received](https://www.irs.gov/taxtopics/tc403)

---
```
