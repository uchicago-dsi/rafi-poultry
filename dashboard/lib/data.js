"use client";
import pako from "pako";
import { state, staticDataStore, updateFilteredData } from "../lib/state";

const ISOCHRONES = "../data/v2/isochrones.geojson.gz";
const BARNS = "../data/v2/barns.geojson.gz";

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
    const [rawPlants, rawBarns, rawIsochrones, rawSales] = await Promise.all([
      fetchData("/api/plants/plants"),
      fetchGzip(BARNS),
      fetchGzip(ISOCHRONES),
      fetchData("/api/plants/sales"),
    ]);

    staticDataStore.allPlants = rawPlants;

    // Update states to display
    staticDataStore.allStates = rawPlants.features
      .map((feature) => feature.properties.State)
      .filter((value, index, array) => array.indexOf(value) === index)
      .sort();

    // Filter barns data to only include farms that are not excluded and have plant access
    console.log("rawBarns", rawBarns);
    const processedBarns = {
      type: "FeatureCollection",
      features: rawBarns.features.filter(
        (feature) =>
          feature.properties.exclude === 0 &&
          feature.properties.integrator_access !== null
      ),
    };
    staticDataStore.allBarns = processedBarns;

    console.log("processedBarns", processedBarns);
    console.log("rawSales", rawSales);

    // Sales and isochrones can be used directly from the API call
    staticDataStore.allSales = rawSales;
    staticDataStore.allIsochrones = rawIsochrones;

    console.log("rawIsochrones", rawIsochrones);
  } catch (error) {
    console.error(error);
  }

  // Initialize display data
  state.data.selectedStates = [...staticDataStore.allStates]; // Start with all states selected
  updateFilteredData(); // TODO: should we trigger this another way
  state.data.isDataLoaded = true;
};
