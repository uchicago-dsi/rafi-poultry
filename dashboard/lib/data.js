"use client";
import pako from "pako";
import { state, staticDataStore, updateFilteredData } from "../lib/state";

const ISOCHRONES = "../data/v2/isochrones.geojson.gz";

const fetchData = async (url) => {
  const response = await fetch(url);
  return await response.json();
};

const fetchGzip = async (url) => {
  const response = await fetch(url);
  const arrayBuffer = await response.arrayBuffer();
  const decompressed = pako.inflate(new Uint8Array(arrayBuffer), {
    to: "string",
  });
  return JSON.parse(decompressed);
};

export const updateStaticDataStore = async () => {
  try {
    const [rawPlants, allBarns, allBarnCounts, rawIsochrones, rawSales] =
      await Promise.all([
        fetchData("/api/plants/plants"),
        fetchData("/api/barns/barns"),
        fetchData("/api/barns/counts"),
        fetchGzip(ISOCHRONES),
        fetchData("/api/plants/sales"),
      ]);

    staticDataStore.allPlants = rawPlants;

    // Update states to display
    staticDataStore.allStates = rawPlants.features
      .map((feature) => feature.properties.State)
      .filter((value, index, array) => array.indexOf(value) === index)
      .sort();

    // Note: barns are processed in API call
    staticDataStore.allBarns = allBarns;
    staticDataStore.allBarnCounts = allBarnCounts;

    // Sales and isochrones can be used directly from the API call
    staticDataStore.allSales = rawSales;
    staticDataStore.allIsochrones = rawIsochrones;
  } catch (error) {
    console.error(error);
  }

  // Initialize display data
  state.data.selectedStates = [...staticDataStore.allStates]; // Start with all states selected
  updateFilteredData(); // TODO: should we trigger this another way
  state.data.isDataLoaded = true;
};
