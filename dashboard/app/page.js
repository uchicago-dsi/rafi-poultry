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
      <div className="block lg:hidden">
        Please use a device that is at least 1024 pixels wide to view the
        poultry dashboard.
      </div>
      <div className="hidden lg:block">
        <main className="flex w-full h-[100vh] relative">
          <div className="relative w-[682px] h-full" ref={containerRef}>
            <Tooltip />
            <DeckGLMap />
          </div>
          <div className="absolute left-4 top-4 bg-white p-2 max-w-[75%] max-h-[75%] overflow-hidden">
            <ControlPanel />
          </div>
          <div className="flex flex-col h-[100vh] w-[342px] overflow-hidden">
            <SummaryStats />
          </div>
        </main>
      </div>
    </div>
  );
}
