"use client";
import { state, updateFilteredData, staticDataStore } from "../lib/state";
import { unpack } from "msgpackr";

// TODO: This file needs to be regenerated with better column names
const ISOCHRONES =
  "../data/new_all_states_with_parent_corp_by_corp.geojson";

const fetchMsgpack = async (dataPath) => {
  const response = await fetch(dataPath);
  const arrayBuffer = await response.arrayBuffer(); 
  const data = unpack(arrayBuffer);
  return data;
};

const fetchData = async (url) => {
  const response = await fetch(url);
  return await response.json();
};

export const updateStaticDataStore = async () => {
  try {
    const [rawPlants, rawBarns, rawIsochrones, rawSales] = await Promise.all([
      fetchData("/api/plants/plants"),
      // TODO: Just use the public version of the barns geojson in the public folder
      fetchMsgpack("/data/all_barns.msgpack"),
      fetchData(ISOCHRONES),
      fetchData("/api/plants/sales")
    ]);

    // Filter FSIS plant data to only include large chicken processing plants
    const processedPlants = {
      type: "FeatureCollection",
      features: rawPlants.features.filter(plant => 
        plant.properties["Animals Processed"] === "Chicken" &&
        plant.properties.Size === "Large")
    };
    staticDataStore.allPlants = processedPlants;

    // Get list of all states that have plants and update staticDataStore
    staticDataStore.allStates = processedPlants.features
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