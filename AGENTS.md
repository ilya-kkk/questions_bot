# Repository Guidelines

## Project Structure & Module Organization
- `app/`: Core bot code (`bot.py`, `handlers.py`, `database.py`, `config.py`, `messages.py`).
- `migrations/`: SQL migration files plus `README.md`; applied via `run_migrations.py`.
- Root scripts: `import_data.py`, `run_migrations.py`, `new_database.py`, `classify_topics.py`.
- Tests: `test_*.py` in the repository root.
- Data/assets: `raw.json` (question seed data), `Dockerfile`, `docker-compose.yaml`.

## Build, Test, and Development Commands
- `docker-compose up --build -d`: Build and start the bot and Postgres containers.
- `docker-compose exec app python run_migrations.py`: Apply SQL migrations to the database.
- `docker-compose exec app python import_data.py`: Load questions from `raw.json`.
- `docker-compose down`: Stop and remove containers.
- `python -m unittest test_simple.py`: Run a single unit test file locally.
- `python -m unittest`: Run all unit tests in the repo.

## Coding Style & Naming Conventions
- Python 3.12, 4-space indentation, standard PEP 8 style.
- Use `snake_case` for functions/variables, `PascalCase` for classes.
- No formatter or linter is enforced; keep changes consistent with existing files.

## Testing Guidelines
- Framework: built-in `unittest` (`test_simple.py`, `test_database.py`).
- New tests should be named `test_*.py` and use `unittest.TestCase`.
- Mock external services (DB, network) with `unittest.mock`.

## Commit & Pull Request Guidelines
- Commit messages are short, imperative, sentence case (English or Russian both appear).
- PRs should include: purpose of change, how to test, and any migration/data impact.
- Link related issues or deployment notes when applicable.

## Configuration & Deployment Notes
- Create a `.env` in the repo root with `BOT_TOKEN` and Postgres credentials.
- Deployment runs via CI/CD after `git push`; check logs via `ssh cm5 "docker-compose logs"`.
- Do not run server commands directly; use the SSH wrapper as documented.
