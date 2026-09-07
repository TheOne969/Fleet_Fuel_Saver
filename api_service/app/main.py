import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import alerts, history, fleet

app = FastAPI(title="Fleet API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alerts.router)
app.include_router(history.router)
app.include_router(fleet.router)

@app.get("/health")
def health():
    return {"status": "ok"}

