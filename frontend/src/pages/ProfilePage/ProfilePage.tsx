import React, { useState } from "react";
import styles from "./ProfilePage.module.css";
import { useLeagueConnect } from "../../utils/leagueConnect";

// Types
import { User } from "../../types/serverResponseTypes";

const ProfilePage = ({ userInfo }: { userInfo: User }) => {
  const [isConnecting, setIsConnecting] = useState(false);
  const { connectLeagueAccount } = useLeagueConnect();

  const handleConnectLeagueAccount = async () => {
    try {
      setIsConnecting(true);
      await connectLeagueAccount();
      // Note: This will redirect the user, so the rest of the function won't execute
    } catch (error) {
      console.error("Failed to connect League account:", error);
      setIsConnecting(false);
    }
  };

  return (
    <div className={styles.container}>
      <main className={styles.main}>
        <div className={styles.profileHeader}>
          <div className={styles.profilePictureContainer}>
            <img
              src={userInfo.profile_picture}
              alt="Profile"
              className={styles.profilePicture}
            />
          </div>
          <div className={styles.profileInfoContainer}>
            <div className={styles.profileName}>{userInfo.username}</div>
            <div className={styles.profileAccountRating}>
              {/* {userInfo.account_rating} */}
            </div>
          </div>
          <div className={styles.profileConnectContainer}>
            <button
              className={styles.connectButton}
              onClick={handleConnectLeagueAccount}
              disabled={isConnecting}
            >
              {isConnecting ? "Connecting..." : "Connect League Account"}
            </button>
          </div>
        </div>
        <div className={styles.profileRankingContainer}>
          {userInfo.verified_riot_account ? (
            <div className={styles.profileStatsContainer}>
              <div className={styles.profileStatItem}>
                <div className={styles.profileStatItemHeader}>
                  <h3>Current</h3>
                </div>
                <div className={styles.profileStatItemContent}>
                  <p>1000</p>
                </div>
              </div>
            </div>
          ) : (
            <div className={styles.connectLeagueAccountContainer}>
              Connect your League account to see your stats
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default ProfilePage;
