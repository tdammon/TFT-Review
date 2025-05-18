import React from "react";
import styles from "./LeagueAccountConnection.module.css";
import { useAuthToken } from "../../utils/auth";
import api from "../../api/axios";
// import riotLogo from "../../assets/riot-logo.png";

interface LeagueAccountConnectionProps {
  onComplete: (connected: boolean) => void;
  onSkip: () => void;
  isOnboarding?: boolean;
}

const LeagueAccountConnection: React.FC<LeagueAccountConnectionProps> = ({
  onComplete,
  onSkip,
  isOnboarding = false,
}) => {
  const { getToken } = useAuthToken();

  const handleConnectAccount = async () => {
    try {
      const token = await getToken();
      if (!token) {
        throw new Error("Authentication failed");
      }

      // Initiate the Riot authentication process
      // This would redirect to Riot's OAuth page
      const response = await api.get("/api/v1/auth/riot/connect", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      // Redirect to Riot login page
      window.location.href = response.data.auth_url;

      // The user will be redirected back to your application after authentication
      // You'll need to handle that in your routes
    } catch (error) {
      console.error("Error connecting League account:", error);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <div className={styles.logoContainer}>
          {/* <img src={riotLogo} alt="Riot Games Logo" className={styles.logo} /> */}
        </div>

        <h2 className={styles.title}>Connect your League of Legends account</h2>

        <p className={styles.description}>
          Connect your League account to unlock these features:
        </p>

        <ul className={styles.benefitsList}>
          <li>Auto-fill game details when uploading videos</li>
          <li>Display your verified rank on your profile</li>
          <li>Help others find content from players at their skill level</li>
        </ul>

        <div className={styles.buttons}>
          <button
            className={styles.connectButton}
            onClick={handleConnectAccount}
          >
            Connect League Account
          </button>

          <button className={styles.skipButton} onClick={onSkip}>
            {isOnboarding ? "Skip for now" : "Cancel"}
          </button>
        </div>

        {isOnboarding && (
          <p className={styles.note}>
            You can always connect your account later in settings.
          </p>
        )}
      </div>
    </div>
  );
};

export default LeagueAccountConnection;
