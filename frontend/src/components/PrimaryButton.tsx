// src/components/PrimaryButton.tsx
import React from "react";

interface PrimaryButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
}

export const PrimaryButton: React.FC<PrimaryButtonProps> = ({ children, onClick, className }) => (
  <button
    onClick={onClick}
    className={`px-6 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 ${className}`}
  >
    {children}
  </button>
);
