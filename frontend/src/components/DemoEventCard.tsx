// src/components/DemoEventCard.tsx
import React from "react";
import { LucideIcon } from "lucide-react";

interface DemoEventCardProps {
  title: string;
  icon: LucideIcon;
  description: string;
  onClick?: () => void;
}

export const DemoEventCard: React.FC<DemoEventCardProps> = ({ title, icon: Icon, description, onClick }) => (
  <div
    className="cursor-pointer bg-white dark:bg-gray-800 rounded-lg shadow p-4 hover:shadow-md transition"
    onClick={onClick}
  >
    <div className="flex items-center space-x-3 mb-2">
      <Icon size={24} className="text-indigo-600" />
      <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">{title}</h3>
    </div>
    <p className="text-sm text-gray-600 dark:text-gray-400">{description}</p>
  </div>
);
