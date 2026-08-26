# RecoverAI Backend

FastAPI backend for AI Revenue Recovery Agent.

## Run locally
```
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Deploy on Render
1. Push this repo to GitHub.
2. Go to https://render.com -> New -> Web Service -> connect this repo.
3. Render auto-detects `render.yaml`. Click Deploy.
4. Your API will be live at `https://<your-app>.onrender.com`

## Endpoints
- POST /events/payment-failed
- POST /recovery/analyze?case_id=
- POST /recovery/plan?case_id=
- POST /recovery/execute
- POST /recovery/verify
- POST /review/{case_id}
- GET /recovery/cases
- GET /recovery/cases/{case_id}
- GET /recovery/metrics
- GET /audit
