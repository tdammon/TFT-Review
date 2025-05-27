import React, { useEffect, useRef } from "react";
import styles from "./UploadProgress.module.css";

interface ChunkProgress {
  chunkNumber: number;
  status: "pending" | "uploading" | "completed" | "error";
  progress: number;
}

interface UploadProgressProps {
  chunks: ChunkProgress[];
  totalChunks: number;
  uploadProgress: number;
  isUploading: boolean;
}

const UploadProgress: React.FC<UploadProgressProps> = ({
  chunks,
  totalChunks,
  uploadProgress,
  isUploading,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const lastCompletedChunk = chunks.reduce(
    (max, chunk) =>
      chunk.status === "completed" ? Math.max(max, chunk.chunkNumber) : max,
    0
  );

  // Auto-scroll to keep the active chunks in view
  useEffect(() => {
    if (containerRef.current && lastCompletedChunk > 0) {
      const chunkWidth = 40; // Width of each chunk + margin
      const scrollAmount = (lastCompletedChunk - 2) * chunkWidth; // Keep last completed chunk and current chunk visible
      containerRef.current.scrollLeft = scrollAmount;
    }
  }, [lastCompletedChunk]);

  return (
    <div className={styles.progressWrapper}>
      <div className={styles.progressInfo}>
        <div className={styles.progressBar}>
          <div
            className={styles.progressFill}
            style={{ width: `${uploadProgress}%` }}
          />
        </div>
        <span className={styles.progressText}>
          {uploadProgress.toFixed(1)}% -{" "}
          {isUploading ? "Uploading video..." : "Processing..."}
        </span>
      </div>

      <div className={styles.chunksContainer} ref={containerRef}>
        <div className={styles.chunksTrack}>
          {chunks.map((chunk) => (
            <div
              key={chunk.chunkNumber}
              className={`${styles.chunk} ${styles[chunk.status]}`}
              title={`Chunk ${chunk.chunkNumber}: ${chunk.status}`}
            >
              {chunk.chunkNumber}
            </div>
          ))}
          {/* Add ellipsis before total indicator */}
          <div className={styles.ellipsis}>...</div>
          {/* Always show total chunks indicator */}
          <div
            className={`${styles.chunk} ${styles.lastChunk}`}
            title={`Total Chunks: ${totalChunks}`}
          >
            {totalChunks}
          </div>
        </div>
      </div>
    </div>
  );
};

export default UploadProgress;
