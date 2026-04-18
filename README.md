# FaceIQ Windows App

This repository now contains a Windows-only desktop app split into two parts:

- `backend/`: a Python FastAPI service that extracts face landmarks and computes FaceIQ-style frontal and side-profile ratios from `research_Facial_Ratio.md`
- `flutter_app/`: a Flutter UI that lets the user pick a frontal photo and a side-profile photo, submit them to the Python backend, and review grouped metric results

## What is implemented

The backend currently supports the research metrics that have clear 2D formulas in the document, including:

- frontal thirds and width-height ratios
- eye, brow, nose, mouth, lip, jaw, and chin ratios that are explicitly defined
- profile forehead, convexity, nasal, nasolabial, nasomental, mentolabial, E-line, and S-line measurements

Metrics that the research guide marks as inferred, proprietary, or unreliable from plain 2D landmarks are returned in the API response as `unsupported_metrics`.

## Backend run

Recommended on Windows: use Python 3.11 for the virtual environment because MediaPipe wheel availability is typically better there than newer Python builds.

```powershell
.\scripts\start_backend.ps1
```

That script:

1. creates `.venv` if it does not exist
2. installs `backend/requirements.txt`
3. starts `uvicorn` on `http://127.0.0.1:8000`

## Flutter run

```powershell
.\scripts\start_flutter_windows.ps1
```

That script:

1. bootstraps the missing Windows Flutter runner with `flutter create --platforms=windows .` if needed
2. runs `flutter pub get`
3. launches the app on Windows

The Flutter UI expects the Python backend to already be running at `http://127.0.0.1:8000`, but the URL is editable inside the app.

## Local validation already done

- backend in-memory syntax validation
- backend synthetic metric validation via `python backend\validate_metrics.py`
- Flutter source-tree presence validation
- Flutter source ASCII validation

Because the local Flutter CLI hangs in this Codex environment, I validated the Flutter source statically instead of running `flutter pub get` or `flutter run` here.
