#!/usr/bin/env python3
"""deadlines.py - a tiny deadline tracker (CSCI 599 A3).

Used two ways, from the same file:
  * as a library by the a3assistant Hermes plugin (tool `deadline_tracker`);
  * as the stand-alone script of the published `deadline-tracker` skill:
        python3 deadlines.py list
        python3 deadlines.py add "Lab 3 report" 2026-11-20 --tag school
        python3 deadlines.py add "Dentist" 2026-11-18T15:30
        python3 deadlines.py complete <id>
        python3 deadlines.py due-soon --hours 48

Data: one JSON file, default $DEADLINES_FILE, else $HERMES_HOME/deadlines.json, else
~/.hermes/deadlines.json. Writes take an exclusive lock and replace the file atomically.
Dates without a time mean "end of that day" (23:59). Times are local to $TZ_NAME
(default America/Los_Angeles). Standard library only. Use synthetic data only.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
import secrets
import sys
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import fcntl  # POSIX
except ImportError:  # pragma: no cover - Windows: no lock, still atomic replace
    fcntl = None

MAX_TITLE = 200
MAX_ITEMS = 500


def default_tz() -> ZoneInfo:
    return ZoneInfo(os.environ.get("TZ_NAME") or "America/Los_Angeles")


def default_path() -> Path:
    if os.environ.get("DEADLINES_FILE"):
        return Path(os.environ["DEADLINES_FILE"]).expanduser()
    home = os.environ.get("HERMES_HOME") or "~/.hermes"
    return Path(home).expanduser() / "deadlines.json"


def parse_due(text: str, tz: ZoneInfo) -> dt.datetime:
    """'YYYY-MM-DD' (end of day) or 'YYYY-MM-DDTHH:MM' / 'YYYY-MM-DD HH:MM', local time."""
    s = (text or "").strip()
    try:
        if len(s) == 10:
            d = dt.date.fromisoformat(s)
            return dt.datetime(d.year, d.month, d.day, 23, 59, tzinfo=tz)
        v = dt.datetime.fromisoformat(s.replace(" ", "T"))
    except ValueError:
        raise ValueError(f"bad due date {text!r}: use YYYY-MM-DD or YYYY-MM-DDTHH:MM") from None
    return v.replace(tzinfo=tz) if v.tzinfo is None else v.astimezone(tz)


class DeadlineStore:
    def __init__(self, path: Path | str | None = None, tz: ZoneInfo | None = None):
        self.path = Path(path) if path else default_path()
        self.tz = tz or default_tz()

    # ------------------------------------------------------------ file I/O
    @contextlib.contextmanager
    def _locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.path.with_name(self.path.name + ".lock")
        with open(lock_path, "a") as lf:
            if fcntl:
                fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl:
                    fcntl.flock(lf, fcntl.LOCK_UN)

    def _read(self) -> dict:
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            return {"deadlines": []}
        if not isinstance(data, dict) or not isinstance(data.get("deadlines"), list):
            raise ValueError(f"{self.path} is not a deadlines file")
        return data

    def _write(self, data: dict) -> None:
        fd, tmp = tempfile.mkstemp(prefix=".deadlines-", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=1)
                f.flush()
                os.fsync(f.fileno())
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.path)
        except BaseException:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(tmp)
            raise

    # ------------------------------------------------------------ operations
    def _view(self, item: dict, now: dt.datetime) -> dict:
        due = dt.datetime.fromisoformat(item["due"])
        hours = (due - now).total_seconds() / 3600
        return {**item, "hours_left": round(hours, 1), "overdue": (not item.get("done")) and hours < 0}

    def list(self, include_done: bool = False, now: dt.datetime | None = None) -> list[dict]:
        now = now or dt.datetime.now(self.tz)
        items = [i for i in self._read()["deadlines"] if include_done or not i.get("done")]
        return [self._view(i, now) for i in sorted(items, key=lambda i: i["due"])]

    def add(self, title: str, due: str, tag: str = "") -> dict:
        title = " ".join((title or "").split())
        if not title:
            raise ValueError("title is required")
        if len(title) > MAX_TITLE:
            raise ValueError(f"title longer than {MAX_TITLE} characters")
        due_at = parse_due(due, self.tz)
        tag = " ".join((tag or "").split())[:40]
        with self._locked():
            data = self._read()
            if len(data["deadlines"]) >= MAX_ITEMS:
                raise ValueError(f"too many deadlines (max {MAX_ITEMS})")
            item = {"id": secrets.token_hex(3), "title": title, "due": due_at.isoformat(timespec="minutes"),
                    "tag": tag, "done": False,
                    "created": dt.datetime.now(self.tz).isoformat(timespec="seconds")}
            data["deadlines"].append(item)
            self._write(data)
        return item

    def complete(self, item_id: str) -> dict:
        with self._locked():
            data = self._read()
            for item in data["deadlines"]:
                if item["id"] == (item_id or "").strip():
                    item["done"] = True
                    item["completed"] = dt.datetime.now(self.tz).isoformat(timespec="seconds")
                    self._write(data)
                    return item
        raise KeyError(f"no deadline with id {item_id!r}")

    def due_soon(self, hours: float = 48, now: dt.datetime | None = None) -> list[dict]:
        """Open deadlines due within `hours` from now, plus overdue ones."""
        now = now or dt.datetime.now(self.tz)
        return [i for i in self.list(now=now) if i["hours_left"] <= hours]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Deadline tracker (JSON output).")
    p.add_argument("--file", help="data file (default: $DEADLINES_FILE or $HERMES_HOME/deadlines.json)")
    sub = p.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("list")
    pl.add_argument("--all", action="store_true", help="include completed")
    pa = sub.add_parser("add")
    pa.add_argument("title")
    pa.add_argument("due", help="YYYY-MM-DD or YYYY-MM-DDTHH:MM (local time)")
    pa.add_argument("--tag", default="")
    pc = sub.add_parser("complete")
    pc.add_argument("id")
    ps = sub.add_parser("due-soon")
    ps.add_argument("--hours", type=float, default=48)
    a = p.parse_args(argv)
    store = DeadlineStore(a.file)
    try:
        if a.cmd == "list":
            out = {"ok": True, "deadlines": store.list(include_done=a.all)}
        elif a.cmd == "add":
            out = {"ok": True, "added": store.add(a.title, a.due, a.tag)}
        elif a.cmd == "complete":
            out = {"ok": True, "completed": store.complete(a.id)}
        else:
            out = {"ok": True, "hours": a.hours, "due_soon": store.due_soon(a.hours)}
    except (ValueError, KeyError) as exc:
        print(json.dumps({"ok": False, "error": str(exc).strip("'\"")}))
        return 1
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
