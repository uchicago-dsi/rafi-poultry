"use client";
// app.js
import React, { useState, useEffect } from "react";

import { state } from "../lib/state";

import DeckGL from "@deck.gl/react";
import { LineLayer, IconLayer, GeoJsonLayer } from "@deck.gl/layers";
import { COORDINATE_SYSTEM } from "@deck.gl/core";
import { Map } from "react-map-gl";

import colorbrewer from "colorbrewer";
import tinycolor from "tinycolor2";
import { ScatterplotLayer } from "deck.gl";
import { useMapData } from "@/lib/useMapData";

// TODO: Is it ok load this client side? Seems like maybe it is for Mapbox?
const MAPBOX_ACCESS_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN;

// TODO: maybe functionalize this later but just hard-coding this short term
// const plantAccessColors = colorbrewer.Set3[4].reverse();
// const plantAccess = [
//   "One Corporation",
//   "Two Corporations",
//   "Three Corporations",
//   "4+ Corporations",
// ];

// const hexPalette = Object.fromEntries(
//   plantAccess.map((access, i) => [access, plantAccessColors[i]])
// );
// const rgbPalette = Object.entries(hexPalette).map(([key, hex]) => {
//   return [key, Object.values(tinycolor(hex).toRgb())];
// });

// for (let key in rgbPalette) {
//   let rgb = rgbPalette[key][1];
//   rgb[3] = 255;
//   rgbPalette[key][1] = rgb;
//   print(rgb);
// }

// const plantColorPalette = Object.fromEntries(rgbPalette);

const plantColorPalette = {
  "One Integrator": [251, 128, 114, 150],
  "Two Integrators": [255, 255, 179, 150],
  "3+ Integrators": [141, 211, 199, 150],
};

const markerPalette = {
  farm: [220, 220, 220, 255],
  plant: [240, 240, 240, 255],
  default: [140, 140, 140, 255],
};

const colorPalette = Object.assign({}, plantColorPalette, markerPalette);

// 4+ Corporations
// :
// (4) [141, 211, 199, 255] // green
// One Corporation
// :
// (4) [251, 128, 114, 255] //red
// Three Corporations
// :
// (4) [255, 255, 179, 255]
// Two Corporations:
// (4) [190, 186, 218, 255] // yellow

// console.log(colorPalette);

export function DeckGLMap() {
  const {
    isDataLoaded,
    stateMapSettings,
    timestampState,
    filteredFarmsData,
    filteredPlantsData,
    filteredCaptureAreas,
    poultryPlants
  } = useMapData();

  // Don't render the component until the data is loaded
  if (!isDataLoaded) {
    return "";
  }

  const plantAccessLayer = new GeoJsonLayer({
    data:filteredCaptureAreas,

    pickable: true,
    onHover: ({ x, y, object }) => {
      state.stateMapSettings.x = x;
      state.stateMapSettings.y = y;
      state.stateMapSettings.hoveredObject = object;
    },

    getFillColor: function (dataRow) {
      // TODO: available if we want to switch back to plants
      // switch (dataRow.properties.plant_access) {
      //   switch (dataRow.properties.corporate_access) {
      //     case 1:
      //       return colorPalette["One Plant"];
      //     case 2:
      //       return colorPalette["Two Plants"];
      //     case 3:
      //       return colorPalette["Three Plants"];
      //     case 4:
      //       return colorPalette["4+ Plants"];
      //   }
      // },
      switch (dataRow.properties.corporate_access) {
        case 1:
          return colorPalette["One Integrator"];
        case 2:
          return colorPalette["Two Integrators"];
        case 3:
          return colorPalette["3+ Integrators"];
        case 4:
          return colorPalette["4+ Integrators"];
      }
    },
  });

  const farmLayer = new IconLayer({
    id: "icon-layer",
    data: filteredFarmsData,
    pickable: true,
    iconAtlas:
      "https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/icon-atlas.png",
    iconMapping: {
      marker: { x: 0, y: 0, width: 128, height: 128, mask: true },
    },

    // TODO: Make farms less chaotic
    getIcon: (d) => "marker",
    getPosition: (d) => d.geometry.coordinates,
    getSize: (d) => 10,
    getColor: (d) => colorPalette.farm,
  });

  const plantLayer = new IconLayer({
    id: "icon-layer",
    stroked: true,
    data: filteredPlantsData,
    iconAtlas:
      "https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/icon-atlas.png",
    iconMapping: {
      marker: { x: 0, y: 0, width: 128, height: 128, mask: true },
    },
    getIcon: (d) => "marker",
    getPosition: (d) => d.geometry.coordinates,
    getSize: 35,
    getColor: colorPalette.plant,
    getLineColor: (d) => [0, 0, 0, 255], // TODO: I want these to be outlined but maybe there's a transparent border?
    getTooltip: (d) => `Address: ${d.properties["Full Address"]}`,

    pickable: true,
    onHover: ({ x, y, object }) => {
      state.stateMapSettings.x = x;
      state.stateMapSettings.y = y;
      state.stateMapSettings.hoveredObject = object;
    },
  });

  const plantInteractiveLayer = new ScatterplotLayer({
    id: "scatterplot-layer",
    data: poultryPlants,
    pickable: true,
    // stroked: true,
    filled: true, // will be filled with empty
    radiusScale: 6,
    radiusMinPixels: 15, // should be about the same size as the marker
    radiusMaxPixels: 100,
    lineWidthMinPixels: 1,
    getPosition: (d) => d.geometry.coordinates,
    getRadius: (d) => 100,
    getFillColor: [0, 0, 0, 0],
    onHover: ({ x, y, object }) => {
      state.stateMapSettings.x = x;
      state.stateMapSettings.y = y;
      state.stateMapSettings.hoveredObject = object;
    },
  });

  var displayLayers = [plantAccessLayer, plantInteractiveLayer, plantLayer];

  if (stateMapSettings.displayFarms) {
    displayLayers.push(farmLayer);
  }

  const deck = (
    <DeckGL
      initialViewState={stateMapSettings.mapZoom} // TODO: is there a way to have an initial state and still dynamically update the view?
      controller={true}
      layers={displayLayers}
      pickingRadius={50} //TODO: This behaves strangely and only works when zoomed out?
    >
      <Map
        mapStyle="mapbox://styles/mapbox/satellite-v9"
        mapboxAccessToken={MAPBOX_ACCESS_TOKEN}
      />
      <div id="legend">
        {Object.entries(plantColorPalette).map(([key, color]) => (
          <div key={key} className="flex items-center">
            <div
              className="swatch"
              style={{
                background: `rgb(${color.slice(0, 3).join(",")},${
                  color[3] / 255
                })`,
              }}
            ></div>
            <div className="label">{key}</div>
          </div>
        ))}
      </div>
    </DeckGL>
  );

  return deck;
}
