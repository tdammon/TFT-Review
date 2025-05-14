from .users import router as users_router
from .videos import router as videos_router
from .comments import router as comments_router
from .events import router as events_router

__all__ = ["users_router", "videos_router", "comments_router", "events_router"]
