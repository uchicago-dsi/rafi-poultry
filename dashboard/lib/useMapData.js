import { useSnapshot } from "valtio";
import { state, filterTimestampStore, filteredDataStore, staticDataStore } from "./state";

export const useMapData = () => {
  const { data: stateData, map: stateMapSettings } = useSnapshot(state);
  const { timestamp } = useSnapshot(filterTimestampStore);
  const { 
    filteredBarns, 
    filteredPlants,
    filteredCompanies,
    filteredSales,
    filteredIsochrones,
    capturedAreas,
    totalFarms,
    plantAccess,
  } = filteredDataStore;

  const { 
    allPlants 
  } = staticDataStore || {};

  return {
    stateMapSettings,
    isDataLoaded: stateData.isDataLoaded,
    filteredCompanies,
    filteredSales,
    filteredIsochrones, 
    capturedAreas,
    totalFarms,
    plantAccess,
    timestamp,
    filteredBarns,
    filteredPlants,
    allPlants,
  };
};
