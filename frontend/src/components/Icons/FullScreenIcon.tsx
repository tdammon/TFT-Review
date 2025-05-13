export const FullscreenIcon = ({
  height = "16",
  width = "16",
  stroke = "currentColor",
}) => (
  <svg
    width={width}
    height={height}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path d="M3 3H9V5H5V9H3V3Z" fill={stroke} />
    <path d="M3 21H9V19H5V15H3V21Z" fill={stroke} />
    <path d="M21 3H15V5H19V9H21V3Z" fill={stroke} />
    <path d="M21 21H15V19H19V15H21V21Z" fill="currentColor" />
  </svg>
);
