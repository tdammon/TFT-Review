import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import styles from "./HomePage.module.css";
import api from "../../api/axios";
import { useAuthToken } from "../../utils/auth";

interface Video {
  id: number;
  title: string;
  thumbnail_url: string | null;
  views: number;
  user_id: number;
  created_at: string;
}

interface User {
  discord_connected: boolean;
  id: number;
  username: string;
  email: string;
  profile_picture: string;
  verified_riot_account: boolean;
}

const HomePage = ({ userInfo }: { userInfo: User }) => {
  const [videos, setVideos] = useState<Video[]>([]);
  const [filter, setFilter] = useState<string>("recent");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const { getToken } = useAuthToken();

  useEffect(() => {
    const fetchVideos = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const token = await getToken();
        if (!token) {
          throw new Error("Authentication failed");
        }

        let endpoint = "/api/v1/videos";
        if (filter === "mine") {
          endpoint = "/api/v1/videos/my-videos";
        }

        const response = await api.get(endpoint, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        setVideos(response.data);
      } catch (err: any) {
        console.error("Error fetching videos:", err);
        setError(err.response?.data?.detail || "Failed to load videos");
      } finally {
        setIsLoading(false);
      }
    };

    fetchVideos();
  }, [filter]);

  const handleFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setFilter(e.target.value);
  };

  return (
    <div className={styles.container}>
      <main className={styles.main}>
        <div className={styles.filters}>
          <h2>Recent Videos</h2>
          <select
            className={styles.filterSelect}
            value={filter}
            onChange={handleFilterChange}
          >
            <option value="recent">Most Recent</option>
            <option value="popular">Most Popular</option>
            <option value="mine">My Videos</option>
          </select>
        </div>

        {isLoading && <div className={styles.loading}>Loading videos...</div>}

        {error && <div className={styles.error}>{error}</div>}

        {!isLoading && !error && videos.length === 0 && (
          <div className={styles.noVideos}>
            {filter === "mine"
              ? "You haven't uploaded any videos yet."
              : "No videos available."}
          </div>
        )}

        <div className={styles.videoGrid}>
          {videos.map((video) => (
            <Link
              to={`/video/${video.id}`}
              className={styles.videoCard}
              key={video.id}
            >
              <div className={styles.thumbnail}>
                {video.thumbnail_url ? (
                  <img
                    src={video.thumbnail_url}
                    alt={video.title}
                    className={styles.thumbnailImage}
                  />
                ) : (
                  <div className={styles.placeholderThumbnail}>
                    <span>{video.title.charAt(0)}</span>
                  </div>
                )}
              </div>
              <div className={styles.videoInfo}>
                <h3>{video.title}</h3>
                <p>
                  Uploaded: {new Date(video.created_at).toLocaleDateString()}
                </p>
                <p>Views: {video.views}</p>
              </div>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
};

export default HomePage;
