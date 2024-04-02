"use client";
import Papa from "papaparse";
import { state, updateFilteredData, staticDataStore } from "../lib/state";

// const POULTRY_PLANTS_CSV = "../data/poultry_plants_with_sales.csv";
const POULTRY_PLANTS_CSV = "../data/location_match_fullest.csv";
// const PLANT_ACCESS_GEOJSON = "../data/all_states.geojson";
const PLANT_ACCESS_GEOJSON =
  "../data/new_all_states_with_parent_corp_by_corp.geojson";
// const COUNTERGLOW_FARMS = "../data/counterglow_geojson.geojson";
// const FARMS = "../data/nc_farms_plants.geojson";
// const FARMS = "../data/test_barns_filtering.geojson";

const getJSON = async (dataPath) => {
  const response = await fetch(dataPath);
  return await response.json();
};

const getPoultryCSV = async (dataPath) => {
  const response = await fetch(dataPath);
  const reader = response.body.getReader();
  const result = await reader.read(); // raw array
  const decoder = new TextDecoder("utf-8");
  const csv = decoder.decode(result.value);

  return new Promise((resolve, reject) => {
    Papa.parse(csv, {
      header: true,
      complete: (results) => {
        const data = results.data.map((row) => ({
          ...row,
          "Sales Volume (Location)": parseFloat(row["Sales Volume (Location)"]),
        }));

        resolve(data);
      },
      error: (error) => {
        reject(error);
      },
    });
  });
};

const parsePlantCSV = async (response) => {
  // const response = await fetch(dataPath);
  const reader = response.body.getReader();
  const result = await reader.read(); // raw array
  const decoder = new TextDecoder("utf-8");
  const csv = decoder.decode(result.value);

  return new Promise((resolve, reject) => {
    Papa.parse(csv, {
      header: true,
      complete: (results) => {
        const data = results.data.map((row) => ({
          ...row,
          "Sales Volume (Location)": parseFloat(row["Sales Volume (Location)"]),
        }));

        resolve(data);
      },
      error: (error) => {
        reject(error);
      },
    });
  });
};

// Function to load data
export const loadData = async () => {
  // Read raw files
  // // staticDataStore.plantAccess = await getJSON(PLANT_ACCESS_GEOJSON);
  // staticDataStore.allStates = staticDataStore.plantAccess.features
  //   .map((feature) => feature.properties.state)
  //   .filter((value, index, array) => array.indexOf(value) === index)
  //   .sort();

  // let farmsResponse = await fetch("/api/farms/");
  // let rawFarms = await farmsResponse.json();
  // staticDataStore.farms = {
  //   type: "FeatureCollection",
  //   features: rawFarms.features.filter(
  //     (feature) =>
  //       feature.properties.exclude === 0 &&
  //       feature.properties.plant_access !== null
  //   ),
  // };

  // Filter FSIS plant data
  // TODO: Rewrite pipeline to save the plants as GeoJSON
  // TODO: Change geojson so it has better feature names?

  // TODO: Question — how much of this processing should be done in the API call?
  let plantsResponse = await fetch("/api/plants/");
  let rawPlants = await plantsResponse.json();
  const rawPoultryPlants = rawPlants.features.filter((plant) => {
    if (
      plant.properties["Animals Processed"] === "Chicken" &&
      plant.properties.Size === "Large"
    ) {
      return true;
    } else {
      return false;
    }
  });
  staticDataStore.poultryPlants = {
    type: "FeatureCollection",
    features: rawPoultryPlants,
  };

  // Initialize display data
  state.stateData.filteredStates = [...state.stateData.allStates]; // Start with all states selected
  updateFilteredData();
  state.stateData.isDataLoaded = true;
};

const fetchData = async (url) => {
  const response = await fetch(url);
  return await response.json();
};

export const updateStaticDataStore = async () => {
  try {
    const [rawPlants, rawFarms, plantAccess,] = await Promise.all([
      fetchData("/api/plants"),
      fetchData("/api/farms"),
      getJSON(PLANT_ACCESS_GEOJSON),
      // TODO: set up sales to come from API
    ]);

    staticDataStore.allStates = plantAccess.features
    .map((feature) => feature.properties.state)
    .filter((value, index, array) => array.indexOf(value) === index)
    .sort();

    // TODO: Move filtering logic to the filteredDataStore
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

    staticDataStore.poultryPlants = processedPlantsJSON;
    staticDataStore.allPlants = processedPlantsJSON;

    // TODO: Move filtering logic to the filteredDataStore
    // Filter farms data
    let farmsJSON = {
      type: "FeatureCollection",
      features: rawFarms.features.filter(
        (feature) =>
          feature.properties.exclude === 0 &&
          feature.properties.plant_access !== null
      ),
    };

    staticDataStore.allFarms = farmsJSON;

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