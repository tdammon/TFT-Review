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

export interface User {
  discord_connected: boolean;
  id: string;
  username: string;
  email: string;
  profile_picture: string;
  verified_riot_account: boolean;
}
