// src/components/Header.tsx
import React from "react";

export const Header: React.FC = () => (
  <header className="py-6 text-center">
    <h1 className="text-4xl sm:text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-indigo-300 to-purple-400 tracking-tight">
      NovaFlow
    </h1>
    <p className="mt-2 text-sm sm:text-base text-gray-400 font-medium">
      AI-Powered Mobile Urban Intelligence & Fleet Sensing Platform
    </p>
  </header>
);

export default Header;
