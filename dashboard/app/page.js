"use client";
import React, { useEffect, useRef } from "react";

import { updateStaticDataStore } from "@/lib/data";
import { state } from "@/lib/state";

import { DeckGLMap } from "@/components/DeckGLMap";
import { SummaryStats } from "@/components/SummaryStats";
import ControlPanel from "@/components/ControlPanel";
import Tooltip from "@/components/Tooltip";

import "mapbox-gl/dist/mapbox-gl.css";
import "@/styles/styles.css";

export default function Home() {
  // Note: load staticDataStore on page load
  useEffect(() => {
    updateStaticDataStore();
  }, []);

  // Note: Handling resizing of container to dynamically update map bounding box
  const containerRef = useRef(null);

  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        const width = containerRef.current.getBoundingClientRect().width;
        const height = containerRef.current.getBoundingClientRect().height;
        state.map.containerWidth = width;
        state.map.containerHeight = height;
      }
    };

    handleResize();
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  return (
    <div>
      <div className="lg:hidden h-[100vh] flex align-center m-4 justify-center">
        <h3>
          The poultry dashboard is designed for viewing on desktop. Please use a
          device that is at least 1024 pixels wide to view the dashboard.
        </h3>
      </div>
      <div className="hidden lg:block" id="report-widget">
        <main className="flex w-full h-[100vh] relative bg-white">
          <div className="relative size-full" ref={containerRef}>
            <Tooltip />
            <DeckGLMap />
          </div>
          <div className="absolute left-4 top-4 p-2 max-w-[75%] max-h-[75%] overflow-hidden bg-white">
            <ControlPanel />
          </div>
          <div className="flex-none w-[342px] h-full overflow-x-hidden">
            <div className="flex flex-col">
              <SummaryStats />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
