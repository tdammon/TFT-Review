import React, { useEffect, useState } from "react";
import styles from "./ProfilePage.module.css";
import { useLeagueConnect } from "../../utils/leagueConnect";
import api from "../../api/axios";
import { useAuthToken } from "../../utils/auth";

// Types
import {
  MatchHistorySummary,
  User,
  PlayerRank,
} from "../../types/serverResponseTypes";

const ProfilePage = ({ userInfo }: { userInfo: User }) => {
  const [isConnecting, setIsConnecting] = useState(false);
  const [loadingStates, setLoadingStates] = useState({
    matchHistory: false,
    rankInfo: false,
  });
  const [matchHistorySummary, setMatchHistorySummary] =
    useState<MatchHistorySummary>({
      average_placement: 0,
      first_places: 0,
      top4_rate: 0,
      total_estimated_lp_change: 0,
    });
  const [playerRank, setPlayerRank] = useState<PlayerRank | null>(null);
  const { connectLeagueAccount } = useLeagueConnect();
  const { getToken } = useAuthToken();

  // Compute a single loading state from individual loading states
  const isLoading = loadingStates.matchHistory || loadingStates.rankInfo;

  useEffect(() => {
    if (!userInfo.riot_puuid) return;

    // Fetch rating history
    const fetchRatingHistory = async () => {
      setLoadingStates((prev) => ({ ...prev, matchHistory: true }));
      try {
        const token = await getToken();
        if (!token) {
          throw new Error("Failed to obtain access token");
        }
        const response = await api.get("/api/v1/tft/rating-history", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
          params: {
            match_count: 20,
          },
        });

        setMatchHistorySummary(response.data.summary);
      } catch (error) {
        console.error("Failed to fetch rating history:", error);
      } finally {
        setLoadingStates((prev) => ({ ...prev, matchHistory: false }));
      }
    };

    // Fetch player rank
    const fetchPlayerRank = async () => {
      setLoadingStates((prev) => ({ ...prev, rankInfo: true }));
      try {
        const token = await getToken();
        if (!token) {
          throw new Error("Failed to obtain access token");
        }
        const response = await api.get("/api/v1/tft/rank", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        console.log("response", response.data);
        setPlayerRank(response.data);
      } catch (error) {
        console.error("Failed to fetch rank info:", error);
      } finally {
        setLoadingStates((prev) => ({ ...prev, rankInfo: false }));
      }
    };

    // Execute both fetch operations
    fetchPlayerRank();
    fetchRatingHistory();
  }, [userInfo.riot_puuid]);

  const handleConnectLeagueAccount = async () => {
    try {
      setIsConnecting(true);
      await connectLeagueAccount();
      // Note: This will redirect the user, so the rest of the function won't execute
    } catch (error) {
      console.error("Failed to connect League account:", error);
      setIsConnecting(false);
    }
  };

  const formatTopFourRate = (rate: number) => {
    return `${(rate * 100).toFixed(1)}%`;
  };

  const formatAvgPlacement = (placement: number) => {
    return placement?.toFixed(2);
  };

  return (
    <div className={styles.container}>
      <main className={styles.main}>
        <div className={styles.profileHeader}>
          <div className={styles.profilePictureContainer}>
            <img
              src={
                userInfo.profile_picture || "https://via.placeholder.com/100"
              }
              alt="Profile"
              className={styles.profilePicture}
            />
          </div>
          <div className={styles.profileInfoContainer}>
            <div className={styles.profileName}>{userInfo.username}</div>
            {userInfo.verified_riot_account && playerRank && (
              <div className={styles.profileAccountRating}>
                {playerRank.formatted_rank || "TFT Player"}
              </div>
            )}
          </div>
          <div className={styles.profileConnectContainer}>
            <button
              className={styles.connectButton}
              onClick={handleConnectLeagueAccount}
              disabled={isConnecting || userInfo.verified_riot_account}
            >
              {isConnecting
                ? "Connecting..."
                : !userInfo.verified_riot_account
                ? "Connect League Account"
                : "Connected"}
            </button>
          </div>
        </div>

        <div className={styles.profileRankingContainer}>
          {userInfo.verified_riot_account ? (
            isLoading ? (
              <div className={styles.connectLeagueAccountContainer}>
                <div className={styles.loadingSpinner}></div>
                Loading stats...
              </div>
            ) : (
              <div className={styles.profileStatsContainer}>
                <div className={styles.profileStatItem}>
                  <div className={styles.profileStatItemHeader}>
                    <h3>Average Placement</h3>
                  </div>
                  <div className={styles.profileStatItemContent}>
                    <p>
                      {formatAvgPlacement(
                        matchHistorySummary.average_placement
                      )}
                    </p>
                  </div>
                </div>
                <div className={styles.profileStatItem}>
                  <div className={styles.profileStatItemHeader}>
                    <h3>First Places</h3>
                  </div>
                  <div className={styles.profileStatItemContent}>
                    <p>{matchHistorySummary.first_places}</p>
                  </div>
                </div>
                <div className={styles.profileStatItem}>
                  <div className={styles.profileStatItemHeader}>
                    <h3>Top 4 Rate</h3>
                  </div>
                  <div className={styles.profileStatItemContent}>
                    <p>{formatTopFourRate(matchHistorySummary.top4_rate)}</p>
                  </div>
                </div>
                <div className={styles.profileStatItem}>
                  <div className={styles.profileStatItemHeader}>
                    <h3>Total LP Change</h3>
                  </div>
                  <div className={styles.profileStatItemContent}>
                    <p
                      className={
                        matchHistorySummary.total_estimated_lp_change >= 0
                          ? styles.positiveLP
                          : styles.negativeLP
                      }
                    >
                      {matchHistorySummary.total_estimated_lp_change > 0
                        ? "+"
                        : ""}
                      {matchHistorySummary.total_estimated_lp_change}
                    </p>
                  </div>
                </div>
              </div>
            )
          ) : (
            <div className={styles.connectLeagueAccountContainer}>
              <div className={styles.connectPromptIcon}>🎮</div>
              Connect your League account to see your TFT stats
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default ProfilePage;
