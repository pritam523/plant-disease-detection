# Troubleshooting

## Model fails to load

Run:

```bash
python run.py check
```

Confirm that `model/trained_model.keras` exists and that `MODEL_PATH` in `.env`
is either empty or points to that file. If the file is missing, re-clone the
repository or restore the model from a backup.

## Port 8000 is already in use

Change `APP_PORT` in `.env` to another free port, then restart the app. Remember
to open the new URL in your browser.

## TensorFlow installation is slow or fails

Use Python 3.12 and install from the canonical requirements file:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The project pins `tensorflow-cpu==2.20.0`; a GPU is not required.

## API keys are not working

- Keys are read only at startup, so restart the server after editing `.env`.
- Leave a key empty to disable that optional service.
- Check that `.env` exists and is in the project root.
- Never paste keys into issues, screenshots, or commits.

## Admin login fails

Generate a fresh password hash:

```bash
python run.py hash-password
```

Paste the printed value into `.env` as `ADMIN_PASSWORD_HASH`, restart the app,
and also replace `ADMIN_SECRET_KEY` with a long random string.

## History or images disappear after restart

Runtime data lives in `data/`. This folder is intentionally ignored by Git, but
it should remain on your local machine. Deleting it removes the SQLite database
and saved uploads.

## Tests fail on a new machine

1. Confirm Python 3.12 is active.
2. Confirm dependencies are installed from `requirements.txt`.
3. Confirm the model and reference JSON files are present.
4. Run the tests with verbose output:

   ```bash
   python -m unittest discover -s tests -v
   ```

## Large model file warning from Git

`model/trained_model.keras` is about 90 MB. GitHub accepts it, but recommends
Git LFS for files over 50 MB. The warning is informational; pushes still work.
If you fork the project and want LFS, configure it before adding the model file.
