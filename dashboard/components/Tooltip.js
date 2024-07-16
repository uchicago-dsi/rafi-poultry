"use client";
import React from "react";
import { useSnapshot } from "valtio";

import { tooltipState } from "@/lib/state";

//TODO: should I just use the snapshot here or pass as args?
export default function Tooltip() {
  const snap = useSnapshot(tooltipState);

  if (typeof snap.hoveredObject === "undefined") {
    return "";
  } else {
    const tooltipPosition = {
      position: "absolute",
      top: `${snap.y}px`,
      left: `${snap.x}px`,
    };

    console.log(snap.hoveredObject.properties);

    if ("corp_access" in snap.hoveredObject.properties) {
      // TODO: Set this up to log corporation access
      if (snap.hoveredObject.properties.corp_access == 1) {
        return (
          <div className="tooltip" style={tooltipPosition}>
            <div>
              <b>
                Corporation Access:{" "}
                {snap.hoveredObject.properties["Parent Corporation"]}
              </b>
            </div>
          </div>
        );
      } else {
        return "";
      }
    } else {
      return (
        <div className="tooltip" style={tooltipPosition}>
          <div>
            <b>{snap.hoveredObject.properties["Establishment Name"]}</b>
          </div>
          <div>
            <b>{snap.hoveredObject.properties["Address"]}</b>
          </div>
          <div>
            <b>
              {snap.hoveredObject.properties["City"]}{" "}
              {snap.hoveredObject.properties["State"]}{" "}
              {snap.hoveredObject.properties["Zip"]}
            </b>
          </div>
          <div>
            <b>
              Parent Corporation:{" "}
              {snap.hoveredObject.properties["Parent Corporation"]}
            </b>
          </div>
        </div>
      );
    }
  }
}
