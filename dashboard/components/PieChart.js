"use client";
import React, { useState, useEffect, useMemo } from "react";
import { useSnapshot } from "valtio";
import { useMapData } from "@/lib/useMapData";
import { state } from "../lib/state";

import { Pie } from "react-chartjs-2";
import { Chart, ArcElement, Legend, Tooltip } from "chart.js";
Chart.register(ArcElement, Legend, Tooltip);

export default function PieChart() {
  const {
    isDataLoaded,
    filteredSales,
    capturedAreas,
    totalFarms,
    filteredCaptureAreas
  } = useMapData();

  const snapshot = useSnapshot(state.data);

  const { cleanedChartData, cleanedChartLabels } = useMemo(() => {
    if (!isDataLoaded) {
      return {
        cleanedChartData: [],
        cleanedChartLabels: [],
      };
    }

    // const data = Object.entries(snapshot.filteredSales);
    const data = Object.entries(capturedAreas);
    const top4 = data.slice(0, 3);
    const labels = top4.map(([key, value]) => key);
    const values = top4.map(([key, value]) => value * 100);

    const remaining = data
      .slice(3)
      .map(([key, value]) => value)
      .reduce((a, b) => a + b, 0);

    return {
      cleanedChartData: [...values, remaining],
      cleanedChartLabels: ["1 Integrator", "2 Integrators", "3+ Integrators"],
      //   cleanedChartLabels: [...labels],
      //   cleanedChartLabels: [...labels, "Other"],
    };
  }, [filteredSales]);

  if (!isDataLoaded) {
    return "";
  }

  const chartData = {
    labels: cleanedChartLabels,
    // TODO: need to standardize the colors used
    datasets: [
      {
        data: cleanedChartData,
        backgroundColor: [
          "rgba(251, 128, 114, 0.6)",
          "rgba(255, 255, 179, 0.6)",
          "rgba(141, 211, 150, 0.6)",
          //   "One Corporation": [251, 128, 114, 150],
          //   "Two Corporations": [255, 255, 179, 150],
          //   "3+ Corporations": [141, 211, 199, 150],
        ],
      },
    ],
  };

  return filteredCaptureAreas.length ? (
    <Pie
      data={chartData}
      options={{
        responsive: true,
        maintainAspectRatio: false, // prevent resizing issue
        plugins: {
          legend: {
            display: true,
            position: "bottom",
          },
          tooltip: {
            callbacks: {
              label: function (context) {
                console.log(context);
                const value = context.dataset.data[context.dataIndex];
                console.log("Tooltip value:", value); // this will log the value
                return context.label + ": " + value.toFixed(1) + "%";
              },
            },
          },
        },
      }}
    />
  ) : (
    ""
  );
}
