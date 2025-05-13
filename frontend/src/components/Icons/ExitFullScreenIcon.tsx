export const ExitFullscreenIcon = ({
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
    <path d="M9 3V9H3V3H9Z" fill={stroke} />
    <path d="M9 21V15H3V21H9Z" fill={stroke} />
    <path d="M21 3V9H15V3H21Z" fill={stroke} />
    <path d="M21 21V15H15V21H21Z" fill={stroke} />
  </svg>
);
