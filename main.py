import os
from dataclasses import asdict
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from stock_checker import run_checks

BASE_DIR = Path(__file__).parent
app = FastAPI(title="JHR Adobe Stock Checker", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/check")
async def check_image(image: UploadFile = File(...)):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(400, "Please upload an image file.")
    data = await image.read()
    if not data:
        raise HTTPException(400, "The uploaded file is empty.")
    suffix = Path(image.filename or "image.jpg").suffix or ".jpg"
    with NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        path = tmp.name
    try:
        report = run_checks(path)
        result = report.to_dict()
        result["file"] = image.filename or "image"
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    finally:
        os.unlink(path)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

@app.get("/")
def index():
    return FileResponse(BASE_DIR / "static" / "index.html")
