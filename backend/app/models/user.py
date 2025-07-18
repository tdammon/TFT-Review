from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.dialects.postgresql import UUID
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .video import Video
    from .comment import Comment
    from .event import Event
from .base import Base


class User(Base):
    """
    User model for storing user information and authentication details.

    Attributes:
        id (UUID): Primary key for the user
        auth0_id (str): Unique identifier from Auth0
        email (str): User's email address
        video (List[Video]): List of videos uploaded by the user
        comments (List[Comment]): List of comments made by the user
        riot_id (str): Riot ID for the user
        riot_puuid (str): Permanent User ID from Riot
        riot_account_name (str): Riot account name (e.g., "Summoner")
        riot_account_tag (str): Riot account tag (e.g., "NA1")
        riot_region (str): Riot account region
        riot_access_token (str): OAuth access token for Riot API
        riot_refresh_token (str): OAuth refresh token for Riot API
        verified_riot_account (bool): Indicates if the user has verified their Riot account
        discord_id (str): Discord user ID
        discord_username (str): Discord username
        discord_connected (bool): Indicates if Discord account is connected
    """

    id: Mapped[str] = Column(UUID(as_uuid=True), primary_key=True, index=True, default=Base.generate_uuid)
    auth0_id: Mapped[str] = Column(String(100), unique=True, index=True, nullable=False)
    email: Mapped[str] = Column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = Column(String(50), unique=True, index=True, nullable=True)
    profile_picture: Mapped[str] = Column(String, nullable=True)
    
    # Riot integration
    riot_id: Mapped[str] = Column(String(100), unique=True, index=True, nullable=True)
    riot_puuid: Mapped[str] = Column(String(100), unique=True, index=True, nullable=True)
    riot_account_name: Mapped[str] = Column(String(100), nullable=True)
    riot_account_tag: Mapped[str] = Column(String(20), nullable=True)
    riot_region: Mapped[str] = Column(String(10), nullable=True)
    riot_access_token: Mapped[str] = Column(String(2000), nullable=True)
    riot_refresh_token: Mapped[str] = Column(String(2000), nullable=True)
    verified_riot_account: Mapped[bool] = Column(Boolean, default=False)
    
    # Discord integration
    discord_id: Mapped[str] = Column(String(100), unique=True, index=True, nullable=True)
    discord_username: Mapped[str] = Column(String(100), nullable=True)
    discord_connected: Mapped[bool] = Column(Boolean, default=False)

    videos: Mapped[List["Video"]] = relationship("Video", back_populates="user")
    comments: Mapped[List["Comment"]] = relationship("Comment", back_populates="user")
    events: Mapped[List["Event"]] = relationship("Event", back_populates="user")