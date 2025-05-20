import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import styles from "./OnboardingPage.module.css";
import api from "../../api/axios";
import { useAuthToken } from "../../utils/auth";
// import RiotLogo from "../../assets/svg/RiotLogo";

const AUTH0_AUDIENCE = process.env.REACT_APP_AUTH0_AUDIENCE;

// Define onboarding steps
enum OnboardingStep {
  Username = 0,
  LeagueConnection = 1,
  Complete = 2,
}

const OnboardingPage = () => {
  const [currentStep, setCurrentStep] = useState<OnboardingStep>(
    OnboardingStep.Username
  );
  const [username, setUsername] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [leagueConnected, setLeagueConnected] = useState(false);
  const navigate = useNavigate();
  const { getToken } = useAuthToken();

  const handleUsernameSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const token = await getToken();

      if (!token) {
        throw new Error("Failed to obtain access token");
      }

      console.log("Token obtained successfully for onboarding");

      const response = await api.post(
        "/api/v1/users/complete-onboarding",
        { username },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      console.log("Username set successfully:", response.data);

      // Move to the next step
      setCurrentStep(OnboardingStep.LeagueConnection);
    } catch (error) {
      console.error("Failed to set username:", error);
      setError("Failed to set username. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleConnectLeagueAccount = async () => {
    try {
      setError("");
      setIsLoading(true);

      const token = await getToken();
      if (!token) {
        throw new Error("Authentication failed");
      }

      // Initiate the Riot authentication process
      const response = await api.get("/api/v1/auth/riot/connect", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      // Redirect to Riot login page
      window.location.href = response.data.auth_url;

      // Note: The user will be redirected back to your application
      // This flow will be continued in a callback endpoint
    } catch (error) {
      console.error("Error connecting League account:", error);
      setError(
        "Failed to start League account connection process. Please try again."
      );
      setIsLoading(false);
    }
  };

  const handleSkipLeagueConnection = () => {
    // Move to the home page
    window.location.href = "/";
  };

  // Render the appropriate step
  const renderStep = () => {
    switch (currentStep) {
      case OnboardingStep.Username:
        return (
          <>
            <h1>Welcome to League Review!</h1>
            <p>Choose a username to get started</p>

            <form onSubmit={handleUsernameSubmit} className={styles.form}>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
                className={styles.input}
                minLength={3}
                maxLength={20}
                pattern="[a-zA-Z0-9_-]+"
                title="Letters, numbers, underscore and hyphen only"
                required
              />

              {error && <div className={styles.error}>{error}</div>}

              <button
                type="submit"
                className={styles.button}
                disabled={isLoading}
              >
                {isLoading ? "Setting up..." : "Continue"}
              </button>
            </form>
          </>
        );

      case OnboardingStep.LeagueConnection:
        return (
          <>
            <div className={styles.logoContainer}>
              {/* <RiotLogo className={styles.logo} /> */}
            </div>

            <h1>Connect your League account</h1>
            <p className={styles.description}>
              Connect your League account to unlock these features:
            </p>

            <ul className={styles.benefitsList}>
              <li>Auto-fill game details when uploading videos</li>
              <li>Display your verified rank on your profile</li>
              <li>Help others find content relevant to their skill level</li>
            </ul>

            {error && <div className={styles.error}>{error}</div>}

            <div className={styles.buttonGroup}>
              <button
                className={styles.primaryButton}
                onClick={handleConnectLeagueAccount}
                disabled={isLoading}
              >
                {isLoading ? "Connecting..." : "Connect League Account"}
              </button>

              <button
                className={styles.secondaryButton}
                onClick={handleSkipLeagueConnection}
                disabled={isLoading}
              >
                Skip for now
              </button>
            </div>

            <p className={styles.note}>
              You can always connect your account later in settings.
            </p>
          </>
        );

      default:
        return null;
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>{renderStep()}</div>
    </div>
  );
};

export default OnboardingPage;
