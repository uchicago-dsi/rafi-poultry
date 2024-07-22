"use client";
import React from "react";

import DeckGL from "@deck.gl/react";
import { ScatterplotLayer } from "deck.gl";
import { IconLayer, GeoJsonLayer } from "@deck.gl/layers";
import { Map, ScaleControl, NavigationControl } from "react-map-gl";
import { tooltipState } from "@/lib/state";
import { useMapData } from "@/lib/useMapData";

// TODO: Is it ok load this client side? Seems like maybe it is for Mapbox?
const MAPBOX_ACCESS_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN;

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

export function DeckGLMap() {
  const {
    isDataLoaded,
    stateMapSettings,
    filteredBarns,
    filteredIsochrones,
    allPlants,
  } = useMapData();

  // Don't render the component until the data is loaded
  if (!isDataLoaded) {
    return "";
  }

  const plantAccessLayer = new GeoJsonLayer({
    data: filteredIsochrones,

    pickable: true,
    onHover: ({ x, y, object }) => {
      tooltipState.x = x;
      tooltipState.y = y;
      tooltipState.hoveredObject = object;
    },

    getFillColor: function (dataRow) {
      switch (dataRow.properties.corp_access) {
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

  const barnsLayer = new IconLayer({
    id: "icon-layer",
    data: filteredBarns,
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
    data: allPlants.features,
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
    // TODO: Wait...can I just delete this or?
    getTooltip: (d) => `Address: ${d.properties["Address"]}`,

    pickable: true,
    // TODO: tooltip should probably be split out for performance eventually
    onHover: ({ x, y, object }) => {
      tooltipState.x = x;
      tooltipState.y = y;
      tooltipState.hoveredObject = object;
    },
  });

  const plantInteractiveLayer = new ScatterplotLayer({
    id: "scatterplot-layer",
    // TODO: we should always display all plants — need to update
    data: allPlants.features,
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
      tooltipState.x = x;
      tooltipState.y = y;
      tooltipState.hoveredObject = object;
    },
  });

  var displayLayers = [plantAccessLayer, plantInteractiveLayer, plantLayer];

  if (stateMapSettings.displayFarms) {
    displayLayers.push(barnsLayer);
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
      >
        <ScaleControl unit="imperial" position="top-right" />
        {/* <NavigationControl position="top-right" /> TODO: This is "under" the Deck map... */}
      </Map>

      <div id="legend" className="mb-5 mr-1">
        {Object.entries(plantColorPalette).map(([key, color]) => (
          <div key={key} className="flex items-center pl-2">
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
