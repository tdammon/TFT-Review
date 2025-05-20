import React, { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import styles from "./VideoAnalysis.module.css";
import api from "../../api/axios";
import { useAuthToken } from "../../utils/auth";
import { CommentIcon } from "../../components/Icons/CommentIcon";
import { FullscreenIcon } from "../../components/Icons/FullScreenIcon";
import { ExitFullscreenIcon } from "../../components/Icons/ExitFullScreenIcon";
import CommentsIcon from "../../components/Icons/CommentsIcon";
import AdminIcon from "../../components/Icons/AdminIcon";
import DetailsIcon from "../../components/Icons/DetailsIcon";
import Tooltip from "../../components/Tooltip/Tooltip";
import InfoIcon from "../../components/Icons/InfoIcon";

// Types
import {
  Comment,
  Event,
  User,
  VideoDetails,
} from "../../types/serverResponseTypes";

// Define sidebar tab types
type SidebarTab = "Comments" | "Admin" | "Details" | "Info";

const VideoAnalysis = ({ userInfo }: { userInfo: User | null }) => {
  const { videoId } = useParams<{ videoId: string }>();
  const [comments, setComments] = useState<Comment[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [newComment, setNewComment] = useState("");
  const [currentTime, setCurrentTime] = useState(0);
  const [videoDuration, setVideoDuration] = useState(0);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoDetails, setVideoDetails] = useState<VideoDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submittingComment, setSubmittingComment] = useState(false);
  const [showCommentInput, setShowCommentInput] = useState(false);
  const [commentTimestamp, setCommentTimestamp] = useState(0);
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [activeTab, setActiveTab] = useState<SidebarTab>("Comments");
  const [hoveredEvent, setHoveredEvent] = useState<Event | null>(null);
  const [activeEventId, setActiveEventId] = useState<string | null>(null);
  const [isCommentInputFocused, setIsCommentInputFocused] = useState(false);
  const [focusedTimestamp, setFocusedTimestamp] = useState(0);
  const videoRef = useRef<HTMLVideoElement>(null);
  const videoContainerRef = useRef<HTMLDivElement>(null);
  const timelineRef = useRef<HTMLDivElement>(null);
  const commentInputRef = useRef<HTMLTextAreaElement>(null);
  const { getToken } = useAuthToken();
  const [isVideoOwner, setIsVideoOwner] = useState(false);
  const [replyingTo, setReplyingTo] = useState<{
    id: string;
    type: "comment" | "event";
    username: string;
  } | null>(null);

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

        const detailsResponse = await api.get(`/api/v1/videos/${videoId}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        setVideoDetails(detailsResponse.data);

        if (detailsResponse.data.comments) {
          setComments(detailsResponse.data.comments);
        }

        if (detailsResponse.data.events) {
          setEvents(detailsResponse.data.events);
        }

        const streamResponse = await api.get(
          `/api/v1/videos/${videoId}/stream`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        setVideoUrl(streamResponse.data.url);

        // Check if current user is the video owner
        if (userInfo && detailsResponse.data.user_id === userInfo.id) {
          setIsVideoOwner(true);
        }
      } catch (err: any) {
        console.error("Error fetching video:", err);
        setError(err.response?.data?.detail || "Failed to load video");
      } finally {
        setIsLoading(false);
      }
    };

    fetchVideoDetails();
  }, [videoId, userInfo]);

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
    const currentTime = e.currentTarget.currentTime;
    setCurrentTime(currentTime);

    // Find the active event based on the current timestamp
    // An event is active if the video is playing within 2 seconds after its timestamp
    const activeEvent = events.find(
      (event) =>
        currentTime >= event.video_timestamp &&
        currentTime < event.video_timestamp + 2
    );

    setActiveEventId(activeEvent?.id || null);
  };

  const handleLoadedMetadata = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    setVideoDuration(e.currentTarget.duration);
  };

  const handleAddCommentClick = () => {
    // Store the current timestamp when the button is clicked
    if (videoRef.current) {
      const currentVideoTime = videoRef.current.currentTime;
      setCommentTimestamp(currentVideoTime);
      setFocusedTimestamp(currentVideoTime);
      setIsCommentInputFocused(true);
      setShowCommentInput(true);
      // Switch to comments tab when adding a comment
      setActiveTab("Comments");

      setTimeout(() => {
        if (commentInputRef.current) {
          commentInputRef.current.focus();
        }
      }, 100);
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

      // Use focusedTimestamp if the input is focused, otherwise use commentTimestamp
      // REVISIT THIS: Do we actually need two timestamps?
      const timestampToUse = isCommentInputFocused
        ? focusedTimestamp
        : commentTimestamp;

      const response = await api.post(
        "/api/v1/comments/",
        {
          content: newComment,
          video_id: videoId,
          parent_id: null,
          video_timestamp: timestampToUse,
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
      setIsCommentInputFocused(false);
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
    setIsCommentInputFocused(false);
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

  const handleEventMarkerClick = (event: Event) => {
    jumpToTimestamp(event.video_timestamp);
  };

  const handleEventMarkerHover = (event: Event | null) => {
    setHoveredEvent(event);
  };

  // Function to switch between tabs
  const handleTabChange = (tab: SidebarTab) => {
    // If switching away from Comments tab and there's a comment in progress, clear it
    if (activeTab === "Comments" && tab !== "Comments" && newComment.trim()) {
      if (window.confirm("You have an unsaved comment. Switch tabs anyway?")) {
        setNewComment("");
        setActiveTab(tab);
      }
    } else {
      setActiveTab(tab);
    }
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

  // Determine which secondary tab to show based on authentication and ownership
  const secondaryTabName = isVideoOwner ? "Admin" : "Details";
  const showSecondaryTab = userInfo !== null; // Only show secondary tab if user is authenticated

  return (
    <div className={styles.container}>
      {/* Sidebar - Only shown when not in fullscreen */}
      {!isFullScreen && (
        <div className={styles.sidebar}>
          {/* Sidebar Tabs */}
          <div className={styles.sidebarTabs}>
            <Tooltip text="Comments & Events" position="bottom">
              <button
                className={`${styles.tabButton} ${
                  activeTab === "Comments" ? styles.activeTab : ""
                }`}
                onClick={() => handleTabChange("Comments")}
                aria-label="Comments & Events"
              >
                <CommentsIcon
                  stroke={activeTab === "Comments" ? "#4a90e2" : "#ccc"}
                />
              </button>
            </Tooltip>

            {showSecondaryTab && (
              <Tooltip text={secondaryTabName} position="bottom">
                <button
                  className={`${styles.tabButton} ${
                    activeTab === secondaryTabName ? styles.activeTab : ""
                  }`}
                  onClick={() => handleTabChange(secondaryTabName)}
                  aria-label={secondaryTabName}
                >
                  {secondaryTabName === "Admin" ? (
                    <AdminIcon
                      stroke={activeTab === "Admin" ? "#4a90e2" : "#ccc"}
                    />
                  ) : (
                    <DetailsIcon
                      stroke={activeTab === "Details" ? "#4a90e2" : "#ccc"}
                    />
                  )}
                </button>
              </Tooltip>
            )}

            <Tooltip text="Video Info" position="bottom">
              <button
                className={`${styles.tabButton} ${
                  activeTab === "Info" ? styles.activeTab : ""
                }`}
                onClick={() => handleTabChange("Info")}
                aria-label="Video Info"
              >
                <InfoIcon stroke={activeTab === "Info" ? "#4a90e2" : "#ccc"} />
              </button>
            </Tooltip>
          </div>

          {/* Tab Content */}
          <div className={styles.tabContent}>
            {/* Comments Tab */}
            {activeTab === "Comments" && (
              <div className={styles.commentsTab}>
                <h2>Comments & Events</h2>

                <div className={styles.commentList}>
                  {/* Combine and sort comments and events chronologically */}
                  {[
                    ...comments,
                    ...events.map((event) => ({
                      id: event.id,
                      isEvent: true,
                      event: event,
                      video_timestamp: event.video_timestamp,
                      created_at: event.created_at,
                    })),
                  ]
                    .sort((a, b) => {
                      // Sort by timestamp first if available
                      if (a.video_timestamp && b.video_timestamp) {
                        return a.video_timestamp - b.video_timestamp;
                      }
                      // Fall back to created_at date
                      return (
                        new Date(a.created_at).getTime() -
                        new Date(b.created_at).getTime()
                      );
                    })
                    .map((item) =>
                      "isEvent" in item ? (
                        // Render event
                        <div
                          key={`event-${item.id}`}
                          className={`${styles.eventItem} ${
                            activeEventId === item.event.id
                              ? styles.activeEventItem
                              : ""
                          }`}
                          onClick={() =>
                            jumpToTimestamp(item.event.video_timestamp)
                          }
                        >
                          <div className={styles.eventInfo}>
                            <span className={styles.eventTitle}>
                              {item.event.title}
                            </span>
                            <button
                              className={styles.timestampButton}
                              onClick={(e) => {
                                e.stopPropagation(); // Prevent triggering the parent onClick
                                jumpToTimestamp(item.event.video_timestamp);
                              }}
                            >
                              {formatTimestamp(item.event.video_timestamp)}
                            </button>
                          </div>
                          {item.event.description && (
                            <p className={styles.eventDescription}>
                              {item.event.description}
                            </p>
                          )}
                          <div className={styles.eventMeta}>
                            <span className={styles.eventLabel}>
                              Key Moment
                            </span>
                            {item.event.event_type && (
                              <span className={styles.eventType}>
                                {item.event.event_type.replace("_", " ")}
                              </span>
                            )}
                            <span className={styles.eventAuthor}>
                              by {item.event.user_username}
                            </span>
                          </div>
                        </div>
                      ) : (
                        // Render comment
                        <div
                          key={`comment-${item.id}`}
                          className={styles.commentItem}
                          onClick={() =>
                            item.video_timestamp !== null &&
                            jumpToTimestamp(item.video_timestamp)
                          }
                        >
                          <div className={styles.commentHeader}>
                            <span className={styles.author}>
                              {item.user_username}
                            </span>
                            {item.video_timestamp !== null && (
                              <button
                                className={styles.timestampButton}
                                onClick={(e) => {
                                  e.stopPropagation(); // Prevent triggering the parent onClick
                                  jumpToTimestamp(item.video_timestamp);
                                }}
                              >
                                at {formatTimestamp(item.video_timestamp)}
                              </button>
                            )}
                          </div>
                          <p className={styles.commentText}>{item.content}</p>
                        </div>
                      )
                    )}

                  {comments.length === 0 && events.length === 0 && (
                    <div className={styles.noComments}>
                      No comments or events yet
                    </div>
                  )}
                </div>

                {/* Permanent Comment Form */}
                {userInfo && (
                  <div className={styles.permanentCommentForm}>
                    <div className={styles.permanentCommentHeader}>
                      <span>
                        Add comment at{" "}
                        {isCommentInputFocused
                          ? formatTimestamp(focusedTimestamp)
                          : formatTimestamp(currentTime)}
                      </span>
                      <button
                        onClick={handleAddComment}
                        className={styles.addCommentButton}
                        disabled={submittingComment || !newComment.trim()}
                      >
                        {submittingComment ? "Adding..." : "Add Comment"}
                      </button>
                    </div>
                    <textarea
                      value={newComment}
                      onChange={(e) => setNewComment(e.target.value)}
                      placeholder="Add your comment..."
                      className={styles.commentInput}
                      ref={commentInputRef}
                      onFocus={() => {
                        if (!isCommentInputFocused) {
                          setFocusedTimestamp(currentTime);
                          setIsCommentInputFocused(true);
                        }
                      }}
                      onBlur={() => {
                        if (!newComment.trim()) {
                          setIsCommentInputFocused(false);
                        }
                      }}
                    />
                  </div>
                )}
              </div>
            )}

            {/* Info Tab */}
            {activeTab === "Info" && videoDetails && (
              <div className={styles.infoTab}>
                <h2>Video Information</h2>
                <div className={styles.videoDetailInfo}>
                  <div className={styles.detailItem}>
                    <h3>Title</h3>
                    <p>{videoDetails.title}</p>
                  </div>

                  {videoDetails.description && (
                    <div className={styles.detailItem}>
                      <h3>Description</h3>
                      <p>{videoDetails.description}</p>
                    </div>
                  )}

                  <div className={styles.detailItem}>
                    <h3>Statistics</h3>
                    <div className={styles.detailStats}>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>Views:</span>
                        <span className={styles.statValue}>
                          {videoDetails.views}
                        </span>
                      </div>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>Uploaded:</span>
                        <span className={styles.statValue}>
                          {new Date(
                            videoDetails.created_at
                          ).toLocaleDateString()}
                        </span>
                      </div>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>Comments:</span>
                        <span className={styles.statValue}>
                          {comments.length}
                        </span>
                      </div>
                      <div className={styles.statItem}>
                        <span className={styles.statLabel}>Events:</span>
                        <span className={styles.statValue}>
                          {events.length}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Admin Tab - Only for video owners */}
            {activeTab === "Admin" && isVideoOwner && (
              <div className={styles.adminTab}>
                <h2>Video Management</h2>
                <div className={styles.adminSection}>
                  <h3>Video Settings</h3>
                  <div className={styles.adminControls}>
                    <button className={styles.editButton}>
                      Edit Video Details
                    </button>
                    <button
                      className={styles.deleteButton}
                      onClick={() => {
                        if (
                          window.confirm(
                            "Are you sure you want to delete this video? This action cannot be undone."
                          )
                        ) {
                          // Handle delete video
                          console.log("Delete video:", videoId);
                        }
                      }}
                    >
                      Delete Video
                    </button>
                  </div>
                </div>

                <div className={styles.adminSection}>
                  <h3>Analytics</h3>
                  <div className={styles.analyticsInfo}>
                    <div className={styles.analyticItem}>
                      <span className={styles.analyticLabel}>Total Views:</span>
                      <span className={styles.analyticValue}>
                        {videoDetails?.views || 0}
                      </span>
                    </div>
                    <div className={styles.analyticItem}>
                      <span className={styles.analyticLabel}>Comments:</span>
                      <span className={styles.analyticValue}>
                        {comments.length}
                      </span>
                    </div>
                    <div className={styles.analyticItem}>
                      <span className={styles.analyticLabel}>Events:</span>
                      <span className={styles.analyticValue}>
                        {events.length}
                      </span>
                    </div>
                    <div className={styles.analyticItem}>
                      <span className={styles.analyticLabel}>Uploaded:</span>
                      <span className={styles.analyticValue}>
                        {videoDetails?.created_at
                          ? new Date(
                              videoDetails.created_at
                            ).toLocaleDateString()
                          : "Unknown"}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Details Tab - For authenticated non-owners */}
            {activeTab === "Details" && userInfo && !isVideoOwner && (
              <div className={styles.detailsTab}>
                <h2>Video Details</h2>
                {videoDetails && (
                  <div className={styles.videoDetailInfo}>
                    <div className={styles.detailItem}>
                      <h3>Title</h3>
                      <p>{videoDetails.title}</p>
                    </div>

                    {videoDetails.description && (
                      <div className={styles.detailItem}>
                        <h3>Description</h3>
                        <p>{videoDetails.description}</p>
                      </div>
                    )}

                    <div className={styles.detailItem}>
                      <h3>Statistics</h3>
                      <div className={styles.detailStats}>
                        <div className={styles.statItem}>
                          <span className={styles.statLabel}>Views:</span>
                          <span className={styles.statValue}>
                            {videoDetails.views}
                          </span>
                        </div>
                        <div className={styles.statItem}>
                          <span className={styles.statLabel}>Comments:</span>
                          <span className={styles.statValue}>
                            {comments.length}
                          </span>
                        </div>
                        <div className={styles.statItem}>
                          <span className={styles.statLabel}>Events:</span>
                          <span className={styles.statValue}>
                            {events.length}
                          </span>
                        </div>
                        <div className={styles.statItem}>
                          <span className={styles.statLabel}>Uploaded:</span>
                          <span className={styles.statValue}>
                            {new Date(
                              videoDetails.created_at
                            ).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main Video Content */}
      <div className={styles.mainContent}>
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
            onLoadedMetadata={handleLoadedMetadata}
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

          {/* Event Markers Timeline */}
          {videoDuration > 0 && (
            <div className={styles.eventMarkersContainer} ref={timelineRef}>
              {events.map((event) => {
                const position = (event.video_timestamp / videoDuration) * 100;
                return (
                  <div
                    key={event.id}
                    className={styles.eventMarker}
                    style={{ left: `${position}%` }}
                    onClick={() => handleEventMarkerClick(event)}
                    onMouseEnter={() => handleEventMarkerHover(event)}
                    onMouseLeave={() => handleEventMarkerHover(null)}
                    title={event.title}
                  />
                );
              })}
              {hoveredEvent && (
                <div
                  className={styles.eventTooltip}
                  style={{
                    left: `${
                      (hoveredEvent.video_timestamp / videoDuration) * 100
                    }%`,
                  }}
                >
                  <div className={styles.eventTooltipTitle}>
                    {hoveredEvent.title}
                  </div>
                  {hoveredEvent.event_type && (
                    <div className={styles.eventTooltipType}>
                      {hoveredEvent.event_type.replace("_", " ")}
                    </div>
                  )}
                  {hoveredEvent.description && (
                    <div className={styles.eventTooltipDescription}>
                      {hoveredEvent.description}
                    </div>
                  )}
                  <div className={styles.eventTooltipTime}>
                    {formatTimestamp(hoveredEvent.video_timestamp)}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Add Comment Button Overlay - Only visible for authenticated users */}
          {userInfo && (
            <button
              className={styles.addCommentOverlay}
              onClick={handleAddCommentClick}
              title="Add comment at this timestamp"
            >
              <CommentIcon />
            </button>
          )}

          {/* Inline Comment Input - Only appears in fullscreen mode and for authenticated users */}
          {isFullScreen && userInfo && showCommentInput && (
            <div
              className={styles.commentOverlay}
              onClick={handleCommentOverlayClick}
            >
              <div className={styles.inlineCommentHeader}>
                Add at{" "}
                {formatTimestamp(
                  isCommentInputFocused ? focusedTimestamp : commentTimestamp
                )}
              </div>
              <textarea
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                placeholder="Add your comment..."
                className={styles.inlineCommentInput}
                autoFocus
                onFocus={() => {
                  if (!isCommentInputFocused) {
                    setFocusedTimestamp(commentTimestamp);
                    setIsCommentInputFocused(true);
                  }
                }}
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
    </div>
  );
};

export default VideoAnalysis;
