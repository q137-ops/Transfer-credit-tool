from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.online_courses import router as online_courses_router


app = FastAPI(title="Transfer Master API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(online_courses_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
