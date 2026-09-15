// src/components/KpiCard.tsx
import React from "react";
import { LucideIcon } from "lucide-react";

interface KpiCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  color?: string; // Tailwind color class e.g. "text-blue-500"
}

export const KpiCard: React.FC<KpiCardProps> = ({ title, value, icon: Icon, color = "text-blue-500" }) => {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 flex items-center space-x-4">
      <div className={`flex-shrink-0 ${color}`}>
        <Icon size={32} />
      </div>
      <div>
        <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</p>
        <p className="text-2xl font-semibold text-gray-900 dark:text-gray-100">{value}</p>
      </div>
    </div>
  );
};
