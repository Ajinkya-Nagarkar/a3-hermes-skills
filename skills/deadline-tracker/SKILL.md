---
name: deadline-tracker
description: Track personal deadlines (add, list, complete, what is due soon) in a small local JSON file. Uses the deadline_tracker tool when the agent has it, otherwise the bundled stand-alone Python script.
version: 1.0.0
author: Ajinkya-Nagarkar
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Productivity, Deadlines, Reminders, Planning]
---

# Deadline Tracker

Keeps a short list of deadlines (title, due date/time, optional tag) and answers
"what is due soon?". Written for the CSCI 599 Assignment 3 personal assistant, where it
also feeds the morning briefing, the evening recap and proactive alerts.

Use synthetic or your own non-sensitive data only. The file holds plain text titles.

## When to Use

- The user asks to add, list or complete a deadline ("add a deadline: Lab 3 report on
  Friday", "what's due this week?", "mark the report done").
- A briefing, recap or reminder needs the deadlines due in the next N hours.

## Procedure

**1. If the `deadline_tracker` tool is available, use it and do not run the script.**
(The A3 deployment exposes this tool from its own plugin and has the terminal disabled.)

| Want | Tool call |
|---|---|
| open deadlines, soonest first | `deadline_tracker(action="list")` |
| add | `deadline_tracker(action="add", title="Lab 3 report", due="2026-11-20", tag="school")` |
| complete | `deadline_tracker(action="complete", id="<id from list>")` |
| due within N hours (incl. overdue) | `deadline_tracker(action="due_soon", hours=48)` |

**2. Otherwise run the bundled script** with the terminal tool (Python 3.9+, standard
library only):

```bash
python3 ${HERMES_SKILL_DIR}/scripts/deadlines.py list
python3 ${HERMES_SKILL_DIR}/scripts/deadlines.py add "Lab 3 report" 2026-11-20 --tag school
python3 ${HERMES_SKILL_DIR}/scripts/deadlines.py add "Project demo" 2026-11-18T15:30
python3 ${HERMES_SKILL_DIR}/scripts/deadlines.py complete <id>
python3 ${HERMES_SKILL_DIR}/scripts/deadlines.py due-soon --hours 48
```

Every command prints JSON: `{"ok": true, ...}` or `{"ok": false, "error": "..."}`.

**3. Answer briefly**: one line per deadline with its due time in words ("Fri 17:00"),
overdue items first and marked OVERDUE.

## Dates

- `YYYY-MM-DD` means the end of that day (23:59); `YYYY-MM-DDTHH:MM` is a local time.
- Convert relative dates ("next Friday") to an absolute date yourself before calling.
- Time zone: `$TZ_NAME` (default `America/Los_Angeles`).

## Data file

`$DEADLINES_FILE` if set, else `$HERMES_HOME/deadlines.json`, else
`~/.hermes/deadlines.json`. Writes take a file lock and replace the file atomically, so
two runs never corrupt it. At most 500 items, titles up to 200 characters.

## Pitfalls

- An unknown id returns `{"ok": false}`: run `list` first and use the exact id.
- Do not store secrets, passwords or other private details in titles.
- Do not invent deadlines: report only what the tool or script returned.

## Verification

After `add` or `complete`, run `list` (or the tool's `list` action) and check that the
item appears or is gone.
