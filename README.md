# Midterm Petition App

A small Flask petition app for students to sign a petition to abolish midterms. Students can enter their name, optionally leave a rationale, and view the current signature count.

## Features

- Public signing page
- Optional rationale field
- Public signature count and recent signatures
- Full signatures page with pagination
- CSV export at `/export.csv`
- Railway-ready with `railway.toml`
- Uses Railway Postgres through `DATABASE_URL`
- Falls back to local SQLite for development

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open:

```text
http://localhost:5000
```

## Railway deployment

### Option A: Deploy from GitHub

1. Create a new GitHub repository and push this folder.
2. In Railway, create a new project.
3. Choose **Deploy from GitHub repo**.
4. Add a PostgreSQL database service in the same Railway project.
5. In your app service variables, set:

```text
DATABASE_URL=${{Postgres.DATABASE_URL}}
SECRET_KEY=make-this-a-long-random-string
```

6. Deploy the app.
7. In the app service settings, generate a public domain.

### Option B: Deploy with Railway CLI

```bash
railway login
railway init
railway up
```

Then add a PostgreSQL service and set the same variables above.

## Useful routes

- `/` — petition signing page
- `/signatures` — all signatures
- `/export.csv` — download signatures as CSV
- `/health` — health check for Railway

## Privacy note

The app stores only the name, optional rationale, and signing timestamp. Ask students to sign only with their own name.
