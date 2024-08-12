import {
  filterTimestampStore,
  filteredDataStore,
  state,
  staticDataStore,
} from "@/lib/state";
import { useEffect } from "react";
import { useSnapshot } from "valtio";

export const useMapData = (mapRef) => {
  const stateMapSettings = useSnapshot(state.map);
  const stateData = useSnapshot(state.data);

  useEffect(() => {
    const flyToSelection = () => {
      if (
        !stateMapSettings.mapZoom ||
        isNaN(stateMapSettings.mapZoom.latitude) ||
        isNaN(stateMapSettings.mapZoom.longitude)
      ) {
        return;
      }

      mapRef?.current?.flyTo({
        center: [
          stateMapSettings.mapZoom.longitude,
          stateMapSettings.mapZoom.latitude,
        ],
        zoom: stateMapSettings.mapZoom.zoom,
      });
    };

    flyToSelection();
  }, [stateMapSettings, mapRef]);

  const { timestamp } = useSnapshot(filterTimestampStore);
  const {
    filteredBarns,
    filteredPlants,
    filteredCompanies,
    filteredSales,
    filteredIsochrones,
    filteredBarnPercents,
    plantAccess,
    HHI,
  } = filteredDataStore;

  const { allPlants } = staticDataStore || {};

  return {
    stateMapSettings,
    isDataLoaded: stateData.isDataLoaded,
    filteredCompanies,
    filteredSales,
    filteredIsochrones,
    filteredBarnPercents,
    plantAccess,
    timestamp,
    filteredBarns,
    filteredPlants,
    allPlants,
    HHI,
  };
};
