import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthToken } from "../../utils/auth";
import api from "../../api/axios";
import styles from "./VideoUpload.module.css";

// Array of TFT ranks
const TFT_RANKS = [
  "Iron 4",
  "Iron 3",
  "Iron 2",
  "Iron 1",
  "Bronze 4",
  "Bronze 3",
  "Bronze 2",
  "Bronze 1",
  "Silver 4",
  "Silver 3",
  "Silver 2",
  "Silver 1",
  "Gold 4",
  "Gold 3",
  "Gold 2",
  "Gold 1",
  "Platinum 4",
  "Platinum 3",
  "Platinum 2",
  "Platinum 1",
  "Emerald 4",
  "Emerald 3",
  "Emerald 2",
  "Emerald 1",
  "Diamond 4",
  "Diamond 3",
  "Diamond 2",
  "Diamond 1",
  "Master",
  "Grandmaster",
];

// Array of TFT finish positions
const TFT_FINISHES = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th"];

// Array of Patch Versions
const PATCH_VERSIONS = ["14.4", "14.3", "14.2", "14.1", "14.0"];

interface VideoUploadProps {
  isOpen: boolean;
  onClose: () => void;
}

interface UploadStatus {
  upload_id: string;
  status:
    | "uploading"
    | "uploading_video"
    | "generating_thumbnail"
    | "completed"
    | "error";
  progress: number;
  error?: string;
  filename: string;
}

const VideoUpload: React.FC<VideoUploadProps> = ({ isOpen, onClose }) => {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState("");

  // New optimized upload states
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus | null>(null);
  const [showGameDetails, setShowGameDetails] = useState(false);
  const [showEventOption, setShowEventOption] = useState(false);
  const [uploadedVideoId, setUploadedVideoId] = useState<string | null>(null);

  // Game details states
  const [gameVersion, setGameVersion] = useState("");
  const [gameVersionError, setGameVersionError] = useState("");
  const [rank, setRank] = useState("");
  const [result, setResult] = useState("");
  const [encounter, setEncounter] = useState("");
  const [composition, setComposition] = useState("");
  const [submittingDetails, setSubmittingDetails] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const navigate = useNavigate();
  const { getToken } = useAuthToken();

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const file = files[0];
      // Check if file is a video
      if (!file.type.startsWith("video/")) {
        setError("Please select a valid video file");
        return;
      }
      // Check file size (limit to 1500MB)
      if (file.size > 1500 * 1024 * 1024) {
        setError("File size should be less than 1500MB (1.5GB)");
        return;
      }

      setSelectedFile(file);
      setError("");

      // Start upload immediately
      await startUpload(file);
    }
  };

  const startUpload = async (file: File) => {
    try {
      setUploading(true);
      setError("");

      const token = await getToken();
      if (!token) {
        throw new Error("Authentication failed");
      }

      // Create form data for upload start
      const formData = new FormData();
      formData.append("file", file);

      // Start the upload
      const response = await api.post("/api/v1/videos/start-upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
          Authorization: `Bearer ${token}`,
        },
      });

      const { upload_id } = response.data;
      setUploadId(upload_id);

      // Start polling for progress
      startProgressPolling(upload_id);

      // Move to game details screen immediately
      setShowGameDetails(true);
    } catch (error: any) {
      console.error("Error starting upload:", error);
      setError(
        error.response?.data?.detail ||
          "Failed to start upload. Please try again."
      );
      setUploading(false);
    }
  };

  const startProgressPolling = (uploadId: string) => {
    pollIntervalRef.current = setInterval(async () => {
      try {
        const token = await getToken();
        if (!token) return;

        const response = await api.get(
          `/api/v1/videos/upload-status/${uploadId}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        const status: UploadStatus = response.data;
        setUploadStatus(status);
        setUploadProgress(status.progress);

        if (status.status === "completed" || status.status === "error") {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }
          setUploading(false);

          if (status.status === "error") {
            setError(status.error || "Upload failed");
          }
        }
      } catch (error) {
        console.error("Failed to check upload status:", error);
      }
    }, 1000); // Poll every second
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError("Please select a video file");
      return;
    }
    // File selection now triggers immediate upload, so this is just for validation
  };

  // Handle submitting game details and completing upload
  const handleGameDetailsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!uploadId) {
      setError("No upload in progress");
      return;
    }

    // Validate game version format
    if (!gameVersion.trim()) {
      setGameVersionError("Patch version is required");
      return;
    }

    // Validate game version format (e.g., 14.4 or 14.4a)
    const patchRegex = /^\d+\.\d+[a-z]?$/;
    if (!patchRegex.test(gameVersion.trim())) {
      setGameVersionError(
        "Invalid patch format. Use format like 14.4 or 14.4a"
      );
      return;
    }

    try {
      setSubmittingDetails(true);
      setError("");
      setGameVersionError("");

      const token = await getToken();
      if (!token) {
        throw new Error("Authentication failed");
      }

      // Parse composition into an array if provided
      const compositionArray = composition.trim()
        ? composition.split(",").map((item) => item.trim())
        : [];

      // Complete the upload with game details
      const formData = new FormData();
      formData.append("upload_id", uploadId);
      formData.append("title", title);
      formData.append("description", description);
      formData.append("game_version", gameVersion.trim());
      formData.append("rank", rank.trim() || "");
      formData.append("result", result.trim() || "");
      formData.append("composition", compositionArray.join(","));

      const response = await api.post(
        "/api/v1/videos/complete-upload",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
            Authorization: `Bearer ${token}`,
          },
        }
      );

      // Store the completed video ID and move to events option
      setUploadedVideoId(response.data.id);
      setShowGameDetails(false);
      setShowEventOption(true);
    } catch (error: any) {
      console.error("Error completing upload:", error);
      setError(
        error.response?.data?.detail ||
          "Failed to complete upload. Please try again."
      );
    } finally {
      setSubmittingDetails(false);
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

  // Handle skipping game details (with warning)
  const handleSkipGameDetails = () => {
    const confirmSkip = window.confirm(
      "You must provide at least the patch version. Are you sure you want to skip without saving any game details?"
    );
    if (confirmSkip) {
      setShowGameDetails(false);
      setShowEventOption(true);
    }
  };

  // Cancel upload
  const handleCancelUpload = async () => {
    if (uploadId) {
      try {
        const token = await getToken();
        if (token) {
          await api.delete(`/api/v1/videos/upload/${uploadId}`, {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });
        }
      } catch (error) {
        console.error("Failed to cancel upload:", error);
      }
    }

    // Clean up
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }

    handleClose();
  };

  // Reset the component state when closed
  const handleClose = () => {
    // Clean up polling
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }

    setTitle("");
    setDescription("");
    setSelectedFile(null);
    setUploading(false);
    setUploadProgress(0);
    setError("");
    setUploadId(null);
    setUploadStatus(null);
    setUploadedVideoId(null);
    setShowGameDetails(false);
    setShowEventOption(false);
    setGameVersion("");
    setGameVersionError("");
    setRank("");
    setResult("");
    setEncounter("");
    setComposition("");
    setSubmittingDetails(false);
    onClose();
  };

  const getProgressMessage = () => {
    if (!uploadStatus) return "Starting upload...";

    switch (uploadStatus.status) {
      case "uploading":
      case "uploading_video":
        return "Uploading video...";
      case "generating_thumbnail":
        return "Generating thumbnail...";
      case "completed":
        return "Upload completed!";
      case "error":
        return `Error: ${uploadStatus.error}`;
      default:
        return uploadStatus.status;
    }
  };

  if (!isOpen) return null;

  return (
    <div className={styles.modalOverlay}>
      <div className={styles.modal}>
        <div className={styles.modalHeader}>
          <h2>
            {showEventOption
              ? "Add Key Moments"
              : showGameDetails
              ? "Game Details"
              : "Upload Video"}
          </h2>
          <button
            className={styles.closeButton}
            onClick={uploading ? handleCancelUpload : handleClose}
          >
            &times;
          </button>
        </div>

        {!showGameDetails && !showEventOption ? (
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
              <p className={styles.fileHint}>
                Select a video file to start uploading immediately
              </p>
            </div>

            {error && <div className={styles.error}>{error}</div>}

            <div className={styles.formActions}>
              <button
                type="button"
                onClick={handleClose}
                className={styles.cancelButton}
                disabled={uploading}
              >
                Cancel
              </button>
            </div>
          </form>
        ) : showGameDetails ? (
          // Game Details Form
          <form
            onSubmit={handleGameDetailsSubmit}
            className={styles.uploadForm}
          >
            <div className={styles.successMessage}>
              <div className={styles.checkmark}>✓</div>
              <h3>Upload started successfully!</h3>
              <p className={styles.instructionText}>
                Fill out game details while your video uploads in the background
              </p>
            </div>

            {/* Upload Progress */}
            {/* <div className={styles.progressContainer}>
              <div className={styles.progressHeader}>
                <span className={styles.progressLabel}>
                  {getProgressMessage()}
                </span>
                <span className={styles.progressPercent}>
                  {uploadProgress}%
                </span>
              </div>
              <div className={styles.progressBarContainer}>
                <div
                  className={styles.progressBar}
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
            </div> */}

            <div className={styles.formGroup}>
              <label htmlFor="patchVersion">
                Patch <span className={styles.requiredField}>*</span>
              </label>
              <select
                id="patchVersion"
                value={gameVersion}
                onChange={(e) => setGameVersion(e.target.value)}
                className={styles.selectInput}
                disabled={submittingDetails}
              >
                <option value="">Select Patch</option>
                {PATCH_VERSIONS.map((patchOption) => (
                  <option key={patchOption} value={patchOption}>
                    {patchOption}
                  </option>
                ))}
              </select>
              {gameVersionError && (
                <div className={styles.fieldError}>{gameVersionError}</div>
              )}
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="rank">Rank</label>
              <select
                id="rank"
                value={rank}
                onChange={(e) => setRank(e.target.value)}
                className={styles.selectInput}
                disabled={submittingDetails}
              >
                <option value="">Select Rank</option>
                {TFT_RANKS.map((rankOption) => (
                  <option key={rankOption} value={rankOption}>
                    {rankOption}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="result">Finish</label>
              <select
                id="result"
                value={result}
                onChange={(e) => setResult(e.target.value)}
                className={styles.selectInput}
                disabled={submittingDetails}
              >
                <option value="">Select Finish Position</option>
                {TFT_FINISHES.map((finishOption) => (
                  <option key={finishOption} value={finishOption}>
                    {finishOption}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="encounter">Encounter (Optional)</label>
              <input
                type="text"
                id="encounter"
                value={encounter}
                onChange={(e) => setEncounter(e.target.value)}
                placeholder="e.g. Dragon, Noxus, etc."
                disabled={submittingDetails}
              />
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="composition">Build (Optional)</label>
              <input
                type="text"
                id="composition"
                value={composition}
                onChange={(e) => setComposition(e.target.value)}
                placeholder="e.g. Sorcerer, 8 Hyperpop, etc. (separate with commas)"
                disabled={submittingDetails}
              />
            </div>

            {error && <div className={styles.error}>{error}</div>}

            <div className={styles.formActions}>
              <button
                type="button"
                onClick={handleSkipGameDetails}
                className={styles.skipButton}
                disabled={submittingDetails}
              >
                Skip Details (Not Recommended)
              </button>
              <button
                type="submit"
                className={styles.submitButton}
                disabled={submittingDetails || !gameVersion.trim()}
              >
                {submittingDetails ? "Saving..." : "Save and Continue"}
              </button>
            </div>
          </form>
        ) : (
          // Event Creation Option Screen
          <div className={styles.eventOptionContainer}>
            <div className={styles.successMessage}>
              <div className={styles.checkmark}>✓</div>
              <h3>Video uploaded successfully!</h3>
              <p className={styles.instructionText}>
                Your video is now available and ready to view
              </p>
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
              <button
                className={styles.addEventsButton}
                onClick={handleAddEvents}
              >
                Add Key Moments
              </button>
              <button
                className={styles.skipEventsButton}
                onClick={handleSkipEvents}
              >
                View Video
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoUpload;
