// src/components/ChartPlaceholder.tsx
import React from "react";

export const ChartPlaceholder: React.FC<{title:string}> = ({title}) => (
  <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 h-64 flex flex-col justify-center items-center">
    <p className="text-gray-500 dark:text-gray-400">{title} Chart Placeholder</p>
  </div>
);
