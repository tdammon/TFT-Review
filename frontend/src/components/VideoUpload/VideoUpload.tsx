import React, { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthToken } from "../../utils/auth";
import api from "../../api/axios";
import styles from "./VideoUpload.module.css";

interface VideoUploadProps {
  isOpen: boolean;
  onClose: () => void;
}

const VideoUpload: React.FC<VideoUploadProps> = ({ isOpen, onClose }) => {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState("");
  // New states for the upload flow
  const [uploadedVideoId, setUploadedVideoId] = useState<string | null>(null);
  const [uploadComplete, setUploadComplete] = useState(false);
  const [showEventOption, setShowEventOption] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { getToken } = useAuthToken();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const file = files[0];
      // Check if file is a video
      if (!file.type.startsWith("video/")) {
        setError("Please select a valid video file");
        return;
      }
      // Check file size (limit to 500MB)
      if (file.size > 500 * 1024 * 1024) {
        setError("File size should be less than 500MB");
        return;
      }
      setSelectedFile(file);
      setError("");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError("Please select a video file");
      return;
    }

    try {
      setUploading(true);
      setError("");

      const token = await getToken();
      if (!token) {
        throw new Error("Authentication failed");
      }

      // Create form data
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("title", title);
      formData.append("description", description);

      // Upload the video
      const response = await api.post("/api/v1/videos", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
          Authorization: `Bearer ${token}`,
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / (progressEvent.total || 100)
          );
          setUploadProgress(percentCompleted);
        },
      });

      // Store the uploaded video ID and show the event option screen
      setUploadedVideoId(response.data.id);
      setUploadComplete(true);
      setShowEventOption(true);
    } catch (error: any) {
      console.error("Error uploading video:", error);
      setError(
        error.response?.data?.detail ||
          "Failed to upload video. Please try again."
      );
    } finally {
      setUploading(false);
    }
  };

  // Handle adding events now
  const handleAddEvents = () => {
    if (uploadedVideoId) {
      navigate(`/video/${uploadedVideoId}/add-events`);
      onClose();
    }
  };

  // Handle skipping event creation
  const handleSkipEvents = () => {
    if (uploadedVideoId) {
      navigate(`/video/${uploadedVideoId}`);
      onClose();
    }
  };

  // Reset the component state when closed
  const handleClose = () => {
    setTitle("");
    setDescription("");
    setSelectedFile(null);
    setUploading(false);
    setUploadProgress(0);
    setError("");
    setUploadedVideoId(null);
    setUploadComplete(false);
    setShowEventOption(false);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className={styles.modalOverlay}>
      <div className={styles.modal}>
        <div className={styles.modalHeader}>
          <h2>{showEventOption ? "Add Key Moments" : "Upload Video"}</h2>
          <button className={styles.closeButton} onClick={handleClose}>
            &times;
          </button>
        </div>

        {!showEventOption ? (
          // Upload Form
          <form onSubmit={handleSubmit} className={styles.uploadForm}>
            <div className={styles.formGroup}>
              <label htmlFor="title">Title</label>
              <input
                type="text"
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Enter video title"
                required
                disabled={uploading}
              />
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="description">Description</label>
              <textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Enter video description"
                rows={4}
                disabled={uploading}
              />
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="video">Video File</label>
              <div className={styles.fileInputWrapper}>
                <input
                  type="file"
                  id="video"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept="video/*"
                  className={styles.fileInput}
                  disabled={uploading}
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className={styles.browseButton}
                  disabled={uploading}
                >
                  Browse Files
                </button>
                <span className={styles.fileName}>
                  {selectedFile ? selectedFile.name : "No file selected"}
                </span>
              </div>
            </div>

            {error && <div className={styles.error}>{error}</div>}

            {uploading && (
              <div className={styles.progressContainer}>
                <div
                  className={styles.progressBar}
                  style={{ width: `${uploadProgress}%` }}
                ></div>
                <span className={styles.progressText}>{uploadProgress}%</span>
              </div>
            )}

            <div className={styles.formActions}>
              <button
                type="button"
                onClick={handleClose}
                className={styles.cancelButton}
                disabled={uploading}
              >
                Cancel
              </button>
              <button
                type="submit"
                className={styles.submitButton}
                disabled={uploading || !selectedFile}
              >
                {uploading ? "Uploading..." : "Upload Video"}
              </button>
            </div>
          </form>
        ) : (
          // Event Creation Option Screen
          <div className={styles.eventOptionContainer}>
            <div className={styles.successMessage}>
              <div className={styles.checkmark}>✓</div>
              <h3>Video uploaded successfully!</h3>
            </div>

            <p className={styles.eventPrompt}>
              Would you like to add key moments to your video now?
              <br />
              <span className={styles.eventPromptDetail}>
                Key moments help viewers navigate to important parts of your
                video.
              </span>
            </p>

            <div className={styles.eventOptionButtons}>
              <button className={styles.skipButton} onClick={handleSkipEvents}>
                Skip for Now
              </button>
              <button
                className={styles.addEventsButton}
                onClick={handleAddEvents}
              >
                Add Key Moments
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoUpload;
