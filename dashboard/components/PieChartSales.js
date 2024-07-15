"use client";
import React, { useMemo } from "react";
import { useMapData } from "@/lib/useMapData";

import { Pie } from "react-chartjs-2";
import { Chart, ArcElement, Legend, Tooltip } from "chart.js";
Chart.register(ArcElement, Legend, Tooltip);

export default function PieChart() {
  const { isDataLoaded, filteredSales } = useMapData();

  const { cleanedChartData, cleanedChartLabels } = useMemo(() => {
    if (!isDataLoaded) {
      return {
        cleanedChartData: [],
        cleanedChartLabels: [],
      };
    }

    const data = Object.entries(filteredSales);
    const { labels, values } = data.slice(0, 4).reduce(
      (acc, [key, value]) => {
        acc.labels.push(key);
        acc.values.push(value.percent * 100);
        return acc;
      },
      { labels: [], values: [] }
    );

    const remaining =
      data
        .slice(4)
        .map(([key, value]) => value.percent)
        .reduce((a, b) => a + b, 0) * 100;

    console.log("labels", labels);
    console.log("values", values);
    console.log("remaining", remaining);

    return {
      cleanedChartData: [...values, remaining],
      cleanedChartLabels: [...labels, "Other"],
    };
  }, [isDataLoaded, filteredSales]);

  if (!isDataLoaded) {
    return "";
  }

  const chartData = {
    labels: cleanedChartLabels,
    datasets: [
      {
        data: cleanedChartData,
        backgroundColor: [
          "rgba(255, 99, 132, 0.6)", // red
          "rgba(54, 162, 235, 0.6)", // blue
          "rgba(255, 206, 86, 0.6)", // yellow
          "rgba(75, 192, 192, 0.6)", // teal
          "rgba(153, 102, 255, 0.6)", // purple
        ],
      },
    ],
  };

  // console.log("filteredSales", filteredSales);
  // console.log("chartData", chartData);

  return Object.keys(filteredSales).length ? (
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
