# app//main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import report_router

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(report_router.router)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "backend is running"}
