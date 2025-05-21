export interface Comment {
  id: string;
  content: string;
  video_timestamp: number;
  user_username: string;
  user_profile_picture?: string;
  created_at: string;
  updated_at: string;
  parent_id?: string;
}

export interface Event {
  id: string;
  title: string;
  description?: string;
  video_timestamp: number;
  event_type?: string;
  user_username: string;
  created_at: string;
  updated_at: string;
}

export interface MatchHistorySummary {
  average_placement: number;
  first_places: number;
  top4_rate: number;
  total_estimated_lp_change: number;
}

export interface MatchHistoryItem {
  match_id: string;
  timestamp: number;
  date: string;
  placement: number;
  estimated_lp_change: number;
  lp_after_game?: number;
  promotion?: boolean;
  demotion?: boolean;
}

export interface VideoDetails {
  id: string;
  title: string;
  description: string | null;
  video_url: string | null;
  thumbnail_url: string | null;
  views: number;
  user_id: string;
  created_at: string;
  comments: Comment[];
  events: Event[];
}

export interface PlayerRank {
  tier: string | null;
  rank: string | null;
  lp: number;
  formatted_rank: string;
  wins: number;
  losses: number;
  win_rate: number;
  is_ranked: boolean;
}

export interface User {
  discord_connected: boolean;
  id: string;
  username: string;
  email: string;
  profile_picture: string;
  verified_riot_account: boolean;
  riot_puuid: string;
  riot_region?: string;
}
