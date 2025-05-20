import React, { useState } from "react";
import styles from "./LeagueAccountConnection.module.css";
import { useLeagueConnect } from "../../utils/leagueConnect";
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
  const [isConnecting, setIsConnecting] = useState(false);
  const { connectLeagueAccount } = useLeagueConnect();

  const handleConnectAccount = async () => {
    try {
      setIsConnecting(true);
      await connectLeagueAccount();
      // This will redirect, so the following code won't execute
    } catch (error) {
      console.error("Error connecting League account:", error);
      setIsConnecting(false);
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
            disabled={isConnecting}
          >
            {isConnecting ? "Connecting..." : "Connect League Account"}
          </button>

          <button
            className={styles.skipButton}
            onClick={onSkip}
            disabled={isConnecting}
          >
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
