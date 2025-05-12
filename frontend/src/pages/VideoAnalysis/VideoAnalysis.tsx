import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import styles from "./VideoAnalysis.module.css";
import api from "../../api/axios";
import { useAuthToken } from "../../utils/auth";

interface Comment {
  id: string;
  text: string;
  timestamp: number;
  author: string;
  createdAt: Date;
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

        // Fetch video details
        const detailsResponse = await api.get(`/api/v1/videos/${videoId}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        setVideoDetails(detailsResponse.data);

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
      } catch (err: any) {
        console.error("Error fetching video:", err);
        setError(err.response?.data?.detail || "Failed to load video");
      } finally {
        setIsLoading(false);
      }
    };

    fetchVideoDetails();
    // Only re-run when videoId changes, not when getToken changes
  }, [videoId]);

  const handleTimeUpdate = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    setCurrentTime(e.currentTarget.currentTime);
  };

  const handleAddComment = () => {
    if (!newComment.trim()) return;

    const comment: Comment = {
      id: Date.now().toString(),
      text: newComment,
      timestamp: currentTime,
      author: "Current User", // TODO: Replace with actual user name
      createdAt: new Date(),
    };

    setComments((prev) => [...prev, comment]);
    setNewComment("");
  };

  const formatTimestamp = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, "0")}`;
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

        <video
          className={styles.videoPlayer}
          controls
          onTimeUpdate={handleTimeUpdate}
        >
          <source src={videoUrl} type="video/mp4" />
          Your browser does not support the video tag.
        </video>
        <div className={styles.videoControls}>
          <button className={styles.controlButton}>Replay Last 10s</button>
          <button className={styles.controlButton}>Slow Motion (0.5x)</button>
          <button className={styles.controlButton}>Frame by Frame</button>
        </div>
      </div>

      <div className={styles.commentSection}>
        <h2>Comments</h2>
        <div className={styles.addComment}>
          <textarea
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            placeholder="Add a comment..."
            className={styles.commentInput}
          />
          <button
            onClick={handleAddComment}
            className={styles.addCommentButton}
          >
            Add Comment at {formatTimestamp(currentTime)}
          </button>
        </div>

        <div className={styles.commentList}>
          {comments.map((comment) => (
            <div key={comment.id} className={styles.commentItem}>
              <div className={styles.commentHeader}>
                <span className={styles.author}>{comment.author}</span>
                <span className={styles.timestamp}>
                  at {formatTimestamp(comment.timestamp)}
                </span>
              </div>
              <p className={styles.commentText}>{comment.text}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default VideoAnalysis;
