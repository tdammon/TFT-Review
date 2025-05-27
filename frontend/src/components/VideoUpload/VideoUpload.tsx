import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthToken } from "../../utils/auth";
import api from "../../api/axios";
import styles from "./VideoUpload.module.css";
import UploadProgress from "./UploadProgress";

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

interface ChunkedUploadResponse {
  upload_id: string;
  chunk_size: number;
  total_chunks: number;
  presigned_urls: { [key: number]: string };
}

interface ChunkUploadProgress {
  chunkNumber: number;
  status: "pending" | "uploading" | "completed" | "error";
  progress: number;
  etag?: string;
}

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

  // New state for chunked upload
  const [chunks, setChunks] = useState<ChunkUploadProgress[]>([]);
  const [uploadingChunks, setUploadingChunks] = useState(false);
  const [currentChunk, setCurrentChunk] = useState(0);
  const [chunkSize] = useState(5 * 1024 * 1024); // 5MB chunks
  const [totalChunks, setTotalChunks] = useState(0);
  const [chunkUploadProgress, setChunkUploadProgress] = useState<{
    [key: number]: number;
  }>({});
  const [uploadedEtags, setUploadedEtags] = useState<{ [key: number]: string }>(
    {}
  );

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

      // Calculate total chunks
      const totalChunks = Math.ceil(file.size / chunkSize);
      setTotalChunks(totalChunks);

      // Initialize chunk progress
      const initialChunks: ChunkUploadProgress[] = Array.from(
        { length: totalChunks },
        (_, i) => ({
          chunkNumber: i + 1,
          status: "pending",
          progress: 0,
        })
      );
      setChunks(initialChunks);

      // Start chunked upload
      await startChunkedUpload(file);
    }
  };

  const startChunkedUpload = async (file: File) => {
    try {
      setUploading(true);
      setError("");

      const token = await getToken();
      if (!token) {
        throw new Error("Authentication failed");
      }

      // Initiate chunked upload
      const response = await api.post<ChunkedUploadResponse>(
        "/api/v1/videos/initiate-chunked-upload",
        {
          filename: file.name,
          content_type: file.type,
          total_size: file.size,
          chunk_size: chunkSize,
        },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      console.log("[UPLOAD_ID] Setting upload_id:", response.data.upload_id);
      setUploadId(response.data.upload_id);

      // Start uploading chunks in the background
      uploadChunks(
        file,
        response.data.presigned_urls,
        response.data.upload_id
      ).catch((error) => {
        console.error("[UPLOAD] Chunk upload failed:", error);
        setError("Failed to upload video chunks. Please try again.");
        setShowGameDetails(false);
      });
    } catch (error: any) {
      console.error(
        "[UPLOAD] Error starting chunked upload:",
        error?.response?.data || error
      );

      // Handle validation error array
      if (Array.isArray(error?.response?.data?.detail)) {
        const validationErrors = error.response.data.detail;
        const errorMessages = validationErrors
          .map((err: any) => err.msg)
          .join(", ");
        setError(`Upload failed: ${errorMessages}`);
      } else if (typeof error?.response?.data?.detail === "string") {
        // Handle string error message
        setError(error.response.data.detail);
      } else if (error?.message) {
        // Handle error object with message
        setError(error.message);
      } else {
        // Handle generic error
        setError("Failed to start upload. Please try again.");
      }
      setUploading(false);
    }
  };

  // Add effect to track uploadId changes
  useEffect(() => {
    console.log("[UPLOAD_ID] Upload ID changed:", uploadId);
  }, [uploadId]);

  // Add effect to track showGameDetails changes
  useEffect(() => {
    console.log("[GAME_DETAILS] Show game details changed:", {
      showGameDetails,
      currentUploadId: uploadId,
    });
  }, [showGameDetails, uploadId]);

  const uploadChunks = async (
    file: File,
    presignedUrls: { [key: number]: string },
    newUploadId: string
  ) => {
    setUploadingChunks(true);
    const etags: { [key: number]: string } = {};

    try {
      console.log("[UPLOAD] Starting chunk upload process", {
        totalChunks,
        chunkSize,
        fileSize: file.size,
        fileName: file.name,
        fileType: file.type,
      });

      // Upload chunks in parallel with a limit of 3 concurrent uploads
      const chunkNumbers = Object.keys(presignedUrls).map(Number);
      const concurrentLimit = 3;

      for (let i = 0; i < chunkNumbers.length; i += concurrentLimit) {
        const chunkBatch = chunkNumbers.slice(i, i + concurrentLimit);
        console.log(`[UPLOAD] Processing batch ${i / concurrentLimit + 1}`, {
          chunkBatch,
        });

        await Promise.all(
          chunkBatch.map(async (chunkNumber) => {
            const start = (chunkNumber - 1) * chunkSize;
            const end = Math.min(start + chunkSize, file.size);
            const chunk = file.slice(start, end);

            console.log(`[UPLOAD] Uploading chunk ${chunkNumber}`, {
              start,
              end,
              size: chunk.size,
              type: chunk.type,
            });

            try {
              const response = await fetch(presignedUrls[chunkNumber], {
                method: "PUT",
                body: chunk,
                headers: {
                  "Content-Type": file.type,
                },
              });

              if (!response.ok) {
                const errorText = await response.text();
                console.error(`[UPLOAD] Chunk ${chunkNumber} upload failed`, {
                  status: response.status,
                  statusText: response.statusText,
                  responseText: errorText,
                  headers: Object.fromEntries(response.headers.entries()),
                });
                throw new Error(
                  `Failed to upload chunk ${chunkNumber}: ${response.statusText}`
                );
              }

              // Get ETag from response headers and clean it
              const etag = response.headers.get("ETag");
              console.log(`[UPLOAD] Chunk ${chunkNumber} response headers:`, {
                headers: Object.fromEntries(response.headers.entries()),
                etag,
              });

              if (etag) {
                // Remove quotes and store with numeric key
                const cleanEtag = etag.replace(/^"|"$/g, "");
                etags[chunkNumber] = cleanEtag;
                setUploadedEtags((prev) => ({
                  ...prev,
                  [chunkNumber]: cleanEtag,
                }));

                console.log(
                  `[UPLOAD] Chunk ${chunkNumber} uploaded successfully`,
                  {
                    originalEtag: etag,
                    cleanEtag,
                    storedEtags: etags,
                  }
                );
              } else {
                console.error(
                  `[UPLOAD] No ETag received for chunk ${chunkNumber}`
                );
                throw new Error(`No ETag received for chunk ${chunkNumber}`);
              }

              // Update chunk status
              setChunks((prev) =>
                prev.map((c) =>
                  c.chunkNumber === chunkNumber
                    ? { ...c, status: "completed", progress: 100 }
                    : c
                )
              );

              // Update overall progress
              const totalProgress =
                (Object.keys(etags).length / totalChunks) * 100;
              setUploadProgress(totalProgress);
            } catch (error: any) {
              console.error(`[UPLOAD] Error uploading chunk ${chunkNumber}:`, {
                error,
                errorMessage: error?.message,
                errorStack: error?.stack,
              });
              setChunks((prev) =>
                prev.map((c) =>
                  c.chunkNumber === chunkNumber
                    ? { ...c, status: "error", progress: 0 }
                    : c
                )
              );
              throw error;
            }
          })
        );
      }

      // Debug log before completing
      console.log("[UPLOAD] Preparing to complete upload", {
        upload_id: newUploadId,
        total_chunks: totalChunks,
        etags: etags,
        etagsLength: Object.keys(etags).length,
        allChunksUploaded: Object.keys(etags).length === totalChunks,
      });

      // Complete the upload
      try {
        const response = await api.post(
          "/api/v1/videos/complete-chunked-upload",
          {
            upload_id: newUploadId,
            total_chunks: totalChunks,
            etags: etags,
          },
          {
            headers: { Authorization: `Bearer ${await getToken()}` },
          }
        );
        console.log("[UPLOAD] Upload completed successfully", {
          response: response.data,
        });

        // Reset upload states after successful completion
        setUploadingChunks(false);
        setUploading(false);
        setUploadProgress(100);
      } catch (error: any) {
        console.error("[UPLOAD] Error completing upload:", {
          error,
          errorResponse: error?.response?.data,
          errorStatus: error?.response?.status,
          requestData: {
            upload_id: newUploadId,
            total_chunks: totalChunks,
            etags: etags,
          },
        });
        throw error;
      }

      setUploadingChunks(false);
      setUploadProgress(100);
    } catch (error: any) {
      console.error("[UPLOAD] Fatal error in chunk upload:", {
        error,
        errorMessage: error?.message,
        errorStack: error?.stack,
        uploadState: {
          uploadId,
          totalChunks,
          completedChunks: Object.keys(etags).length,
          chunks: chunks.map((c) => ({
            number: c.chunkNumber,
            status: c.status,
          })),
        },
      });

      // Format error message
      let errorMessage = "Failed to upload video chunks. ";
      if (error?.message) {
        errorMessage += error.message;
      } else if (Array.isArray(error?.response?.data?.detail)) {
        const validationErrors = error.response.data.detail;
        errorMessage += validationErrors.map((err: any) => err.msg).join(", ");
      } else if (typeof error?.response?.data?.detail === "string") {
        errorMessage += error.response.data.detail;
      }

      setError(errorMessage);
      setUploadingChunks(false);
      throw error;
    }
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

    console.log("[GAME_DETAILS] Submitting details with upload_id:", {
      uploadId,
      type: typeof uploadId,
    });

    if (!uploadId || typeof uploadId !== "string") {
      console.error("[GAME_DETAILS] Invalid upload_id:", {
        uploadId,
        type: typeof uploadId,
      });
      setError("Invalid upload ID. Please try uploading again.");
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

      // Check if chunks are still uploading
      if (uploadingChunks) {
        setError(
          "Please wait for the video upload to complete before saving details."
        );
        setSubmittingDetails(false);
        return;
      }

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
      formData.append("title", title || "Untitled"); // Ensure title is never empty
      formData.append("description", description || "");
      formData.append("game_version", gameVersion.trim());
      formData.append("rank", rank.trim() || "");
      formData.append("result", result.trim() || "");
      formData.append("composition", compositionArray.join(","));

      const response = await api.post(
        "/api/v1/videos/complete-chunked-upload-details",
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
      console.error(
        "[GAME_DETAILS] Error completing upload:",
        error?.response?.data || error
      );

      // Handle validation error array
      if (Array.isArray(error?.response?.data?.detail)) {
        const validationErrors = error.response.data.detail;
        const errorMessages = validationErrors
          .map((err: any) => err.msg)
          .join(", ");
        setError(`Validation error: ${errorMessages}`);
      } else if (typeof error?.response?.data?.detail === "string") {
        // Handle string error message
        setError(error.response.data.detail);
      } else {
        // Handle generic error
        setError("Failed to complete upload. Please try again.");
      }
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
    console.log("handleClose");

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
    }
  };

  if (!isOpen) return null;

  return (
    <div className={styles.modalOverlay}>
      <div className={styles.modal}>
        <div className={styles.modalHeader}>
          <h2>
            {showEventOption
              ? "Add Events"
              : showGameDetails
              ? "Game Details"
              : "Upload Video"}
          </h2>
          <button className={styles.closeButton} onClick={handleClose}>
            ×
          </button>
        </div>

        {showEventOption ? (
          <div className={styles.eventOptionContainer}>
            <div className={styles.successMessage}>
              <div className={styles.checkmark}>✓</div>
              <h3>Video Upload Complete!</h3>
            </div>
            <p className={styles.eventPrompt}>
              Would you like to add events to your video now?
              <span className={styles.eventPromptDetail}>
                Events help others navigate through important moments in your
                gameplay.
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
                Add Events
              </button>
            </div>
          </div>
        ) : showGameDetails ? (
          <form
            onSubmit={handleGameDetailsSubmit}
            className={styles.uploadForm}
          >
            {(uploading || uploadingChunks) && (
              <UploadProgress
                chunks={chunks}
                totalChunks={totalChunks}
                uploadProgress={uploadProgress}
                isUploading={uploadingChunks}
              />
            )}

            <div className={styles.formGroup}>
              <label>
                Patch Version <span className={styles.requiredField}>*</span>
              </label>
              <select
                className={`${styles.selectInput} ${
                  gameVersionError ? styles.inputError : ""
                }`}
                value={gameVersion}
                onChange={(e) => setGameVersion(e.target.value)}
              >
                <option value="">Select Patch Version</option>
                {PATCH_VERSIONS.map((version) => (
                  <option key={version} value={version}>
                    {version}
                  </option>
                ))}
              </select>
              {gameVersionError && (
                <div className={styles.fieldError}>{gameVersionError}</div>
              )}
            </div>

            <div className={styles.formGroup}>
              <label>Rank</label>
              <select
                className={styles.selectInput}
                value={rank}
                onChange={(e) => setRank(e.target.value)}
              >
                <option value="">Select Rank</option>
                {TFT_RANKS.map((rank) => (
                  <option key={rank} value={rank}>
                    {rank}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.formGroup}>
              <label>Result</label>
              <select
                className={styles.selectInput}
                value={result}
                onChange={(e) => setResult(e.target.value)}
              >
                <option value="">Select Result</option>
                {TFT_FINISHES.map((finish) => (
                  <option key={finish} value={finish}>
                    {finish}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.formGroup}>
              <label>Composition</label>
              <input
                type="text"
                value={composition}
                onChange={(e) => setComposition(e.target.value)}
                placeholder="Enter composition (comma-separated)"
              />
            </div>

            {error && <div className={styles.error}>{error}</div>}

            <div className={styles.formActions}>
              <button
                type="button"
                className={styles.cancelButton}
                onClick={handleSkipGameDetails}
                disabled={submittingDetails}
              >
                Skip
              </button>
              <button
                type="submit"
                className={styles.submitButton}
                disabled={submittingDetails || uploadingChunks || uploading}
              >
                {submittingDetails
                  ? "Saving..."
                  : uploadingChunks || uploading
                  ? "Please wait for upload to complete..."
                  : "Save Details"}
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleSubmit} className={styles.uploadForm}>
            <div className={styles.formGroup}>
              <label>Upload Video File</label>
              <div className={styles.fileInputWrapper}>
                <input
                  type="file"
                  ref={fileInputRef}
                  className={styles.fileInput}
                  onChange={handleFileChange}
                  accept="video/*"
                  disabled={uploading}
                />
                <button
                  type="button"
                  className={styles.browseButton}
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                >
                  Browse
                </button>
                {selectedFile && (
                  <span className={styles.fileName}>{selectedFile.name}</span>
                )}
              </div>
            </div>

            <div className={styles.formGroup}>
              <label>
                Title <span className={styles.requiredField}>*</span>
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Enter video title"
                required
              />
            </div>

            <div className={styles.formGroup}>
              <label>
                Description <span className={styles.requiredField}>*</span>
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Enter video description"
                required
              />
            </div>

            {error && <div className={styles.error}>{error}</div>}

            <div className={styles.formActions}>
              <button
                type="button"
                className={styles.cancelButton}
                onClick={handleCancelUpload}
              >
                Cancel
              </button>
              {selectedFile && title.trim() && description.trim() ? (
                <button
                  type="button"
                  className={styles.submitButton}
                  onClick={() => setShowGameDetails(true)}
                >
                  Continue to Game Details
                </button>
              ) : (
                <button
                  type="submit"
                  className={styles.submitButton}
                  disabled={!selectedFile}
                >
                  {uploading ? "Uploading..." : "Upload Video"}
                </button>
              )}
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default VideoUpload;
