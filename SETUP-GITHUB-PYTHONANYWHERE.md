# Step-by-step: GitHub + PythonAnywhere (first time)

Follow these steps in order. Replace anything in CAPS with your own details.

---

# Part 1: GitHub

## Step 1.1 — Create a GitHub account (if you don’t have one)

1. Go to **https://github.com**
2. Click **Sign up**
3. Enter email, password, username. Complete sign-up and verify your email.

## Step 1.2 — Install Git on your computer (if needed)

- **Mac:** Open Terminal and run: `git --version`  
  - If it says "command not found", install Xcode Command Line Tools: run `xcode-select --install` and follow the prompts.  
  - Or install from https://git-scm.com/download/mac
- **Windows:** Download and run the installer from https://git-scm.com/download/win

## Step 1.3 — Create a new repository on GitHub

1. Log in to GitHub.
2. Click the **+** (top right) → **New repository**.
3. **Repository name:** e.g. `boardgame-events` (no spaces).
4. Leave **Public** selected.
5. **Do not** check "Add a README" or "Add .gitignore" — we already have files.
6. Click **Create repository**.

## Step 1.4 — Push your project from your computer

Open **Terminal** (Mac) or **Git Bash** (Windows) and run these commands **one at a time**. Replace `YOUR_GITHUB_USERNAME` and `boardgame-events` if you used a different repo name.

**Go to your project folder:**
```bash
cd /Users/jordanbird/Cursor
```

**Turn this folder into a Git repo and make the first commit:**
```bash
git init
git add .
git status
```
You should see a list of files. Then:
```bash
git commit -m "Initial commit"
```

**Connect to GitHub and push (use YOUR repo URL from GitHub):**
```bash
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/boardgame-events.git
git branch -M main
git push -u origin main
```

- If it asks for **username**: your GitHub username.
- If it asks for **password**: use a **Personal Access Token**, not your normal password.  
  To create one: GitHub → your profile (top right) → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)** → **Generate new token**. Give it a name, check **repo**, generate, then **copy the token** and paste it when Git asks for a password.

When `git push` finishes without errors, your code is on GitHub.

---

# Part 2: Create your SECRET_KEY

You need a long random string for the app. Do this **once** on your computer.

1. Open Terminal.
2. Run:
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```
3. **Copy the whole line of letters and numbers** (e.g. `a1b2c3d4e5...`).  
   Save it in a temporary note — you’ll paste it into PythonAnywhere in Part 3.  
   **Don’t share it or put it in GitHub.**

---

# Part 3: PythonAnywhere

## Step 3.1 — Sign up

1. Go to **https://www.pythonanywhere.com**
2. Click **Pricing & signup** → **Create a Beginner account** (free).
3. Choose a **username** and password. Remember this username — your site will be `YOURUSERNAME.pythonanywhere.com`.

## Step 3.2 — Get your code onto PythonAnywhere

1. Open the **Dashboard** (or click the PythonAnywhere logo).
2. Click the **Consoles** tab.
3. Click **$ Bash** (opens a Linux terminal).
4. **Clone your GitHub repo** (replace with your GitHub username and repo name):
   ```bash
   git clone https://github.com/YOUR_GITHUB_USERNAME/boardgame-events.git
   ```
   Enter your GitHub username and (if asked) your Personal Access Token as the password.
5. When it finishes, you’ll have a folder named `boardgame-events`. Check:
   ```bash
   ls boardgame-events
   ```
   You should see `app`, `wsgi.py`, `requirements.txt`, etc.

## Step 3.3 — Create the web app

1. Click the **Web** tab (top of the page).
2. Click **Add a new web app**.
3. Click **Next**.
4. Choose **Manual configuration** (not the Flask wizard). Click **Next**.
5. Choose **Python 3.10** (or 3.11). Click **Next**.
6. Your app will be created. You’ll see a page with **Code**, **WSGI configuration file**, **Virtualenv**, etc.

## Step 3.4 — Create a virtualenv and install dependencies

1. Click the **Consoles** tab. Click **$ Bash** to open a new console.
2. Run these commands **one at a time** (replace `YOUR_USERNAME` with your PythonAnywhere username):

   ```bash
   cd ~/boardgame-events
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   flask db upgrade
   ```

   When `flask db upgrade` finishes, your database tables are created. You can type `deactivate` to leave the virtualenv, or just leave the console open.

   **If you get "no such table: task_template" (or similar):** The app was fixed so this doesn’t happen. Pull the latest code (`git pull`), then run `flask db upgrade` again.

3. Go back to the **Web** tab. In the **Code** section, set:
   - **Source code / Directory:** `/home/YOUR_USERNAME/boardgame-events`
   - **Working directory:** leave blank (or the same path).
4. Scroll to **Virtualenv**. Click **Enter path to a virtualenv**.
5. Type: `/home/YOUR_USERNAME/boardgame-events/venv` and click the green check (or Save).  
   This tells PythonAnywhere to use the venv you just created.

## Step 3.5 — Edit the WSGI file

1. On the **Web** tab, find **WSGI configuration file**. Click the link (e.g. `/var/www/YOUR_USERNAME_pythonanywhere_com_wsgi.py`).
2. **Delete everything** in the file.
3. **Paste exactly this** (change `YOUR_USERNAME` and `boardgame-events` if your folder name is different):

   ```python
   import sys
   path = '/home/YOUR_USERNAME/boardgame-events'
   if path not in sys.path:
       sys.path.insert(0, path)

   from wsgi import application
   ```

4. Click **Save**.

## Step 3.6 — Set the SECRET_KEY

1. On the **Web** tab, scroll to **Environment variables** (or **Code** section — it may say "Environment").
2. Click **Enter environment variable** (or the **Add a new variable** / edit area).
3. **Variable name:** `SECRET_KEY`  
   **Value:** paste the long string you generated in Part 2 (the output of `secrets.token_hex(32)`).
4. Save (green check or Save button).

## Step 3.7 — Reload the app

1. Scroll to the top of the **Web** tab.
2. Click the big green **Reload** button (reloads your web app).
3. Open your site: **https://YOUR_USERNAME.pythonanywhere.com**

You should see your app. If you get an error, check the **Error log** on the Web tab for the exact message.

---

# Quick reference

| What | Where |
|------|--------|
| Your PythonAnywhere username | Top-right of the dashboard; also in the URL |
| Your app URL | https://YOUR_USERNAME.pythonanywhere.com |
| Project folder on PA | `/home/YOUR_USERNAME/boardgame-events` |
| Virtualenv path | `/home/YOUR_USERNAME/boardgame-events/venv` |
| SECRET_KEY | Web tab → Environment variables |
| Reload after changes | Web tab → green Reload button |
| Error messages | Web tab → Error log |

---

# If something goes wrong

- **502 / 504 error:** Check the **Error log** on the Web tab. Often it’s a typo in the WSGI path or a missing package — run `pip install -r requirements.txt` in the virtualenv again.
- **"No module named 'app'":** The `path` in the WSGI file must point to the folder that contains `app` and `wsgi.py` (e.g. `/home/YOUR_USERNAME/boardgame-events`).
- **"application" or "app" errors:** The WSGI file must end with `from wsgi import application` (no `:app`).
- **Database / table errors:** In a Bash console: `cd ~/boardgame-events`, `source venv/bin/activate`, then `flask db upgrade`.

Once this works, you can edit code on your computer, then run `git add .`, `git commit -m "Your message"`, `git push`, and on PythonAnywhere run `cd ~/boardgame-events && git pull` and click **Reload** on the Web tab to update the live site.
