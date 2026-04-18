from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile

from .landmarks import FaceMeshExtractor, LandmarkExtractionError
from .research_metrics import analyze_face_pair


app = FastAPI(
    title="FaceIQ Labs Facial Ratio Analyzer",
    description="Windows backend that analyzes frontal and side-profile photos using the research_Facial_Ratio.md formulas.",
    version="0.1.0",
)

extractor = FaceMeshExtractor()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(
    front_image: UploadFile = File(..., description="Frontal face image"),
    side_image: UploadFile = File(..., description="Side profile image"),
) -> dict:
    try:
        front_bytes = await front_image.read()
        side_bytes = await side_image.read()
        front_face = extractor.extract(front_bytes, view="front")
        side_face = extractor.extract(side_bytes, view="side")
        return analyze_face_pair(front_face, side_face)
    except LandmarkExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive API boundary
        raise HTTPException(status_code=500, detail=f"Unexpected analysis failure: {exc}") from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
