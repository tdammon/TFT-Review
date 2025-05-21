import React, { useRef, useState } from "react";
import styles from "./Header.module.css";
import { useAuth0 } from "@auth0/auth0-react";
import { Link } from "react-router-dom";
import VideoUpload from "../VideoUpload/VideoUpload";

const Header = () => {
  const { user } = useAuth0();
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  const handleOpenUploadModal = () => {
    setIsUploadModalOpen(true);
  };

  const handleCloseUploadModal = () => {
    setIsUploadModalOpen(false);
  };

  return (
    <header className={styles.header}>
      <h1>Better TFT</h1>
      <div className={styles.userSection}>
        <span>Welcome, {user?.name}</span>
        <button className={styles.uploadButton} onClick={handleOpenUploadModal}>
          Upload Video
        </button>
        <ProfileDropdown user={user} />
      </div>

      {/* Video Upload Modal */}
      <VideoUpload
        isOpen={isUploadModalOpen}
        onClose={handleCloseUploadModal}
      />
    </header>
  );
};

export default Header;

const ProfileDropdown = ({ user }: { user: any }) => {
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  const { logout } = useAuth0();
  const toggleDropdown = (): void => {
    setIsOpen(!isOpen);
  };

  const handleLogout = (): void => {
    logout();
  };

  return (
    <div className={styles.dropdown} ref={dropdownRef}>
      <button
        className={styles.dropdownButton}
        onClick={toggleDropdown}
        aria-expanded={isOpen}
      >
        <img
          src={user?.picture}
          alt="Profile"
          className={styles.profilePicture}
        />
        <span className={styles.username}>
          <svg
            className={styles.chevron}
            width="25"
            height="25"
            viewBox="0 0 24 24"
            fill="currentColor"
          >
            <path d="M7 10l5 5 5-5z" />
          </svg>
        </span>
        {isOpen && (
          <div className={styles.dropdownContent}>
            <Link className={styles.dropdownItem} to="/profile">
              Profile
            </Link>
            {/* <Link className={styles.dropdownItem} to="settings">
              Settings
            </Link> */}
            <button
              className={`${styles.logoutButton} ${styles.dropdownItem}`}
              onClick={handleLogout}
            >
              Log Out
            </button>
          </div>
        )}
      </button>
    </div>
  );
};
