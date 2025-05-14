import React, { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import styles from "./VideoAnalysis.module.css";
import api from "../../api/axios";
import { useAuthToken } from "../../utils/auth";
import { CommentIcon } from "../../components/Icons/CommentIcon";
import { FullscreenIcon } from "../../components/Icons/FullScreenIcon";
import { ExitFullscreenIcon } from "../../components/Icons/ExitFullScreenIcon";

interface Comment {
  id: number;
  content: string;
  video_timestamp: number;
  user_username: string;
  user_profile_picture?: string;
  created_at: string;
  updated_at: string;
  parent_id?: number;
}

interface VideoDetails {
  id: number;
  title: string;
  description: string | null;
  video_url: string | null;
  thumbnail_url: string | null;
  views: number;
  user_id: number;
  created_at: string;
  comments: Comment[];
}

const VideoAnalysis = () => {
  const { videoId } = useParams<{ videoId: string }>();
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState("");
  const [currentTime, setCurrentTime] = useState(0);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoDetails, setVideoDetails] = useState<VideoDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submittingComment, setSubmittingComment] = useState(false);
  const [showCommentInput, setShowCommentInput] = useState(false);
  const [commentTimestamp, setCommentTimestamp] = useState(0);
  const [isFullScreen, setIsFullScreen] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const videoContainerRef = useRef<HTMLDivElement>(null);
  const { getToken } = useAuthToken();

  useEffect(() => {
    const fetchVideoDetails = async () => {
      if (!videoId) return;

      try {
        setIsLoading(true);
        setError(null);

        const token = await getToken();
        if (!token) {
          throw new Error("Authentication failed");
        }

        // Fetch video details (now includes comments)
        const detailsResponse = await api.get(`/api/v1/videos/${videoId}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        setVideoDetails(detailsResponse.data);

        // Set comments from the video details response
        if (detailsResponse.data.comments) {
          setComments(detailsResponse.data.comments);
        }

        // Fetch streaming URL
        const streamResponse = await api.get(
          `/api/v1/videos/${videoId}/stream`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        setVideoUrl(streamResponse.data.url);

        // No need to fetch comments separately anymore
        // Comments are now included in the video details response
      } catch (err: any) {
        console.error("Error fetching video:", err);
        setError(err.response?.data?.detail || "Failed to load video");
      } finally {
        setIsLoading(false);
      }
    };

    fetchVideoDetails();
  }, [videoId]);

  // Handle fullscreen changes
  useEffect(() => {
    const handleFullScreenChange = () => {
      const isDocFullScreen = document.fullscreenElement !== null;
      setIsFullScreen(isDocFullScreen);
    };

    document.addEventListener("fullscreenchange", handleFullScreenChange);

    return () => {
      document.removeEventListener("fullscreenchange", handleFullScreenChange);
    };
  }, []);

  const handleTimeUpdate = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    setCurrentTime(e.currentTarget.currentTime);
  };

  const handleAddCommentClick = () => {
    // Store the current timestamp when the button is clicked
    if (videoRef.current) {
      setCommentTimestamp(videoRef.current.currentTime);
      setShowCommentInput(true);
    }
  };

  const toggleFullScreen = () => {
    if (!videoContainerRef.current) return;

    if (!document.fullscreenElement) {
      // Enter fullscreen
      videoContainerRef.current.requestFullscreen().catch((err) => {
        console.error(`Error attempting to enable fullscreen: ${err.message}`);
      });
    } else {
      // Exit fullscreen
      document.exitFullscreen().catch((err) => {
        console.error(`Error exiting fullscreen: ${err.message}`);
      });
    }
  };

  const handleAddComment = async () => {
    if (!newComment.trim() || !videoId) return;

    try {
      setSubmittingComment(true);

      const token = await getToken();
      if (!token) {
        throw new Error("Authentication failed");
      }

      const response = await api.post(
        "/api/v1/comments/",
        {
          content: newComment,
          video_id: parseInt(videoId),
          parent_id: null, // This is a top-level comment
          video_timestamp: commentTimestamp,
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      // Add the new comment to the list
      const newCommentData = response.data;
      setComments((prev) => [newCommentData, ...prev]);

      // Also update the comments in videoDetails if it exists
      if (videoDetails && videoDetails.comments) {
        setVideoDetails({
          ...videoDetails,
          comments: [newCommentData, ...videoDetails.comments],
        });
      }

      setNewComment("");
      setShowCommentInput(false);
    } catch (err: any) {
      console.error("Error adding comment:", err);
      alert(
        err.response?.data?.detail || "Failed to add comment. Please try again."
      );
    } finally {
      setSubmittingComment(false);
    }
  };

  const handleCancelComment = () => {
    setNewComment("");
    setShowCommentInput(false);
  };

  const formatTimestamp = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, "0")}`;
  };

  const jumpToTimestamp = (timestamp: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = timestamp;
      videoRef.current.pause();
    }
  };

  const handleCommentOverlayClick = (e: React.MouseEvent) => {
    // Prevent clicks on the comment overlay from propagating to the video
    e.stopPropagation();
  };

  if (isLoading) {
    return <div className={styles.loading}>Loading video...</div>;
  }

  if (error) {
    return <div className={styles.error}>{error}</div>;
  }

  if (!videoUrl) {
    return <div className={styles.error}>Video not available</div>;
  }

  return (
    <div className={styles.container}>
      <div className={styles.videoSection}>
        {videoDetails && (
          <div className={styles.videoHeader}>
            <h1>{videoDetails.title}</h1>
            {videoDetails.description && <p>{videoDetails.description}</p>}
            <div className={styles.videoMeta}>
              <span>{videoDetails.views} views</span>
              <span>
                Uploaded on{" "}
                {new Date(videoDetails.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>
        )}

        <div
          ref={videoContainerRef}
          className={`${styles.videoPlayerContainer} ${
            isFullScreen ? styles.fullscreenContainer : ""
          }`}
        >
          <video
            ref={videoRef}
            className={styles.videoPlayer}
            controls
            controlsList="nodownload nofullscreen"
            disablePictureInPicture
            onTimeUpdate={handleTimeUpdate}
          >
            <source src={videoUrl} type="video/mp4" />
            Your browser does not support the video tag.
          </video>

          {/* Custom Video Controls Overlay */}
          <div className={styles.customControls}>
            <button
              className={styles.fullscreenButton}
              onClick={toggleFullScreen}
              title={isFullScreen ? "Exit fullscreen" : "Enter fullscreen"}
            >
              {isFullScreen ? <ExitFullscreenIcon /> : <FullscreenIcon />}
              <span className={styles.buttonText}>
                {isFullScreen ? "Exit Fullscreen" : "Fullscreen"}
              </span>
            </button>
          </div>

          {/* Add Comment Button Overlay - Always visible */}
          <button
            className={styles.addCommentOverlay}
            onClick={handleAddCommentClick}
            title="Add comment at this timestamp"
          >
            <CommentIcon />
          </button>

          {/* Inline Comment Input - Appears directly in the video player */}
          {showCommentInput && (
            <div
              className={styles.commentOverlay}
              onClick={handleCommentOverlayClick}
            >
              <div className={styles.inlineCommentHeader}>
                Add at {formatTimestamp(commentTimestamp)}
              </div>
              <textarea
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                placeholder="Add your comment..."
                className={styles.inlineCommentInput}
                autoFocus
              />
              <div className={styles.inlineCommentActions}>
                <button
                  onClick={handleCancelComment}
                  className={styles.inlineCancelButton}
                  disabled={submittingComment}
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddComment}
                  className={styles.inlineAddButton}
                  disabled={submittingComment || !newComment.trim()}
                >
                  {submittingComment ? "Adding..." : "Add"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Comment section - Only shown when not in fullscreen */}
      {!isFullScreen && (
        <div className={styles.commentSection}>
          <h2>Comments</h2>

          <div className={styles.commentList}>
            {comments.map((comment) => (
              <div key={comment.id} className={styles.commentItem}>
                <div className={styles.commentHeader}>
                  <span className={styles.author}>{comment.user_username}</span>
                  {comment.video_timestamp !== null && (
                    <button
                      className={styles.timestampButton}
                      onClick={() => jumpToTimestamp(comment.video_timestamp)}
                    >
                      at {formatTimestamp(comment.video_timestamp)}
                    </button>
                  )}
                </div>
                <p className={styles.commentText}>{comment.content}</p>
              </div>
            ))}
            {comments.length === 0 && (
              <div className={styles.noComments}>No comments yet</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default VideoAnalysis;
