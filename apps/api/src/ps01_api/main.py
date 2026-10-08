from fastapi import FastAPI

app = FastAPI(
    title="PS-01 Secure Knowledge API",
    version="0.1.0",
    description="Authenticated API for a multi-modal knowledge workspace.",
)


@app.get("/health", tags=["operations"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
