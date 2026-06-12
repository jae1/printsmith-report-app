from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import endpoints, views

def create_app() -> FastAPI:
    app = FastAPI(title="PrintSmith Report App")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(views.router)
    app.include_router(endpoints.router)

    return app

app = create_app()
