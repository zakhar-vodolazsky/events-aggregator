from fastapi import APIRouter, FastAPI

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    return {"status": "ok"}


app = FastAPI()
app.include_router(router)
