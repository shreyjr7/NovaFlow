// src/components/FleetStatus.tsx
import React from "react";
import { LucideIcon } from "lucide-react";
import { Badge } from "./Badge"; // assume simple badge component exists

interface FleetStatusProps {
  online: number;
  offline: number;
  warning: number;
  icon: LucideIcon;
}

export const FleetStatus: React.FC<FleetStatusProps> = ({ online, offline, warning, icon: Icon }) => (
  <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
    <div className="flex items-center mb-4">
      <Icon size={24} className="text-green-600 mr-2" />
      <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Fleet Status</h2>
    </div>
    <div className="flex space-x-4">
      <Badge color="green">Online: {online}</Badge>
      <Badge color="red">Offline: {offline}</Badge>
      <Badge color="yellow">Warning: {warning}</Badge>
    </div>
  </div>
);
