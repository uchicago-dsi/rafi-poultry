"use client";
import { proxy, useSnapshot } from "valtio";
import bbox from "@turf/bbox";
import { WebMercatorViewport } from "@deck.gl/core";

import { staticDataStore } from "./data";

// Create a proxy state
export const state = proxy({
  // basic data
  stateData: {
    plantAccess: [],
    poultryPlants: [],
    allStates: [],

    // filtered data
    filteredStates: [],
    filteredPlants: [],
    filteredCaptureAreas: [],
    filteredCompanies: [],
    filteredSales: [],
    capturedAreas: {},
    isDataLoaded: false,
  },

  //TODO: Unsure about the best practices for how to load and manage these nested states
  stateMapSettings: {
    // cursor state
    x: undefined,
    y: undefined,
    hoveredObject: undefined,

    // display options
    displayFarms: false,

    // map view
    containerWidth: 0,
    containerHeight: 0,
    mapZoom: undefined,
  },
});

function updateFilteredStates() {
  // TODO: Wait...what is this doing? Update this to use the staticDataStore also
  // choose the filtered areas to display
  state.stateData.filteredCaptureAreas =
    state.stateData.plantAccess.features.filter((row) => {
      if (state.stateData.filteredStates.includes(row.properties.state)) {
        return true;
      } else {
        return false;
      }
    });
}

function updateFilteredPlants() {
  state.stateData.filteredPlants =
  staticDataStore.allPlants.features.filter((row) => {
  // state.stateData.poultryPlants.features.filter((row) => {
    if (state.stateData.filteredStates.includes(row.properties.State)) {
      return true;
    } else {
      return false;
    }
  });
}

function updateFilteredCompanies() {
  state.stateData.filteredCompanies = state.stateData.filteredPlants
    .map((plant) => plant.properties["Parent Corporation"])
    .filter((value, index, array) => array.indexOf(value) === index);
}

function updateFilteredSales() {
  // build dictionary for each company in the area
  let companySales = {};
  for (let i = 0; i < state.stateData.filteredCompanies.length; i++) {
    companySales[state.stateData.filteredCompanies[i]] = 0;
  }

  for (let i = 0; i < state.stateData.filteredPlants.length; i++) {
    let salesVolume =
      state.stateData.filteredPlants[i].properties["Sales Volume (Location)"];
    if (!Number.isNaN(salesVolume)) {
      companySales[
        state.stateData.filteredPlants[i].properties["Parent Corporation"]
      ] += salesVolume;
    }
  }

  // filter NaN values and return dictionary
  let filtered = Object.entries(companySales).reduce(
    (filtered, [key, value]) => {
      if (!Number.isNaN(value)) {
        filtered[key] = value;
      }
      return filtered;
    },
    {}
  );

  // sort on value and convert to object
  let sorted = Object.entries(filtered).sort((a, b) => b[1] - a[1]);
  let unnestedSales = Object.fromEntries(sorted);

  const totalSales = Object.values(unnestedSales).reduce(
    (accumulator, value) => {
      return accumulator + value;
    },
    0
  );

  // create nested object for each corporation
  let nestedSales = {};
  for (let key in unnestedSales) {
    nestedSales[key] = {
      sales: unnestedSales[key],
      percent: unnestedSales[key] / totalSales,
    };
  }
  state.stateData.filteredSales = nestedSales;
}

function calculateCapturedArea() {
  let areas = {
    1: 0,
    2: 0,
    3: 0,
    // 4: 0,
  };

  // TODO: Need to add area to GeoJSON
  for (let i = 0; i < state.stateData.filteredCaptureAreas.length; i++) {
    areas[
      state.stateData.filteredCaptureAreas[i].properties.corporate_access
    ] += state.stateData.filteredCaptureAreas[i].properties.area;
  }

  let totalArea = Object.values(areas).reduce((acc, val) => acc + val, 0);

  let percentArea = {};
  Object.keys(areas).forEach((key) => {
    percentArea[key] = areas[key] / totalArea;
  });

  // return percentArea;
  state.stateData.capturedAreas = percentArea;
}

function calculateCapturedAreaByBarns() {
  // initialize object for reduce operation
  const counts = {
    totalFarms: 0,
    totalCapturedFarms: 0,
    plantAccessCounts: {
      0: 0, // '0' represents NaN or no access
      1: 0,
      2: 0,
      3: 0,
    },
  };

  staticDataStore.allFarms.features.reduce((accumulator, feature) => {
  // state.stateData.farms.features.reduce((accumulator, feature) => {
    const plantAccess = feature.properties.plant_access || "0"; // Default to '0' if null
    accumulator.totalFarms += 1
    // Only count farms in captive draw areas
    if (plantAccess != "0") {
      accumulator.totalCapturedFarms += 1;
    }
    accumulator.plantAccessCounts[plantAccess] += 1;

    return accumulator;
  }, counts);

  let percentCaptured = {};
  Object.keys(counts.plantAccessCounts).forEach((key) => {
    if (key != "0") {
      percentCaptured[key] = counts.plantAccessCounts[key] / counts.totalCapturedFarms;
    }
  });

  state.stateData.totalFarms = counts.totalFarms;
  state.stateData.capturedAreas = percentCaptured;
}

function updateMapZoom() {
  // default zoom state is everything (handles the case of no selection)
  var zoomGeoJSON = state.stateData.plantAccess.features;

  // update to the selected areas if they exist
  if (state.stateData.filteredStates.length) {
    zoomGeoJSON = state.stateData.filteredCaptureAreas;
  }

  const currentGeojson = {
    type: "FeatureCollection",
    features: zoomGeoJSON,
  };
  const boundingBox = bbox(currentGeojson);
  const fittedViewport = new WebMercatorViewport(
    state.stateMapSettings.containerWidth,
    state.stateMapSettings.containerHeight
  );

  const currentLatLonZoom = fittedViewport.fitBounds(
    [
      [boundingBox[0], boundingBox[1]],
      [boundingBox[2], boundingBox[3]],
    ],
    {
      width: state.stateMapSettings.containerWidth,
      height: state.stateMapSettings.containerHeight,
      padding: { top: 20, bottom: 20, left: 20, right: 20 },
    }
  );

  state.stateMapSettings.mapZoom = {
    longitude: currentLatLonZoom.longitude,
    latitude: currentLatLonZoom.latitude,
    zoom: currentLatLonZoom.zoom,

    pitch: 0,
    bearing: 0,
  };
}

export function updateFilteredData() {
  updateFilteredStates();
  updateFilteredPlants();
  updateFilteredCompanies();
  updateFilteredSales();
  calculateCapturedArea();
  calculateCapturedAreaByBarns();
  updateMapZoom();
}
