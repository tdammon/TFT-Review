import React, { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import LoginPage from "./pages/LoginPage/LoginPage";
import LoadingScreen from "./components/LoadingScreen/LoadingScreen";
import HomePage from "./pages/HomePage/HomePage";
import VideoAnalysis from "./pages/VideoAnalysis/VideoAnalysis";
import OnboardingPage from "./pages/OnboardingPage/OnboardingPage";
import AuthLayout from "./layouts/AuthLayout";
import { useAuthToken } from "./utils/auth";
import api from "./api/axios";

interface User {
  discord_connected: boolean;
  id: number;
  username: string;
  email: string;
  profile_picture: string;
  verified_riot_account: boolean;
}

const AppRoutes = () => {
  const { isAuthenticated, isLoading } = useAuth0();
  const { getToken } = useAuthToken();
  const [hasUsername, setHasUsername] = useState<boolean | null>(null);
  const [checkingUsername, setCheckingUsername] = useState(true);
  const [userInfo, setUserInfo] = useState<User | null>(null);

  useEffect(() => {
    const checkUsername = async () => {
      if (isAuthenticated) {
        try {
          const token = await getToken();

          if (!token) {
            throw new Error("Access token is undefined");
          }

          // Use axios instance with proper baseURL
          const response = await api.get("/api/v1/users/me", {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });

          setUserInfo(response.data);

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
          setHasUsername(false);
        }
      }
      setCheckingUsername(false);
    };

    checkUsername();
  }, [isAuthenticated]);

  if (isLoading || checkingUsername) {
    return <LoadingScreen />;
  }

  if (!isAuthenticated) {
    return <LoginPage />;
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
            element={<VideoAnalysis userInfo={userInfo} />}
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

  // Fallback loading state while checking username
  return <LoadingScreen />;
};

export default AppRoutes;
