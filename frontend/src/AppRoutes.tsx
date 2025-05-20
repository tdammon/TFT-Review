import { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import LoginPage from "./pages/LoginPage/LoginPage";
import LoadingScreen from "./components/LoadingScreen/LoadingScreen";
import HomePage from "./pages/HomePage/HomePage";
import VideoAnalysis from "./pages/VideoAnalysis/VideoAnalysis";
import OnboardingPage from "./pages/OnboardingPage/OnboardingPage";
import EventCreation from "./components/EventCreation/EventCreation";
import AuthLayout from "./layouts/AuthLayout";
import { useAuthToken } from "./utils/auth";
import api from "./api/axios";

// Types
import { User } from "./types/serverResponseTypes";

const AppRoutes = () => {
  const { isAuthenticated, isLoading } = useAuth0();
  const { getToken } = useAuthToken();
  const [hasUsername, setHasUsername] = useState<boolean | null>(null);
  const [checkingUsername, setCheckingUsername] = useState(true);
  const [userInfo, setUserInfo] = useState<User | null>(null);
  const [serverError, setServerError] = useState(false);

  useEffect(() => {
    const checkUsername = async () => {
      if (isAuthenticated) {
        try {
          const token = await getToken();

          if (!token) {
            throw new Error("Access token is undefined");
          }

          const response = await api.get("/api/v1/users/me", {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });

          setUserInfo(response.data);
          setServerError(false);

          // Check if username exists and is not a temporary username
          const username = response.data.username;
          const isTempUsername = username && username.startsWith("user_");
          setHasUsername(!!username && !isTempUsername);

          if (isTempUsername) {
            console.log(
              "User has temporary username, redirecting to onboarding"
            );
            setHasUsername(false);
          }
        } catch (error) {
          console.error("Failed to check username:", error);
          setServerError(true);
        }
      }
      setCheckingUsername(false);
    };

    checkUsername();
  }, [isAuthenticated]);

  if (isLoading || checkingUsername) {
    return <LoadingScreen />;
  }

  // Public routes accessible without authentication
  if (!isAuthenticated) {
    return (
      <Routes>
        <Route
          path="/video/:videoId"
          element={<VideoAnalysis userInfo={null} />}
        />
        <Route path="*" element={<LoginPage />} />
      </Routes>
    );
  }

  // Show error screen if we encountered server issues
  if (serverError) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          padding: "20px",
          textAlign: "center",
        }}
      >
        <h2>Unable to connect to server</h2>
        <p>
          We're having trouble connecting to our servers. Please try again
          later.
        </p>
        <button
          onClick={() => window.location.reload()}
          style={{
            padding: "10px 20px",
            marginTop: "20px",
            cursor: "pointer",
            background: "#4a90e2",
            color: "white",
            border: "none",
            borderRadius: "4px",
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  // Only show main app routes if user has completed onboarding
  if (hasUsername === true) {
    return (
      <Routes>
        <Route element={<AuthLayout />}>
          {userInfo && (
            <Route path="/" element={<HomePage userInfo={userInfo} />} />
          )}
          <Route
            path="/video/:videoId"
            element={<VideoAnalysis userInfo={userInfo as User | null} />}
          />
          <Route
            path="/video/:videoId/add-events"
            element={<EventCreation />}
          />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    );
  }

  // If authenticated but no username, show onboarding
  if (hasUsername === false) {
    return <OnboardingPage />;
  }

  // Fallback loading state while checking username
  return <LoadingScreen />;
};

export default AppRoutes;
