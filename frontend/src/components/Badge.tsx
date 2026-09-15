// src/components/Badge.tsx
import React from "react";

interface BadgeProps {
  children: React.ReactNode;
  color?: "gray" | "red" | "green" | "yellow" | "blue";
}

export const Badge: React.FC<BadgeProps> = ({ children, color = "gray" }) => {
  const colorClasses = {
    gray: "bg-gray-200 text-gray-800",
    red: "bg-red-200 text-red-800",
    green: "bg-green-200 text-green-800",
    yellow: "bg-yellow-200 text-yellow-800",
    blue: "bg-blue-200 text-blue-800",
  }[color];

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClasses}`}> {children} </span>
  );
};
