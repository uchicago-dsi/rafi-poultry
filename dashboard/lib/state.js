"use client";
import { proxy } from "valtio";
import bbox from "@turf/bbox";
import { WebMercatorViewport } from "@deck.gl/core";
import { derive } from "valtio/utils";
import { state2abb } from "./constants";

export const staticDataStore = {
  allPlants: [],
  allBarns: [],
  allSales: [],
  allIsochrones: [],
  allStates: [],
};

export const filteredDataStore = {
  filteredPlants: [],
  filteredBarns: [],
  filteredSales: [],
  filteredIsochrones: [],

  // TODO: These names are confusing
  percentCapturedBarns: [], // Refers to the percentage of area with access to integrators
  totalCapturedBarns: [],
  totalSales: 0,
  HHI: 0
};

export const state = proxy({
  data: {
    isDataLoaded: false,
    selectedStates: [],
  },

  map: {
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
  // TODO: Do we need to actually do this? Should we change the barns data so it comes in with the state already?
  // const stateabbrevs = states.map((state) => state2abb[state]);
  filteredDataStore.filteredBarns =
  staticDataStore.allBarns.features.filter((row) =>
    states.includes(row.properties.state)
  );
}

function updateFilteredSales(states) {
    let corporationTotals = {};

    states.forEach(state => {
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

    const totalSales = Object.values(corporationTotals).reduce((sum, corp) => sum + corp.sales, 0);

    const sortedArray = Object.entries(corporationTotals).sort((a, b) => b[1].sales - a[1].sales);
    sortedArray.forEach(([corporation, data]) => {
      data.percent = (data.sales / totalSales); 
    });
    const sortedCorporationTotals = Object.fromEntries(sortedArray);

    filteredDataStore.filteredSales = sortedCorporationTotals;
    filteredDataStore.totalSales = totalSales;
  }

function calculateCapturedBarns() {
  const counts = {
    totalFarms: 0,
    totalCapturedBarns: 0,
    plantAccessCounts: {
      0: 0, // '0' represents NaN or no access
      1: 0,
      2: 0,
      3: 0,
    },
  };

  // TODO: filteredBarns and allBarns should be the same format...decide if they should be a list or a geojson
  filteredDataStore.filteredBarns.reduce((accumulator, feature) => {
    const plantAccess = feature.properties.integrator_access === 4 ? 3 : (feature.properties.integrator_access || 0); // convert 4 to 3, default to 0 if null
    accumulator.totalFarms += 1;
    // Only count farms in captive draw areas
    if (plantAccess != 0) {
      accumulator.totalCapturedBarns += 1;
    }
    accumulator.plantAccessCounts[plantAccess] += 1;
    return accumulator;
  }, counts);

  let percentCapturedBarns = {};
  Object.keys(counts.plantAccessCounts).forEach((key) => {
    if (key != "0") {
      percentCapturedBarns[key] =
        counts.plantAccessCounts[key] / counts.totalCapturedBarns;
    }
  });

  filteredDataStore.totalCapturedBarns = counts.totalCapturedBarns;
  filteredDataStore.percentCapturedBarns = percentCapturedBarns;
}

function calculateHHI() {
  // TODO: should probably make total sales part of the state
  // calculate total sales in selected area
  if (Object.keys(filteredDataStore.filteredSales).length) {
    // let totalSales = Object.values(filteredDataStore.filteredSales).reduce(
    //   (acc, item) => acc + item.sales,
    //   0
    // );

    // calculate HHI
    return Object.values(filteredDataStore.filteredSales).reduce(
      (acc, item) => acc + Math.pow((item.sales * 100) / filteredDataStore.totalSales, 2),
      0
    );
  } else {
    return 0;
  }
}

function updateMapZoom(filteredStates) {
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

  const boundingBox = bbox(currentGeojson);
  const fittedViewport = new WebMercatorViewport(
    state.map.containerWidth,
    state.map.containerHeight
  );

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

// export const updateFilteredData = async (stateData) => {
  export function updateFilteredData(stateData) {
  if (!stateData?.isDataLoaded) {
    return;
  }
  updateFilteredPlants(stateData.selectedStates);
  updateFilteredIsochrones(stateData.selectedStates);
  updateFilteredSales(stateData.selectedStates);
  updateFilteredBarns(stateData.selectedStates);
  updateMapZoom(stateData.selectedStates);

  // TODO: What's the right way to do this? Should these return things or update in place?
  calculateCapturedBarns();
  filteredDataStore.HHI = calculateHHI();

  return performance.now();
}

// use this to trigger refresh
export const filterTimestampStore = derive({
  timestamp: (get) => updateFilteredData(get(state).data),
});
