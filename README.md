# 🍴 FoodQ — GitHub + Deploy Classroom Demo

FoodQ is a Thai-language cafeteria queue demo with three roles: student, merchant, and admin.

## Two deployment routes

| Feature | GitHub Pages (`docs/`) | Render (`server.py`) |
|---|---|---|
| Public URL | Yes | Yes |
| Frontend UI | Yes | Yes |
| Python Backend + API | No | Yes |
| Database | Browser LocalStorage | SQLite on server (temporary on Free plan) |
| Shared orders across devices | No | Yes, while server remains running |

### Upload project to GitHub (no Terminal)

1. Create a repository named `foodq-cafeteria-demo` at https://github.com/new .
2. Unzip the **FoodQ_GitHub_Deploy_Ready.zip** file.
3. Open the new GitHub repository > **Add file** > **Upload files**.
4. Upload the **contents inside** `FoodQ_GitHub_Deploy_Ready` (including `server.py`, `index.html`, `render.yaml`, `docs/index.html`). If GitHub's uploader does not keep the `docs/` folder, add it separately using the browser or git.
5. Click **Commit changes**. Never upload `*.sqlite3`, personal names, or secret tokens.

### Route A — GitHub Pages (frontend only)

1. Repository > **Settings** > **Pages**.
2. Under **Build and deployment**, select **Deploy from a branch**.
3. Select branch `main`, folder `/docs`, and **Save**.
4. GitHub Pages will show a URL similar to `https://YOUR_USERNAME.github.io/foodq-cafeteria-demo/` once published.

In this mode the role buttons work but all orders are stored **locally per browser**. Different students will NOT see shared orders. This is intentional for GitHub Pages.

### Route B — Render (Frontend + Backend + SQLite)

1. Open https://dashboard.render.com/ and sign in.
2. Choose **New** > **Web Service** and connect the GitHub repository.
3. Runtime: `Python`; Region: `Singapore`; Plan: `Free` (if available).
4. Build command: `python -m compileall -q server.py`
5. Start command: `python server.py`
6. Set the health check path to `/api/health`. Create the service and wait for deploy.
7. Open the `https://YOUR_SERVICE.onrender.com/` URL displayed by Render.

`render.yaml` is also supplied for the Render Blueprint flow (New > Blueprint). When deployed, the app binds to `0.0.0.0` and Render's `PORT` environment variable.

**Important:** Render Free has a temporary filesystem: SQLite orders can disappear when the service sleeps, restarts, or redeploys. It is **not suitable for long-term storage**. For permanent storage, migrate to PostgreSQL or use a paid persistent disk. The classroom demo intentionally has no authentication/authorization; do not use real student details or sensitive data, and do not deploy it for actual school transactions.

### Local preview

- Open `docs/index.html` directly: static offline demo.
- Run `python3 server.py` and browse `http://127.0.0.1:8877`: API + SQLite.
- Health check: `http://127.0.0.1:8877/api/health`.

### Smoke test for class

1. Student: choose a store and add food, then book a queue.
2. Merchant: switch role, select the corresponding store, and advance the order to `ready`.
3. Student: refresh the queue list to see updated status (Render version).
4. Admin: view overview metrics. Reset is intentionally disabled on public Render.

### Architecture

Browser UI (`index.html`) → `/api/orders`, `/api/state` (Python `server.py`) → SQLite (`foodq.sqlite3`, auto-created on server at runtime). For GitHub Pages the API is intentionally bypassed and LocalStorage is used instead.
