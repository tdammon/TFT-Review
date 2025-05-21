from .users import router as users_router
from .videos import router as videos_router
from .comments import router as comments_router
from .events import router as events_router
from .auth import router as auth_router
from .tft import router as tft_router

__all__ = ["users_router", "videos_router", "comments_router", "events_router", "auth_router", "tft_router"]
