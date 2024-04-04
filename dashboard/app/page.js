"use client";
import React, { useEffect, useRef } from "react";

import { updateStaticDataStore } from "../lib/data";
import { state } from "../lib/state";

import { DeckGLMap } from "../components/DeckGLMap";
import { SummaryStats } from "../components/SummaryStats";
import ControlPanel from "../components/ControlPanel";
import PieChart from "../components/PieChart";
import Tooltip from "../components/Tooltip";

import "mapbox-gl/dist/mapbox-gl.css";
import "../styles/styles.css";
// import styles from "./page.module.css"; //TODO: unsure about styles import

export default function Home() {
  // load staticDataStore on page load
  useEffect(() => {
    updateStaticDataStore();
  }, []);

  // Handling resizing of container to dynamically update map bounding box
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
      <main className="flex w-full h-[100vh] relative flex">
        <div className="relative w-3/4" ref={containerRef}>
          <Tooltip />
          <DeckGLMap />
        </div>
        <div className="absolute left-4 top-4 bg-white p-2">
          <ControlPanel />
        </div>
        <div className="flex flex-col w-1/4 h-[100vh] overflow-hidden">
          <div>
            <SummaryStats />
          </div>
        </div>
      </main>
    </div>
  );
}
