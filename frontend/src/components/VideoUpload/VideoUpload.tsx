import React, { useState, useRef } from "react";
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
  const [showGameDetails, setShowGameDetails] = useState(false);
  const [showEventOption, setShowEventOption] = useState(false);

  // Game details states
  const [gameVersion, setGameVersion] = useState("");
  const [gameVersionError, setGameVersionError] = useState("");
  const [rank, setRank] = useState("");
  const [result, setResult] = useState("");
  const [encounter, setEncounter] = useState("");
  const [composition, setComposition] = useState("");

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

      // Store the uploaded video ID and show the game details screen
      setUploadedVideoId(response.data.id);
      setUploadComplete(true);
      setShowGameDetails(true);
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

  // Handle submitting game details
  const handleGameDetailsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!uploadedVideoId) return;

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

      // Update the video with game details
      await api.patch(
        `/api/v1/videos/${uploadedVideoId}`,
        {
          game_version: gameVersion.trim(),
          rank: rank.trim() || null,
          result: result.trim() || null,
          composition: compositionArray.length > 0 ? compositionArray : null,
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      // Move to the events option screen
      setShowGameDetails(false);
      setShowEventOption(true);
    } catch (error: any) {
      console.error("Error updating video details:", error);
      setError(
        error.response?.data?.detail ||
          "Failed to update video details. Please try again."
      );
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
    setShowGameDetails(false);
    setShowEventOption(false);
    setGameVersion("");
    setGameVersionError("");
    setRank("");
    setResult("");
    setEncounter("");
    setComposition("");
    onClose();
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
          <button className={styles.closeButton} onClick={handleClose}>
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
        ) : showGameDetails ? (
          // Game Details Form
          <form
            onSubmit={handleGameDetailsSubmit}
            className={styles.uploadForm}
          >
            <div className={styles.successMessage}>
              <div className={styles.checkmark}>✓</div>
              <h3>Video uploaded successfully!</h3>
              <p className={styles.instructionText}>
                Add game details to help others find and understand your content
              </p>
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="patchVersion">
                Patch <span className={styles.requiredField}>*</span>
              </label>
              <select
                id="patchVersion"
                value={gameVersion}
                onChange={(e) => setGameVersion(e.target.value)}
                className={styles.selectInput}
              >
                <option value="">Select Patch</option>
                {PATCH_VERSIONS.map((patchOption) => (
                  <option key={patchOption} value={patchOption}>
                    {patchOption}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="rank">Rank</label>
              <select
                id="rank"
                value={rank}
                onChange={(e) => setRank(e.target.value)}
                className={styles.selectInput}
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
              />
            </div>

            {error && <div className={styles.error}>{error}</div>}

            <div className={styles.formActions}>
              <button
                type="button"
                onClick={handleSkipGameDetails}
                className={styles.skipButton}
              >
                Skip Details (Not Recommended)
              </button>
              <button type="submit" className={styles.submitButton}>
                Save and Continue
              </button>
            </div>
          </form>
        ) : (
          // Event Creation Option Screen
          <div className={styles.eventOptionContainer}>
            <div className={styles.successMessage}>
              <div className={styles.checkmark}>✓</div>
              <h3>Game details saved!</h3>
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
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoUpload;
