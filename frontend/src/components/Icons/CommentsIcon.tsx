import React from "react";

export const CommentsIcon = ({
  height = "24",
  width = "24",
  stroke = "currentColor",
}) => (
  <svg
    width={width}
    height={height}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M21 12C21 16.9706 16.9706 21 12 21C10.2289 21 8.57736 20.5211 7.16899 19.6805L3 21L4.3195 16.831C3.47886 15.4226 3 13.7711 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z"
      stroke={stroke}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      fill="rgba(255, 255, 255, 0.1)"
    />
    <line
      x1="8"
      y1="10"
      x2="16"
      y2="10"
      stroke={stroke}
      strokeWidth="1.5"
      strokeLinecap="round"
    />
    <line
      x1="8"
      y1="14"
      x2="13"
      y2="14"
      stroke={stroke}
      strokeWidth="1.5"
      strokeLinecap="round"
    />
  </svg>
);

export default CommentsIcon;
