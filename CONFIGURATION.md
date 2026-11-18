# Configuration and credential setup

This project keeps all credentials **outside the source code and outside the
shared ZIP/package**. No real API keys or passwords are included. Each person
runs the app with their own local configuration.

## 1. Create your local configuration file

From the project root:

```powershell
Copy-Item .env.example .env
```

On macOS/Linux:

```bash
cp .env.example .env
```

`.env` is ignored by Git and must never be shared or committed.

## 2. Fill in the keys you want to use

Open `.env` in a text editor:

```powershell
notepad .env
```

| Variable | Required? | Where to get it | Notes |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | Optional | Google AI Studio | Enables detailed visual analysis support |
| `GEMINI_MODEL` | Optional | Google AI Studio | Default: `gemini-3.5-flash-lite` |
| `PLANTNET_API_KEY` | Optional | Pl@ntNet API portal | Enables species cross-check |
| `PLANTNET_ENABLED` | Optional | Set `true` when a key is present | Disabled by default without a key |
| `AI_FALLBACK_ENABLED` | Recommended | Leave `true` | Uses external references when the local model is uncertain |
| `OPEN_METEO_ENABLED` | Optional | No key needed | Local weather context |
| `ADMIN_PASSWORD_HASH` | For admin panel | Generate locally (see below) | Never use a shared password |
| `ADMIN_SECRET_KEY` | For admin panel | Any long random string | Change before sharing a deployment |

Leave a key empty to disable that optional integration. The core trained-model
prediction path works without any external key.

## 3. Generate an admin password hash

```powershell
.\.venv-app\Scripts\python.exe run.py hash-password
```

Paste the printed hash into `.env` as `ADMIN_PASSWORD_HASH`, then replace
`ADMIN_SECRET_KEY` with a long random string.

## 4. Verify and run

```powershell
.\.venv-app\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-app\Scripts\python.exe run.py check
.\.venv-app\Scripts\python.exe run.py
```

Open:

- User app: <http://127.0.0.1:8000/>
- Admin panel: <http://127.0.0.1:8000/admin>
- API docs: <http://127.0.0.1:8000/docs>

## 5. Sharing rules

- Share `.env.example`, never `.env`.
- If a key is accidentally shared, rotate it immediately with the provider.
- Do not put keys in screenshots, issue reports, notebooks, or source files.
- The ZIP/package intentionally contains placeholders only.

See [README.md](README.md) for the full project overview and
[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common setup problems.
