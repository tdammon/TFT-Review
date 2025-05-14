import React, { useState, useRef, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuthToken } from "../../utils/auth";
import api from "../../api/axios";
import styles from "./EventCreation.module.css";

interface Event {
  id: string;
  title: string;
  video_timestamp: number;
}

const EventCreation: React.FC = () => {
  const { videoId } = useParams<{ videoId: string }>();
  const navigate = useNavigate();
  const { getToken } = useAuthToken();
  const videoRef = useRef<HTMLVideoElement>(null);

  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoTitle, setVideoTitle] = useState("");
  const [currentTime, setCurrentTime] = useState(0);
  const [eventTitle, setEventTitle] = useState("");
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [addingEvent, setAddingEvent] = useState(false);

  useEffect(() => {
    const fetchVideoDetails = async () => {
      if (!videoId) return;

      try {
        setLoading(true);
        setError("");

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

        setVideoTitle(detailsResponse.data.title);

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

        // Fetch existing events if any
        const eventsResponse = await api.get(`/api/v1/events/${videoId}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        setEvents(eventsResponse.data);
      } catch (err: any) {
        console.error("Error fetching video:", err);
        setError(err.response?.data?.detail || "Failed to load video");
      } finally {
        setLoading(false);
      }
    };

    fetchVideoDetails();
  }, [videoId]);

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const formatTimestamp = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, "0")}`;
  };

  const handleAddEvent = async () => {
    if (!eventTitle.trim() || !videoId) return;

    try {
      setAddingEvent(true);

      const token = await getToken();
      if (!token) {
        throw new Error("Authentication failed");
      }

      const response = await api.post(
        "/api/v1/events/",
        {
          title: eventTitle,
          video_id: videoId,
          video_timestamp: videoRef.current?.currentTime || 0,
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      // Add the new event to the list
      setEvents((prev) => [...prev, response.data]);
      setEventTitle("");

      // Pause the video when an event is added
      if (videoRef.current) {
        videoRef.current.pause();
      }
    } catch (err: any) {
      console.error("Error adding event:", err);
      setError(
        err.response?.data?.detail || "Failed to add event. Please try again."
      );
    } finally {
      setAddingEvent(false);
    }
  };

  const handleDeleteEvent = async (eventId: string) => {
    try {
      const token = await getToken();
      if (!token) {
        throw new Error("Authentication failed");
      }

      await api.delete(`/api/v1/events/${eventId}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      // Remove the event from the list
      setEvents((prev) => prev.filter((event) => event.id !== eventId));
    } catch (err: any) {
      console.error("Error deleting event:", err);
      setError(
        err.response?.data?.detail ||
          "Failed to delete event. Please try again."
      );
    }
  };

  const jumpToTimestamp = (timestamp: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = timestamp;
      videoRef.current.pause();
    }
  };

  const handleFinish = () => {
    navigate(`/video/${videoId}`);
  };

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <div className={styles.loader}></div>
        <p>Loading video...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.errorContainer}>
        <h2>Error</h2>
        <p>{error}</p>
        <button onClick={() => navigate(`/video/${videoId}`)}>
          Go to Video
        </button>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>Add Key Moments to "{videoTitle}"</h1>
        <p className={styles.instructions}>
          Play the video and click "Mark Key Moment" at important points to help
          viewers navigate your content.
        </p>
      </div>

      <div className={styles.content}>
        <div className={styles.videoSection}>
          {videoUrl && (
            <video
              ref={videoRef}
              className={styles.videoPlayer}
              controls
              onTimeUpdate={handleTimeUpdate}
            >
              <source src={videoUrl} type="video/mp4" />
              Your browser does not support the video tag.
            </video>
          )}

          <div className={styles.eventCreationForm}>
            <div className={styles.currentTimestamp}>
              Current Time: {formatTimestamp(currentTime)}
            </div>
            <div className={styles.eventInputContainer}>
              <input
                type="text"
                value={eventTitle}
                onChange={(e) => setEventTitle(e.target.value)}
                placeholder="Enter a title for this moment"
                className={styles.eventTitleInput}
                disabled={addingEvent}
              />
              <button
                onClick={handleAddEvent}
                className={styles.addEventButton}
                disabled={addingEvent || !eventTitle.trim()}
              >
                {addingEvent ? "Adding..." : "Mark Key Moment"}
              </button>
            </div>
          </div>
        </div>

        <div className={styles.eventsSection}>
          <h2>Key Moments ({events.length})</h2>
          {events.length === 0 ? (
            <p className={styles.noEvents}>
              No key moments added yet. Play the video and mark important
              moments.
            </p>
          ) : (
            <div className={styles.eventsList}>
              {events
                .sort((a, b) => a.video_timestamp - b.video_timestamp)
                .map((event) => (
                  <div key={event.id} className={styles.eventItem}>
                    <div className={styles.eventInfo}>
                      <span className={styles.eventTitle}>{event.title}</span>
                      <button
                        className={styles.timestampButton}
                        onClick={() => jumpToTimestamp(event.video_timestamp)}
                      >
                        {formatTimestamp(event.video_timestamp)}
                      </button>
                    </div>
                    <button
                      className={styles.deleteEventButton}
                      onClick={() => handleDeleteEvent(event.id)}
                    >
                      &times;
                    </button>
                  </div>
                ))}
            </div>
          )}

          <div className={styles.finishButtonContainer}>
            <button onClick={handleFinish} className={styles.finishButton}>
              Finish
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EventCreation;
