Интерфейс верстаем строго по папке design/. Перед любой работой с UI прочитай design/CLAUDE.md и следуй ему.

Фронтенд — `frontend/` (Vite + React + TypeScript). `frontend/src/styles/tokens.css` — копия `design/tokens/tokens.css`; при изменении токенов обнови обе.

Бэкенд — `backend/` (FastAPI + PostgreSQL, запуск и API — `backend/README.md`). Логика серии и пропусков продублирована в `backend/app/services/stats.py` и `frontend/src/lib/stats.ts` — меняй обе.
