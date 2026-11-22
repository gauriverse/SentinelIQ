from fastapi import FastAPI


from app.api import auth
from app.core.config import settings

app = FastAPI(title=settings.app_name, version=settings.version)
app.include_router(auth.router)

@app.get("/health", tags=["system"])
def health() -> dict[str,str]:
    return {"status":"ok", "version": settings.version}