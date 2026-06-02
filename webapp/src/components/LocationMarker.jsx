import React from "react";
import { Marker } from "react-leaflet";

export default function LocationMarker({ position }) {
  return (
    <Marker position={position} icon={L.divIcon({
      className: 'location-marker',
      html: `
        <div style="
          width: 24px; height: 24px; border-radius: 50%;
          background: #4285F4; border: 3px solid #fff;
          box-shadow: 0 2px 8px rgba(66,133,244,0.3);
        "></div>
      `,
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    })} />
  );
}
