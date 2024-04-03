"use client";
import { state, updateFilteredData, staticDataStore } from "../lib/state";

const PLANT_ACCESS_GEOJSON =
  "../data/new_all_states_with_parent_corp_by_corp.geojson";

const getJSON = async (dataPath) => {
  const response = await fetch(dataPath);
  return await response.json();
};

const fetchData = async (url) => {
  const response = await fetch(url);
  return await response.json();
};

export const updateStaticDataStore = async () => {
  try {
    const [rawPlants, rawFarms, plantAccess, salesJSON] = await Promise.all([
      fetchData("/api/plants/plants"),
      fetchData("/api/farms"),
      getJSON(PLANT_ACCESS_GEOJSON),
      fetchData("/api/plants/sales")
    ]);

    staticDataStore.allStates = plantAccess.features
    .map((feature) => feature.properties.state)
    .filter((value, index, array) => array.indexOf(value) === index)
    .sort();

    // TODO: Maybe move filtering logic to the filteredDataStore
    // Filter FSIS plant data
    const processedPlants = rawPlants.features.filter((plant) => {
      if (
        plant.properties["Animals Processed"] === "Chicken" &&
        plant.properties.Size === "Large"
      ) {
        return true;
      } else {
        return false;
      }
    });

    let processedPlantsJSON = {
      type: "FeatureCollection",
      features: processedPlants,
    };

    // TODO: Wait which is which...
    staticDataStore.allPlants = processedPlantsJSON;

    // TODO: Maybe move filtering logic to the filteredDataStore
    // Filter farms data
    let farmsJSON = {
      type: "FeatureCollection",
      features: rawFarms.features.filter(
        (feature) =>
          feature.properties.exclude === 0 &&
          feature.properties.plant_access !== null
      ),
    };

    staticDataStore.allBarns = farmsJSON;
    staticDataStore.allSales = salesJSON;

    // TODO: I don't think I actually want this in state...
    state.stateData.plantAccess = plantAccess
    // TODO: But maybe the list of possible states should be in state?
    state.stateData.allStates = state.stateData.plantAccess.features
      .map((feature) => feature.properties.state)
      .filter((value, index, array) => array.indexOf(value) === index)
      .sort();
  } catch (error) {
    console.error(error);
  }

  // Initialize display data
  state.stateData.filteredStates = [...state.stateData.allStates]; // Start with all states selected
  updateFilteredData();
  state.stateData.isDataLoaded = true;
};