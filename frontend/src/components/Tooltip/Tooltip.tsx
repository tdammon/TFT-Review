import React, { useState, ReactNode } from "react";
import styles from "./Tooltip.module.css";

interface TooltipProps {
  children: ReactNode;
  text: string;
  position?: "top" | "right" | "bottom" | "left";
}

const Tooltip: React.FC<TooltipProps> = ({
  children,
  text,
  position = "top",
}) => {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <div
      className={styles.tooltipContainer}
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
    >
      {children}
      {isVisible && (
        <div className={`${styles.tooltip} ${styles[position]}`}>{text}</div>
      )}
    </div>
  );
};

export default Tooltip;
