# a3-hermes-skills

A small Hermes Agent skill tap from a USC CSCI 599 (Agentic AI) assignment.
All examples use synthetic data.

| Skill | What it does |
|---|---|
| [`deadline-tracker`](skills/deadline-tracker/SKILL.md) | Add, list and complete deadlines; "what is due in the next N hours?". Uses the `deadline_tracker` tool when the agent has one, otherwise the bundled stand-alone script (`scripts/deadlines.py`, Python standard library only). |

## Install (Hermes Agent v0.22.7)

```bash
hermes skills install Ajinkya-Nagarkar/a3-hermes-skills/skills/deadline-tracker
# or add the whole repo as a tap:
hermes skills tap add Ajinkya-Nagarkar/a3-hermes-skills
```

Then ask the agent, e.g. "add a deadline: Lab 3 report on 2026-11-20" or "what is due in
the next 48 hours?".

The script also works on its own:

```bash
python3 skills/deadline-tracker/scripts/deadlines.py add "Lab 3 report" 2026-11-20 --tag school
python3 skills/deadline-tracker/scripts/deadlines.py due-soon --hours 72
```

`index.md` and `privacy.md` are the home page and privacy note of the assignment's test
OAuth app (GitHub Pages).

License: MIT.
