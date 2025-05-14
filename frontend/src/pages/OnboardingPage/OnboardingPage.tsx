import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import styles from "./OnboardingPage.module.css";
import api from "../../api/axios";
import { useAuthToken } from "../../utils/auth";

const AUTH0_AUDIENCE = process.env.REACT_APP_AUTH0_AUDIENCE;

const OnboardingPage = () => {
  const [username, setUsername] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { getToken } = useAuthToken();

  const handleSubmit = async (e: React.FormEvent) => {
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

      console.log("Onboarding completed successfully:", response.data);

      // Force a full page reload to ensure state is refreshed
      window.location.href = "/";

      // The navigate function below won't be reached due to the page reload
      // navigate("/");
    } catch (error) {
      console.error("Failed to complete onboarding:", error);
      setError("Failed to complete onboarding. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h1>Welcome to League Review!</h1>
        <p>Choose a username to get started</p>

        <form onSubmit={handleSubmit} className={styles.form}>
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

          <button type="submit" className={styles.button} disabled={isLoading}>
            {isLoading ? "Setting up..." : "Continue"}
          </button>
        </form>
      </div>
    </div>
  );
};

export default OnboardingPage;
