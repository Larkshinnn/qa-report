# QA Report

Standalone QA reporting app extracted from Workbench.

## Structure

- `frontend/`: Vue 3 + Vite app for Vercel.
- `backend/`: FastAPI + PostgreSQL API for Railway.
- `docs/`: PRD and design baseline.

## Local development

1. Create `backend/.env` from `backend/.env.example`.
2. Create `frontend/.env` from `frontend/.env.example`.
3. Start PostgreSQL and run `alembic upgrade head` from `backend/`.
4. Start the API with `uvicorn app.main:app --reload --port 8000`.
5. Start the frontend with `pnpm dev` from `frontend/`.

Google OAuth requires a Google Cloud OAuth Web Application client. Register the exact callback URL from `GOOGLE_REDIRECT_URI`.

## Deployment

Deploy `backend/` to Railway and `frontend/` to Vercel. The complete workflow,
environment variables, health check, and smoke test are in
`docs/DEPLOYMENT.md`. Google OAuth is configured only after both deployments
are healthy.
