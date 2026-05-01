# Changelog

## Current audit baseline

- Core CLI, collector and pytest are the active project focus.
- GUI is paused and kept as experimental code.
- AI integration has been removed from the active code and docs.
- HTTP attendance analysis accepts request-level `aliases` and merges matching
  collector events into the canonical `employee_id`.
- Default local sample paths now point to `data/attendance.csv`, `data/vhod.ndjson`, `data/vihod.ndjson`, and `data/person.sample.json`.
- Analyzer can read collector SQLite databases directly through SQLAlchemy (`file_type="sqlite"` or `.db` auto-detection).
- Tests are the source of truth for current behavior.
