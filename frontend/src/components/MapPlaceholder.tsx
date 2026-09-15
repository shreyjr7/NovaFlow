// src/components/MapPlaceholder.tsx
import React from "react";
import { LiveGisMap } from "./LiveGisMap";

export const MapPlaceholder: React.FC<{ height?: string }> = ({ height = "480px" }) => (
  <LiveGisMap height={height} />
);

export default MapPlaceholder;
