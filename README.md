# JHR Checker

A FastAPI web app for the classic computer-vision portion of an Adobe Stock technical pre-check. It checks resolution, file size, focus/blur, noise, exposure, contrast, saturation, white balance, chromatic aberration, and horizon tilt.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000. The API is available at `POST /api/check`.

This is a heuristic pre-check, not an Adobe acceptance guarantee. Logo, face, trademark, and other compliance checks are intentionally outside this first pass.
