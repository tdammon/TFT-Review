import React, { useEffect, useState, useRef } from "react";
import styles from "./ProfilePage.module.css";
import { useLeagueConnect } from "../../utils/leagueConnect";
import api from "../../api/axios";
import { useAuthToken } from "../../utils/auth";

// Types
import {
  MatchHistorySummary,
  MatchHistoryItem,
  User,
  PlayerRank,
} from "../../types/serverResponseTypes";

const GAME_COUNT_OPTIONS = [5, 10, 25, 50];

const ProfilePage = ({ userInfo }: { userInfo: User }) => {
  const [isConnecting, setIsConnecting] = useState(false);
  const [loadingStates, setLoadingStates] = useState({
    matchHistory: false,
    extendedMatchHistory: false,
    rankInfo: false,
  });
  const [matchHistory, setMatchHistory] = useState<MatchHistoryItem[]>([]);
  const [matchHistorySummary, setMatchHistorySummary] =
    useState<MatchHistorySummary>({
      average_placement: 0,
      first_places: 0,
      top4_rate: 0,
      total_estimated_lp_change: 0,
    });
  const [playerRank, setPlayerRank] = useState<PlayerRank | null>(null);
  const [selectedGameCount, setSelectedGameCount] = useState<number>(5);

  const { connectLeagueAccount } = useLeagueConnect();
  const { getToken } = useAuthToken();

  // Calculate stats for the current selected game count
  const displayedMatches = React.useMemo(() => {
    return matchHistory.slice(0, selectedGameCount);
  }, [matchHistory, selectedGameCount]);

  // Determine if we have enough data for the selected count
  const hasEnoughData = React.useMemo(() => {
    return displayedMatches.length >= selectedGameCount;
  }, [displayedMatches.length, selectedGameCount]);

  // Calculate summary stats based on displayed matches
  const displayedSummary = React.useMemo(() => {
    if (displayedMatches.length === 0) return matchHistorySummary;

    const avgPlacement =
      displayedMatches.reduce((sum, match) => sum + match.placement, 0) /
      displayedMatches.length;
    const firstPlaces = displayedMatches.filter(
      (match) => match.placement === 1
    ).length;
    const top4Count = displayedMatches.filter(
      (match) => match.placement <= 4
    ).length;
    const top4Rate = top4Count / displayedMatches.length;
    const totalLpChange = displayedMatches.reduce(
      (sum, match) => sum + match.estimated_lp_change,
      0
    );

    return {
      average_placement: avgPlacement,
      first_places: firstPlaces,
      top4_rate: top4Rate,
      total_estimated_lp_change: totalLpChange,
    };
  }, [displayedMatches, matchHistorySummary]);

  // Compute loading state based on current data and selected count
  const isLoading = React.useMemo(() => {
    // Always show loading if we're fetching initial data
    if (loadingStates.matchHistory || loadingStates.rankInfo) {
      return true;
    }

    // If we're fetching extended data AND the user wants to see more than 5 matches
    // AND we don't have enough data yet
    if (
      loadingStates.extendedMatchHistory &&
      selectedGameCount > 5 &&
      !hasEnoughData
    ) {
      return true;
    }

    // If the user selected more than we have data for and extended data isn't loaded yet
    if (
      selectedGameCount > displayedMatches.length &&
      !loadingStates.extendedMatchHistory &&
      matchHistory.length <= 5
    ) {
      return true;
    }

    return false;
  }, [
    loadingStates.matchHistory,
    loadingStates.rankInfo,
    loadingStates.extendedMatchHistory,
    selectedGameCount,
    displayedMatches.length,
    hasEnoughData,
    matchHistory.length,
  ]);

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
            match_count: 5,
            initial_count: 0,
          },
        });

        console.log("5 matches", response.data);
        setMatchHistory(response.data.rating_history);
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

    const fetchExtendedRatingHistory = async () => {
      setLoadingStates((prev) => ({ ...prev, extendedMatchHistory: true }));
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
            match_count: 45,
            initial_count: 5,
          },
        });

        console.log("45 matches", response.data);
        setMatchHistory((prevHistory) => {
          console.log("prevHistory", prevHistory);
          const combinedHistory = [
            ...prevHistory,
            ...response.data.rating_history,
          ];

          // Sort by timestamp to ensure proper ordering
          return combinedHistory.sort((a, b) => b.timestamp - a.timestamp);
        });
      } catch (error) {
        console.error("Failed to fetch extended rating history:", error);
      } finally {
        setLoadingStates((prev) => ({ ...prev, extendedMatchHistory: false }));
      }
    };

    // Execute fetch operations
    fetchPlayerRank();
    fetchRatingHistory();
    fetchExtendedRatingHistory();
  }, [userInfo.riot_puuid]);

  const handleGameCountChange = (gameCount: number) => {
    setSelectedGameCount(gameCount);
    // The useEffect will re-fetch the data when selectedGameCount changes
  };

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
            <>
              <div className={styles.tabsContainer}>
                {GAME_COUNT_OPTIONS.map((count) => (
                  <button
                    key={count}
                    className={`${styles.tabButton} ${
                      selectedGameCount === count ? styles.activeTab : ""
                    }`}
                    onClick={() => handleGameCountChange(count)}
                  >
                    Last {count} Games
                  </button>
                ))}
              </div>

              {isLoading ? (
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
                        {formatAvgPlacement(displayedSummary.average_placement)}
                      </p>
                    </div>
                  </div>
                  <div className={styles.profileStatItem}>
                    <div className={styles.profileStatItemHeader}>
                      <h3>First Places</h3>
                    </div>
                    <div className={styles.profileStatItemContent}>
                      <p>{displayedSummary.first_places}</p>
                    </div>
                  </div>
                  <div className={styles.profileStatItem}>
                    <div className={styles.profileStatItemHeader}>
                      <h3>Top 4 Rate</h3>
                    </div>
                    <div className={styles.profileStatItemContent}>
                      <p>{formatTopFourRate(displayedSummary.top4_rate)}</p>
                    </div>
                  </div>
                  <div className={styles.profileStatItem}>
                    <div className={styles.profileStatItemHeader}>
                      <h3>Total LP Change</h3>
                    </div>
                    <div className={styles.profileStatItemContent}>
                      <p
                        className={
                          displayedSummary.total_estimated_lp_change >= 0
                            ? styles.positiveLP
                            : styles.negativeLP
                        }
                      >
                        {displayedSummary.total_estimated_lp_change > 0
                          ? "+"
                          : ""}
                        {displayedSummary.total_estimated_lp_change}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </>
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
