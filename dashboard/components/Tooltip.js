"use client";
import React, { useState, useEffect } from "react";
import { useSnapshot } from "valtio";

import { state } from "../lib/state";

//TODO: should I just use the snapshot here or pass as args?
export default function Tooltip() {
  const snapshot = useSnapshot(state.map);

  if (typeof snapshot.hoveredObject === "undefined") {
    return "";
  } else {
    const tooltipPosition = {
      position: "absolute",
      top: `${snapshot.y}px`,
      left: `${snapshot.x}px`,
    };

    console.log(snapshot.hoveredObject.properties)

    if ("corp_access" in snapshot.hoveredObject.properties) {
      // TODO: Set this up to log corporation access
      if (snapshot.hoveredObject.properties.corp_access == 1) {
        return (
          <div className="tooltip" style={tooltipPosition}>
            <div>
              <b>
                Corporation Access:{" "}
                {snapshot.hoveredObject.properties["Parent Corporation"]}
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
            <b>{snapshot.hoveredObject.properties["Establishment Name"]}</b>
          </div>
          <div>
            <b>{snapshot.hoveredObject.properties["Address"]}</b>
          </div>
          <div>
            <b>{snapshot.hoveredObject.properties["City"]} {snapshot.hoveredObject.properties["State"]} {snapshot.hoveredObject.properties["Zip"]}</b>
          </div>
          <div>
            <b>
              Parent Corporation:{" "}
              {snapshot.hoveredObject.properties["Parent Corporation"]}
            </b>
          </div>
        </div>
      );
    }
  }
}
