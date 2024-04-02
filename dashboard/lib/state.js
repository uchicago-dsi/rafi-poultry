"use client";
import { proxy } from "valtio";
import bbox from "@turf/bbox";
import { WebMercatorViewport } from "@deck.gl/core";
import { derive } from "valtio/utils";
import { state2abb } from "./constants";

export const staticDataStore = {
  allPlants: [],
  allFarms: [],
  allSales: [],
  allIsochrones: [],
  poultryPlants: [],
};

export const staticFilteredState = {
  filteredFarmsData: [],
  filteredPlantsData: [],
  filteredCompanies: [],
  filteredSales: [],
  filteredCaptureAreas: [],
  // TODO: These names are confusing. What is capturedAreas?
  capturedAreas: [],
  totalFarms: [],
  plantAccess: [],
};
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

function updateFilteredStates(states) {
  // TODO: I don't like this function and I think it's doing too much
  // TODO: standardize the column names so they are all lower case (something else is State)
    staticFilteredState.filteredCaptureAreas =
      state.stateData.plantAccess.features.filter((row) =>
        states.includes(row.properties.state)
      );

  const stateabbrevs = states.map((state) => state2abb[state]);

  const _features = staticDataStore.allFarms.features;
  const features = [];
  for (let i = 0; i < _features.length; i++) {
    const isInState = stateabbrevs.includes(_features[i].properties.state);
    const isExcluded = _features[i].properties.exclude === 0;
    const hasPlantAccess = _features[i].properties.plant_access !== null;
    if (isInState && isExcluded && hasPlantAccess) {
      features.push(_features[i]);
    }
  }
  staticFilteredState.filteredFarmsData = features;

  staticFilteredState.filteredPlantsData = staticDataStore.allPlants.features
    ? staticDataStore.allPlants.features.filter((row) =>
        states.includes(row.properties.State)
      )
    : [];
}

// TODO: Should this be kept in state? And separate from the filteredDataStore?
function updateFilteredCompanies() {
  staticFilteredState.filteredCompanies = staticFilteredState.filteredPlantsData
    .map((plant) => plant.properties["Parent Corporation"])
    .filter((value, index, array) => array.indexOf(value) === index);
}

function updateFilteredSales() {
  // build dictionary for each company in the area
  let companySales = {};
  for (let i = 0; i < staticFilteredState.filteredCompanies.length; i++) {
    companySales[staticFilteredState.filteredCompanies[i]] = 0;
  }

  for (let i = 0; i < staticFilteredState.filteredPlantsData.length; i++) {
    let salesVolume =
      staticFilteredState.filteredPlantsData[i].properties[
        "Sales Volume (Location)"
      ];
    if (!Number.isNaN(salesVolume)) {
      companySales[
        staticFilteredState.filteredPlantsData[i].properties[
          "Parent Corporation"
        ]
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
  staticFilteredState.filteredSales = nestedSales;
}

function calculateCapturedArea() {
  let areas = {
    1: 0,
    2: 0,
    3: 0,
    // 4: 0,
  };

  // TODO: Need to add area to GeoJSON
  for (let i = 0; i < staticFilteredState.filteredCaptureAreas.length; i++) {
    areas[
      staticFilteredState.filteredCaptureAreas[i].properties.corporate_access
    ] += staticFilteredState.filteredCaptureAreas[i].properties.area;
  }

  let totalArea = Object.values(areas).reduce((acc, val) => acc + val, 0);

  let percentArea = {};
  Object.keys(areas).forEach((key) => {
    percentArea[key] = areas[key] / totalArea;
  });

  // return percentArea;
  staticFilteredState.capturedAreas = percentArea;
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

  // filteredDataStore.filteredFarmsData.features.reduce((accumulator, feature) => {
  staticDataStore.allFarms.features.reduce((accumulator, feature) => {
    const plantAccess = feature.properties.plant_access || "0"; // Default to '0' if null
    accumulator.totalFarms += 1;
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
      percentCaptured[key] =
        counts.plantAccessCounts[key] / counts.totalCapturedFarms;
    }
  });

  staticDataStore.totalFarms = counts.totalFarms;
  staticDataStore.capturedAreas = percentCaptured;
}

function updateMapZoom(filteredStates) {
  // default zoom state is everything (handles the case of no selection)
  var zoomGeoJSON = staticFilteredState.filteredCaptureAreas.features;

  // update to the selected areas if they exist
  if (filteredStates.length) {
    zoomGeoJSON = staticFilteredState.filteredCaptureAreas;
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

export function updateFilteredData(stateData) {
  if (!stateData?.isDataLoaded) {
    return;
  }
  updateFilteredStates(stateData.filteredStates);
  updateFilteredCompanies();
  updateFilteredSales();
  calculateCapturedArea();
  calculateCapturedAreaByBarns();
  updateMapZoom(stateData.filteredStates);
  return performance.now();
}

export const filterTimestampStore = derive({
  timestamp: (get) => updateFilteredData(get(state).stateData),
});
