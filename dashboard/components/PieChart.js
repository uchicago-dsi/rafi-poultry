"use client";
import React, { useMemo } from "react";
import { useMapData } from "@/lib/useMapData";

import { Pie } from "react-chartjs-2";
import { Chart, ArcElement, Legend, Tooltip } from "chart.js";
Chart.register(ArcElement, Legend, Tooltip);

export default function PieChart() {
  const { isDataLoaded, percentCapturedBarns, totalCapturedBarns } =
    useMapData();

  const { cleanedChartData, cleanedChartLabels } = useMemo(() => {
    if (!isDataLoaded) {
      return {
        cleanedChartData: [],
        cleanedChartLabels: [],
      };
    }
    const values = Object.entries(percentCapturedBarns).map(
      ([key, value]) => value * 100
    );
    return {
      cleanedChartData: values,
      cleanedChartLabels: ["1 Integrator", "2 Integrators", "3+ Integrators"],
    };
  }, [percentCapturedBarns]);

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

  return totalCapturedBarns ? (
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
                console.log("Tooltip value:", value);
                return context.label + ": " + value.toFixed(1) + "%";
              },
            },
          },
        },
      }}
    />
  ) : (
    "No barns data in selected states"
  );
}
