"use client";
import { proxy } from "valtio";
import bbox from "@turf/bbox";
import { WebMercatorViewport } from "@deck.gl/core";
import { derive } from "valtio/utils";

export const staticDataStore = {
  allPlants: [],
  allBarns: [],
  allBarnCounts: [],
  allSales: [],
  allIsochrones: [],
  allStates: [],
};

export const filteredDataStore = {
  filteredPlants: [],
  filteredBarns: [],
  filteredBarnPercents: {},
  filteredSales: [],
  filteredIsochrones: [],

  totalSales: 0,
  HHI: 0,
};

// Note: Separate tooltip state from the main state to avoid re-renders
export const tooltipState = proxy({
  x: undefined,
  y: undefined,
  hoveredObject: undefined,
});

export const state = proxy({
  data: {
    isDataLoaded: false,
    selectedStates: [],
  },

  map: {
    // display options
    displayFarms: false,

    // map view
    containerWidth: 0,
    containerHeight: 0,
    mapZoom: undefined,
  },
});

function updateFilteredPlants(states) {
  filteredDataStore.filteredPlants = staticDataStore.allPlants.features
    ? staticDataStore.allPlants.features.filter((row) =>
        states.includes(row.properties.State)
      )
    : [];
}

function updateFilteredIsochrones(states) {
  filteredDataStore.filteredIsochrones =
    staticDataStore.allIsochrones.features.filter((row) =>
      states.includes(row.properties.state)
    );
}

function updateFilteredBarns(states) {
  filteredDataStore.filteredBarns = staticDataStore.allBarns.features.filter(
    (row) => states.includes(row.properties.state)
  );
}

function updateFilteredBarnPercents(states) {
  let filteredBarnCounts = {
    Total: 0,
    1: 0,
    2: 0,
    3: 0,
  };
  Object.keys(staticDataStore.allBarnCounts)
    .filter((state) => states.includes(state))
    .forEach((state) => {
      const barns = staticDataStore.allBarnCounts[state];
      filteredBarnCounts["Total"] += barns.totalBarns;
      filteredBarnCounts[1] += barns.plantAccessCounts[1];
      filteredBarnCounts[2] += barns.plantAccessCounts[2];
      filteredBarnCounts[3] += barns.plantAccessCounts[3];
    }, {});

  let filteredBarnPercents = {};
  Object.keys(filteredBarnCounts).forEach((key) => {
    if (key != "Total") {
      filteredBarnPercents[key] =
        filteredBarnCounts[key] / filteredBarnCounts["Total"];
    }
  });
  filteredDataStore.filteredBarnPercents = filteredBarnPercents;
}

function updateFilteredSales(states) {
  let corporationTotals = {};

  states.forEach((state) => {
    const stateData = staticDataStore.allSales[state];
    if (stateData) {
      Object.entries(stateData).forEach(([corporation, data]) => {
        if (!corporationTotals[corporation]) {
          corporationTotals[corporation] = { sales: 0 }; // Initialize if not already present
        }
        corporationTotals[corporation].sales += data.sales;
      });
    }
  });

  const totalSales = Object.values(corporationTotals).reduce(
    (sum, corp) => sum + corp.sales,
    0
  );

  const sortedArray = Object.entries(corporationTotals).sort(
    (a, b) => b[1].sales - a[1].sales
  );
  sortedArray.forEach(([corporation, data]) => {
    data.percent = data.sales / totalSales;
  });
  const sortedCorporationTotals = Object.fromEntries(sortedArray);

  filteredDataStore.filteredSales = sortedCorporationTotals;
  filteredDataStore.totalSales = totalSales;
}

function calculateHHI() {
  if (Object.keys(filteredDataStore.filteredSales).length) {
    return Object.values(filteredDataStore.filteredSales).reduce(
      (acc, item) =>
        acc + Math.pow((item.sales * 100) / filteredDataStore.totalSales, 2),
      0
    );
  } else {
    return 0;
  }
}

function updateMapZoom(filteredStates) {
  if (!state.map.containerHeight || !state.map.containerWidth) {
    return;
  }

  // default zoom state is everything (handles the case of no selection)
  var zoomGeoJSON = staticDataStore.allIsochrones.features;

  // TODO: allIsochrones and filteredIsochrones should be the same format
  // update to the selected areas if they exist
  if (filteredStates.length) {
    zoomGeoJSON = filteredDataStore.filteredIsochrones;
  }
  const currentGeojson = {
    type: "FeatureCollection",
    features: zoomGeoJSON,
  };

  console.log("containerHeight", state.map.containerHeight);
  console.log("containerWidth", state.map.containerWidth);

  const boundingBox = bbox(currentGeojson);
  const fittedViewport = new WebMercatorViewport(
    state.map.containerWidth,
    state.map.containerHeight
  );

  console.log("boundingBox", boundingBox);
  console.log("fittedViewport", fittedViewport);

  const currentLatLonZoom = fittedViewport.fitBounds(
    [
      [boundingBox[0], boundingBox[1]],
      [boundingBox[2], boundingBox[3]],
    ],
    {
      width: state.map.containerWidth,
      height: state.map.containerHeight,
      padding: { top: 20, bottom: 20, left: 20, right: 20 },
    }
  );

  state.map.mapZoom = {
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

  // TODO: What's the right way to do this? Should these return things or update in place?
  updateFilteredPlants(stateData.selectedStates);
  updateFilteredIsochrones(stateData.selectedStates);
  updateFilteredSales(stateData.selectedStates);
  updateFilteredBarns(stateData.selectedStates);
  updateFilteredBarnPercents(stateData.selectedStates);
  updateMapZoom(stateData.selectedStates);

  filteredDataStore.HHI = calculateHHI();

  return performance.now();
}

// use this to trigger refresh
export const filterTimestampStore = derive({
  timestamp: (get) => updateFilteredData(get(state).data),
});
