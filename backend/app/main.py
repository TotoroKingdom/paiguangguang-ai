from fastapi import FastAPI

app = FastAPI(title="Paiguangguang Health Service", docs_url=None, redoc_url=None)


@app.get("/api/v1/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
