import api from "../api/axios";
import { useAuthToken } from "./auth";

/**
 * Initiates the League of Legends account connection process
 * @param token - Auth token for the API request
 * @returns Promise with the redirect URL or an error
 */
export const initiateLeagueConnection = async (
  token: string
): Promise<string> => {
  try {
    if (!token) {
      throw new Error("Authentication failed: No token provided");
    }

    // Initiate the Riot authentication process
    const response = await api.get("/api/v1/auth/riot/connect", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    // Return the auth URL for redirection
    return response.data.auth_url;
  } catch (error) {
    console.error("Error connecting League account:", error);
    throw error;
  }
};

/**
 * Custom hook for League account connection functionality
 */
export const useLeagueConnect = () => {
  const { getToken } = useAuthToken();

  const connectLeagueAccount = async (): Promise<void> => {
    try {
      const token = await getToken();

      if (!token) {
        throw new Error("Authentication failed");
      }

      const authUrl = await initiateLeagueConnection(token);

      // Redirect to Riot login page
      window.location.href = authUrl;
    } catch (error) {
      console.error("Error connecting League account:", error);
      throw error;
    }
  };

  return { connectLeagueAccount };
};
