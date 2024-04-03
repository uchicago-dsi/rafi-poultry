"use client";
import React, { useState, useEffect, useMemo } from "react";
import { useSnapshot } from "valtio";

import { state } from "../lib/state";

import { Pie } from "react-chartjs-2";
import { Chart, ArcElement, Legend, Tooltip } from "chart.js";
Chart.register(ArcElement, Legend, Tooltip);

// TODO: This can maybe go away?

export default function PieChart() {
  const snapshot = useSnapshot(state.data);

  const { cleanedChartData, cleanedChartLabels } = useMemo(() => {
    if (!snapshot.isDataLoaded) {
      return {
        cleanedChartData: [],
        cleanedChartLabels: [],
      };
    }

    const data = Object.entries(snapshot.filteredSales);
    const top4 = data.slice(0, 3);
    const labels = top4.map(([key, value]) => key);
    const values = top4.map(([key, value]) => value.percent * 100);

    const remaining = data
      .slice(3)
      .map(([key, value]) => value.percent)
      .reduce((a, b) => a + b, 0);

    return {
      cleanedChartData: [...values, remaining],
      cleanedChartLabels: [...labels, "Other"],
    };
  }, [snapshot.filteredSales]);

  if (!snapshot.isDataLoaded) {
    return "";
  }

  const chartData = {
    labels: cleanedChartLabels,
    // TODO: need to standardize the colors used
    datasets: [
      {
        data: cleanedChartData,
        backgroundColor: [
          "rgba(255, 99, 132, 0.6)",
          "rgba(54, 162, 235, 0.6)",
          "rgba(255, 206, 86, 0.6)",
          "rgba(75, 192, 192, 0.6)",
          // Add more colors as needed
        ],
      },
    ],
  };

  return snapshot.filteredCaptureAreas.length ? (
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
