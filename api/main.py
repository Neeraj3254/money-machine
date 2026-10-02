from fastapi import FastAPI


app = FastAPI(
    title="Money Machine API",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "system": "Money Machine",
        "status": "online",
        "version": "0.1.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }