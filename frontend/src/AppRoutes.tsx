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

const AppRoutes = () => {
  const { isAuthenticated, isLoading } = useAuth0();
  const { getToken } = useAuthToken();
  const [hasUsername, setHasUsername] = useState<boolean | null>(null);
  const [checkingUsername, setCheckingUsername] = useState(true);

  useEffect(() => {
    const checkUsername = async () => {
      if (isAuthenticated) {
        try {
          const token = await getToken();

          if (!token) {
            throw new Error("Access token is undefined");
          }

          console.log("Token obtained successfully");
          console.log("Checking username at:", new Date().toISOString());

          // Use axios instance with proper baseURL
          const response = await api.get("/api/v1/users/me", {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });

          console.log("Response status:", response.status);
          console.log("Response data:", response.data);

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
  }, [isAuthenticated, getToken]);

  if (isLoading || checkingUsername) {
    return <LoadingScreen />;
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  // If authenticated but no username, show onboarding
  if (hasUsername === false) {
    return <OnboardingPage />;
  }

  // Only show main app routes if user has completed onboarding
  if (hasUsername === true) {
    return (
      <Routes>
        <Route element={<AuthLayout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/video/:videoId" element={<VideoAnalysis />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    );
  }

  // Fallback loading state while checking username
  return <LoadingScreen />;
};

export default AppRoutes;
