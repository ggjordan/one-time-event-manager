# Deploying the app online

Get the app off your machine and onto the web. Two straightforward options:

---

## Option 1: PythonAnywhere (good for SQLite + file uploads)

Free tier, persistent disk, and SQLite work well. Suited to a single store / low traffic.

### 1. Put the code online

- Create a **GitHub** (or GitLab) repo and push this project:
  - `git init && git add . && git commit -m "Initial commit"`
  - Create repo on GitHub, then: `git remote add origin <url>` and `git push -u origin main`
- Or upload the project as a zip and extract it in your PythonAnywhere home.

### 2. PythonAnywhere setup

1. Sign up at [pythonanywhere.com](https://www.pythonanywhere.com) (free account).
2. **Web** tab → **Add a new web app** → **Manual configuration** → pick Python 3.10 (or 3.11).
3. **Virtualenv**: click the link, create one (e.g. `myenv`), then in it run:
   ```bash
   pip install -r requirements.txt
   flask db upgrade   # create tables from migrations
   ```
   If you didn’t commit `migrations/`, run your migrations on the server after copying them or generate with `flask db init` and `flask db migrate` there.

4. **WSGI configuration file**: open the link and replace the contents with (adjust `yourusername` and `yourapp`):
   ```python
   import sys
   path = '/home/yourusername/yourapp'
   if path not in sys.path:
       sys.path.insert(0, path)

   from wsgi import application
   ```

5. **Environment variables**: in **Web** → **Environment** (or in a script you run once), set:
   - `SECRET_KEY` — a long random string (e.g. from `python -c "import secrets; print(secrets.token_hex(32))"`).

6. **Static files** (optional): if you add a `static` URL, map it in the Web tab to your app’s `static` folder.

7. **Reload** the web app. Your app will be at `https://yourusername.pythonanywhere.com`.

### 3. Database and uploads

- SQLite: the app will create `instance/app.db` the first time it runs (and after `flask db upgrade`). No extra DB setup.
- Screenshots: stored under `instance/uploads/screenshots/`. They persist on PythonAnywhere’s disk.

---

## Option 2: Render (free tier, from Git)

Good if you want “push to Git → auto deploy”. Free tier uses ephemeral disk: SQLite and uploads are lost on redeploy or after spin-down. For a real long-term site, add a PostgreSQL DB and/or persistent disk later.

### 1. Push code to GitHub

Same as above: repo created, code pushed.

### 2. Render setup

1. Sign up at [render.com](https://render.com) and connect your GitHub account.
2. **New** → **Web Service**. Select your repo.
3. Settings:
   - **Build command:** `pip install -r requirements.txt && flask db upgrade`
   - **Start command:** `gunicorn -b 0.0.0.0:$PORT wsgi:app`
   - **Environment variables:** add `SECRET_KEY` (same as above).

4. Deploy. Your app will be at `https://your-service-name.onrender.com`.

### 3. Limitations on free tier

- App spins down after inactivity; first request can be slow.
- SQLite and `instance/uploads` are ephemeral — they reset on deploy or when the container is recreated. For production, add a Render PostgreSQL database and switch `DATABASE_URL` to it (and consider cloud storage for screenshots).

---

## Checklist before going live

- [ ] Set a strong **SECRET_KEY** in the host’s environment (never commit it).
- [ ] Run **migrations** on the server (`flask db upgrade`) so tables exist.
- [ ] If you use a production DB (e.g. PostgreSQL), set **DATABASE_URL** and install the driver (e.g. `psycopg2-binary` in `requirements.txt`).
- [ ] For production, set `debug=False` (your `wsgi.py` only runs `app.run()` when executed directly; gunicorn doesn’t use that).

---

## Run production-style locally

To test with gunicorn (same as Render):

```bash
gunicorn -b 127.0.0.1:5001 wsgi:app
```

Then open `http://127.0.0.1:5001`.
