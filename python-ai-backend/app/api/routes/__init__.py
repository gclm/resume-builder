# author: jf
"""Route registry for FastAPI."""

from app.api.routes.audio_routes import router as audio_router
from app.api.routes.chat_routes import router as chat_router
from app.api.routes.interview_routes import router as interview_router
from app.api.routes.rag_routes import router as rag_router
from app.api.routes.realtime_routes import router as realtime_router

ALL_ROUTERS = (chat_router, rag_router, interview_router, audio_router, realtime_router)

__all__ = [
    "ALL_ROUTERS",
    "chat_router",
    "rag_router",
    "interview_router",
    "audio_router",
    "realtime_router",
]
