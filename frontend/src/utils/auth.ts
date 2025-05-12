import { useAuth0 } from "@auth0/auth0-react";

// Auth0 configuration
const AUTH0_AUDIENCE = process.env.REACT_APP_AUTH0_AUDIENCE;

/**
 * Utility function to get the Auth0 access token directly from localStorage
 * This bypasses the getAccessTokenSilently method which may have cross-domain restrictions
 */
export const getAccessTokenFromStorage = (): string | null => {
  try {
    // Find all Auth0 cache keys
    const cacheKeys = Object.keys(localStorage).filter((key) =>
      key.startsWith("@@auth0spajs@@")
    );

    if (cacheKeys.length === 0) {
      console.warn("No Auth0 cache keys found in localStorage");
      return null;
    }

    console.log("Found Auth0 cache keys:", cacheKeys);

    // Try to find any valid token in any of the cache entries
    for (const cacheKey of cacheKeys) {
      try {
        const cacheData = JSON.parse(localStorage.getItem(cacheKey) || "{}");

        // Find any token entry
        const tokenEntries = Object.values(cacheData).filter(
          (entry: any) =>
            entry && typeof entry === "object" && entry.access_token
        );

        if (tokenEntries.length > 0) {
          const token = (tokenEntries[0] as any).access_token;

          if (token) {
            console.log(`Found token in cache key: ${cacheKey}`);

            // Check if it's a JWT (has 3 parts separated by dots)
            const parts = token.split(".");
            if (parts.length === 3) {
              console.log("Token appears to be a JWT (3 parts)");
            } else {
              console.log("Token appears to be an opaque token (not a JWT)");
            }

            return token;
          }
        }
      } catch (e) {
        console.warn(`Error parsing cache key ${cacheKey}:`, e);
        // Continue to next cache key
      }
    }

    console.warn("No valid tokens found in any Auth0 cache entries");
    return null;
  } catch (error) {
    console.error("Error extracting token from localStorage:", error);
    return null;
  }
};

/**
 * Custom hook that provides access to tokens, either via Auth0 methods or direct localStorage access
 */
export const useAuthToken = () => {
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();

  const getToken = async (): Promise<string | null> => {
    if (!isAuthenticated) return null;

    try {
      // First try the official method - without explicit scope parameter
      const token = await getAccessTokenSilently({
        authorizationParams: {
          audience: AUTH0_AUDIENCE,
          // No explicit scope - using default scopes from Auth0 configuration
        },
        timeoutInSeconds: 5, // Set a short timeout
      }).catch(() => null);

      if (token) {
        return token;
      }

      // Fall back to direct localStorage access if the official method fails
      console.log("Falling back to direct localStorage access for token");
      return getAccessTokenFromStorage();
    } catch (error) {
      console.error("Error getting token:", error);
      return getAccessTokenFromStorage();
    }
  };

  return { getToken };
};
