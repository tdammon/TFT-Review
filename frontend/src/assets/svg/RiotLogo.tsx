import React from "react";

interface RiotLogoProps {
  className?: string;
  width?: number;
  height?: number;
}

const RiotLogo: React.FC<RiotLogoProps> = ({
  className,
  width = 80,
  height = 80,
}) => {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 200 200"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      <g fill="#D13639">
        <path d="M41.3086 71.88H67.3686V128H41.3086V71.88Z" />
        <path d="M144.879 128V71.88H170.939V128H144.879Z" />
        <path d="M133.869 71.88V95.39H118.349V71.88H92.2988V128H118.349V112.27H133.869V128H159.919V71.88H133.869Z" />
        <path d="M100 38.5C65.2722 38.5 37.25 66.5222 37.25 101.25C37.25 135.978 65.2722 164 100 164C134.728 164 162.75 135.978 162.75 101.25C162.75 66.5222 134.728 38.5 100 38.5ZM100 45.5C130.841 45.5 155.75 70.4091 155.75 101.25C155.75 132.091 130.841 157 100 157C69.1591 157 44.25 132.091 44.25 101.25C44.25 70.4091 69.1591 45.5 100 45.5Z" />
      </g>
    </svg>
  );
};

export default RiotLogo;
