from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from ..db.database import get_db
from ..models.comment import Comment, validate_comment_data
from ..models.user import User
from ..models.video import Video
from ..models.event import Event
from ..schemas.comment import CommentCreate, CommentUpdate, CommentResponse
from ..auth import get_current_user

router = APIRouter(
    prefix="/comments", 
    tags=["comments"]
)

@router.get("/{video_id}", response_model=List[CommentResponse])
async def get_comments(
    video_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get all comments for a video"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    comments = db.query(Comment).filter(Comment.video_id == video_id).order_by(Comment.created_at.desc()).all()
    return comments

@router.get("/event/{event_id}", response_model=List[CommentResponse])
async def get_comments_by_event(
    event_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get all comments for a specific event"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    comments = db.query(Comment).filter(Comment.event_id == event_id).order_by(Comment.created_at.desc()).all()
    return comments

@router.post("/", response_model=CommentResponse)
async def create_comment(
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new comment on a video"""
    try:
        # Validate based on our business rules
        validated_data = validate_comment_data(
            parent_id=comment_data.parent_id,
            video_timestamp=comment_data.video_timestamp,
            event_id=comment_data.event_id
        )
        
        # Update the data with validated values
        comment_data.parent_id = validated_data["parent_id"]
        comment_data.video_timestamp = validated_data["video_timestamp"]
        comment_data.event_id = validated_data["event_id"]
        
        # Verify video exists
        video = db.query(Video).filter(Video.id == comment_data.video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # If event_id is provided, verify it exists and belongs to the same video
        if comment_data.event_id:
            event = db.query(Event).filter(Event.id == comment_data.event_id).first()
            if not event:
                raise HTTPException(status_code=404, detail="Event not found")
            if event.video_id != comment_data.video_id:
                raise HTTPException(status_code=400, detail="Event does not belong to this video")
        
        # Create comment
        comment = Comment(
            content=comment_data.content,
            user_id=current_user.id,
            user_username=current_user.username,
            video_id=comment_data.video_id,
            parent_id=comment_data.parent_id,
            video_timestamp=comment_data.video_timestamp,
            event_id=comment_data.event_id,
        )
        
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return comment
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: uuid.UUID,
    comment_data: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a comment"""
    # Verify comment exists
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Verify user is the owner of the comment
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized to update this comment")
    
    # Update comment
    for key, value in comment_data.dict(exclude_unset=True).items():
        setattr(comment, key, value)
        
    db.commit() 
    db.refresh(comment)
    return comment

@router.delete("/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a comment"""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Verify user is the owner of the comment
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized to delete this comment")
    
    db.delete(comment)
    db.commit()
    return {"message": "Comment deleted successfully"}