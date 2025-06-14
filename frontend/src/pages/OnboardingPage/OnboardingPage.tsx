import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import styles from "./OnboardingPage.module.css";
import api from "../../api/axios";
import { useAuthToken } from "../../utils/auth";
import { useLeagueConnect } from "../../utils/leagueConnect";

// import RiotLogo from "../../assets/svg/RiotLogo";

const AUTH0_AUDIENCE = process.env.REACT_APP_AUTH0_AUDIENCE;

// Define onboarding steps
enum OnboardingStep {
  Username = 0,
  LeagueConnection = 1,
  Complete = 2,
}

// Region options for Riot API
const REGION_OPTIONS = [
  {
    value: "americas",
    label: "Americas",
    description: "NA, BR, LAN, LAS, OCE",
  },
  {
    value: "europe",
    label: "Europe",
    description: "EUW, EUNE, TR, RU",
  },
  {
    value: "asia",
    label: "Asia",
    description: "KR, JP, SG, PH, TH, TW, VN",
  },
];

const OnboardingPage = () => {
  const [currentStep, setCurrentStep] = useState<OnboardingStep>(
    OnboardingStep.Username
  );
  const [selectedRegion, setSelectedRegion] = useState("");
  const [username, setUsername] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [leagueConnected, setLeagueConnected] = useState(false);
  const navigate = useNavigate();
  const { getToken, user } = useAuthToken();
  const { connectLeagueAccount } = useLeagueConnect();

  const handleUsernameSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!selectedRegion) {
      setError("Please select your region");
      return;
    }

    setIsLoading(true);

    try {
      const token = await getToken();

      if (!token) {
        throw new Error("Failed to obtain access token");
      }

      console.log("Token obtained successfully for onboarding");

      const response = await api.post(
        "/api/v1/users/complete-onboarding",
        {
          username,
          profile_picture: user?.picture,
          riot_region: selectedRegion,
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      console.log("Username and region set successfully:", response.data);

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

      await connectLeagueAccount();
      // Note: This will redirect the user to Riot's auth page
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
            <h1>Welcome to Better TFT!</h1>
            <p>Set up your profile to get started</p>

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

              <div className={styles.regionSelection}>
                <label className={styles.regionLabel}>
                  Select your region:
                </label>
                <div className={styles.regionOptions}>
                  {REGION_OPTIONS.map((region) => (
                    <label key={region.value} className={styles.regionOption}>
                      <input
                        type="radio"
                        name="region"
                        value={region.value}
                        checked={selectedRegion === region.value}
                        onChange={(e) => setSelectedRegion(e.target.value)}
                        className={styles.regionRadio}
                      />
                      <div className={styles.regionContent}>
                        <div className={styles.regionTitle}>{region.label}</div>
                        <div className={styles.regionDescription}>
                          {region.description}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {error && <div className={styles.error}>{error}</div>}

              <button
                type="submit"
                className={styles.button}
                disabled={isLoading || !username.trim() || !selectedRegion}
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
                {isLoading ? (
                  "Connecting..."
                ) : (
                  <>
                    <span className={styles.buttonIcon}>
                      <svg
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        xmlns="http://www.w3.org/2000/svg"
                      >
                        <path
                          d="M20 12H4M4 12L10 6M4 12L10 18"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </span>
                    Connect League Account
                  </>
                )}
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
