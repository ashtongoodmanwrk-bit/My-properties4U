from fastapi import FastAPI

app = FastAPI(title="Property Management API")


@app.get("/health")
def health():
    return {"status": "ok"}
