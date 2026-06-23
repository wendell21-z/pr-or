# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PR-OR** is a press shop production scheduling system for VW (Volkswagen). It combines a Flask REST API backend with a Vue 3 frontend, centered around an OR-Tools CP-SAT solver that generates 7-day production plans for stamping dies across production lines.

## Directory Structure

```
app.py              # Flask app factory + /solve/start endpoint (scheduler entry)
config.py           # Flask configs (dev/prod, DB URI, pool options)
models.py           # SQLAlchemy ORM models: Car, Die, Part, Task, Day, etc.
scheduler.py        # ProductionScheduler — fetches data, builds CP-SAT model, solves
fact_api.py         # REST API blueprint (/fact/*) for CRUD on all domain entities
utils.py            # ensure_day(), ensure_default_working_time() helpers
requirements.txt    # Dependencies: flask, sqlalchemy, pymysql
frontend/           # Vue 3 + Vite + TypeScript + Element Plus UI
tests/              # pytest directory (currently test_partinventory_query.py)
```

## Key Architecture Concepts

### Scheduler Pipeline (`scheduler.py`)
`ProductionScheduler(line_id, start_date, days_count=7)` is the core solver:
1. **fetch_data()** — queries DB for dies on the line, parts, consumption (via CarUsage joins), initial inventory, dunnage data, pinned tasks; auto-creates missing Day rows.
2. **solve()** — builds a CP-SAT model with boolean `produce_vars`, integer `qty_vars`, `stock_vars` per (die, day); constraints: daily time limit (min 120 min per active die), stock balance (`prev_stock + qty - consumption`), dunnage capacity caps, pinned task enforcement; objective maximizes total fill rate. Returns list of `[{date, tasks: [{die_id, die_name, quantity, duration_minutes, dunnage}]}]`.

### REST API (`fact_api.py`)
All CRUD for domain entities lives in the `fact` Blueprint at `/fact/*`:
- **Entities**: `working-time`, `day`, `line`, `die`, `dunnage`, `part`, `car`, `part-car`, `car-usage`, `dunnage-inventory`, `part-inventory`
- **Pattern**: each entity has upsert (`POST`), list (`GET`), delete (`DELETE`). Batch upsert for die, dunnage, day, car-usage, part-inventory, dunnage-inventory.
- Serialization is via `_serialize(entity)` / `_serialize_all(items)`, with camelCase field names matching the Kotlin backend contract.

### ORM Models (`models.py`)
All MySQL tables mapped as SQLAlchemy models. Key relationships:
- `Die` ↔ `Part` (one-to-many via die_id)
- `Car` ↔ `Part` (many-to-many via CarPart)
- `DunnageInventoryHistory` composite PK on (dunnage_id, day_id)
- `PartInventory` composite PK on (part_id, day_id)

## Development Commands

### Backend
```bash
# Run the Flask app (default: port 8080)
python app.py

# Custom config
FLASK_CONFIG=development python app.py

# Python env (venv exists at .venv/)
source .venv/bin/activate
pip install -r requirements.txt
```

### Frontend
```bash
cd frontend
npm run dev        # Vite dev server
npm run build      # Production build
npm run preview    # Preview built output
npm run build-check  # vue-tsc + build
```

### Tests
```bash
pytest tests/ -v
pytest tests/test_partinventory_query.py -v -s   # single test with output
```

## Important Conventions & Gotchas

- **Date format**: Day IDs use ISO strings `'YYYY-MM-DD'` throughout. Always pass dates as strings matching Day.id.
- **Pinned tasks** have 5 types: `is_day_pinned`, `is_die_pinned`, `is_quantity_pinned`, `is_seq_pinned`, `pinned_type`. Only `is_day_pinned` + `is_quantity_pinned` are enforced by the solver.
- **Minimum production time**: any active die scheduled must produce ≥120 minutes or 0 (enforced via big-M implication).
- **Dunnage capacity constraint**: `sum(stock_vars[related_parts]) <= empty_dunnages * capacity + initial_stock`. Stock cannot exceed dunnage physical limits.
- **Consumption calculation**: `Sum(car_usage.car_id == CarPart.car_id * CarPart.usage)` grouped by day and part.
- **`_sanity_checks()`** in scheduler prints debug info (capacity, stock, consumption mismatches). Run with `FLASK_CONFIG=development` for detailed traces on errors.
