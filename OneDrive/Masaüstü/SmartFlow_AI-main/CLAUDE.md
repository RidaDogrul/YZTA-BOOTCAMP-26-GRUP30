# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All commands run from `backend/` with the venv active (`.venv\Scripts\Activate.ps1`).

```powershell
# Run server
uvicorn app.main:app --reload

# Run all tests
pytest

# Run a single test
pytest tests/test_endpoints.py::test_dashboard_summary

# Load demo data (server must be running)
curl -X POST http://127.0.0.1:8000/api/seed
```

## Architecture

**Stack:** FastAPI + SQLAlchemy 2.x + Pydantic v2 + SQLite. No async ORM — all DB calls are synchronous via `Depends(get_db)` request-scoped sessions.

**Request flow:** `main.py` → router (`app/routers/*.py`) → `crud.py` (pure DB functions taking `Session`) → ORM model → Pydantic schema for serialization.

**Key conventions:**
- `crud.py` contains all DB queries as plain functions; routers call crud directly, no service layer except `dashboard_service.py`.
- `ProductRead` has a `from_orm_with_flags()` classmethod — use it instead of `model_validate()` to get `is_critical` computed correctly.
- Turkish status strings are load-bearing: `"Hazırlanıyor"`, `"Kargoda"`, `"Teslim Edildi"`, `"Gecikmiş"`, `"Bekliyor"`, `"Tamamlandı"`. Changing these breaks dashboard counts and tests.
- `delayed_orders` is counted via `Order.cargo_status == "Gecikmiş"`, not `Order.status`.

**Kişi 2 extension points** (not yet implemented):
- Add `app/routers/chat.py`, `alerts.py`, `tasks_generate.py` and include them in `main.py`.
- `schemas.py` already has `ChatRequest` and `ChatResponse` stubs.
- `crud.create_message()` and `crud.create_task()` are the write helpers.

**Test setup:** `tests/conftest.py` creates a separate `test_smartflow.db` and overrides `get_db` via `app.dependency_overrides`. Each test gets a fresh session but the DB schema persists for the session. Tests that read data must call `POST /api/seed` first.

## Git

Branch naming: `feature/<name>`, `bugfix/<name>`, `docs/<name>`, `refactor/<name>`.  
Commit style: `feat(scope):`, `fix(scope):`, `test(scope):`, `chore:`. No Claude co-author signature.
