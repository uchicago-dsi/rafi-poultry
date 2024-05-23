"use client";
import pako from 'pako';
import { state, staticDataStore, updateFilteredData } from "../lib/state";

const ISOCHRONES = "../data/v2/isochrones.geojson";

const fetchData = async (url) => {
  const response = await fetch(url);
  return await response.json();
};

const fetchGzip = async (url) => {
  const response = await fetch(url);
  const arrayBuffer = await response.arrayBuffer();
  const decompressed = pako.inflate(new Uint8Array(arrayBuffer), { to: 'string' });
  return JSON.parse(decompressed);
}

export const updateStaticDataStore = async () => {
  try {
    const [rawPlants, rawBarns, rawIsochrones, rawSales] = await Promise.all([
      fetchData("/api/plants/plants"),
      fetchGzip("/data/filtered_barns.geojson.gz"),
      fetchData(ISOCHRONES),
      fetchData("/api/plants/sales")
    ]);

    // FSIS plant data to only include large chicken processing plants
    // const processedPlants = {
    //   type: "FeatureCollection",
    //   features: rawPlants.features.filter(plant => 
    //     plant.properties["Animals Processed"] === "Chicken" &&
    //     plant.properties.Size === "Large")
    // };
    // staticDataStore.allPlants = processedPlants;
    console.log("rawPlants", rawPlants)
    staticDataStore.allPlants = rawPlants;
    // console.log("rawPlants", rawPlants)

    // Get list of all states that have plants and update staticDataStore
    // staticDataStore.allStates = processedPlants.features
    // .map((feature) => feature.properties.State)
    // .filter((value, index, array) => array.indexOf(value) === index)
    // .sort();
    staticDataStore.allStates = rawPlants.features
    .map((feature) => feature.properties.State)
    .filter((value, index, array) => array.indexOf(value) === index)
    .sort();

    // Filter barns data to only include farms that are not excluded and have plant access
    const processedBarns = {
      type: "FeatureCollection",
      features: rawBarns.features.filter(
        (feature) =>
          feature.properties.exclude === 0 &&
          feature.properties.plant_access !== null
      ),
    };
    staticDataStore.allBarns = processedBarns;

    // Sales and isochrones can be used directly from the API call
    staticDataStore.allSales = rawSales;
    staticDataStore.allIsochrones = rawIsochrones

  } catch (error) {
    console.error(error);
  }

  // Initialize display data
  state.data.selectedStates = [...staticDataStore.allStates]; // Start with all states selected
  updateFilteredData(); // TODO: should we trigger this another way
  state.data.isDataLoaded = true;
};