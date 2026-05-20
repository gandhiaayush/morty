import importlib
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from database import init_db
from seed import seed_if_empty
from scheduler import start_scheduler, stop_scheduler
from schemas import router as schemas_router

_tool_modules = [
    "tools.crud",
    "tools.search",
    "tools.services",
    "tools.callbacks",
]

_loaded_routers = []
for _mod_name in _tool_modules:
    try:
        _mod = importlib.import_module(_mod_name)
        if hasattr(_mod, "router"):
            _loaded_routers.append(_mod.router)
    except ModuleNotFoundError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_if_empty()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Morty Tool Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for _router in _loaded_routers:
    app.include_router(_router, prefix="/tools")

app.include_router(schemas_router)


@app.get("/health")
def health():
    return {"status": "ok"}
