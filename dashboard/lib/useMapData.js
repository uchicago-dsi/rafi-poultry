import { useSnapshot } from "valtio";
import { state, filterTimestampStore, staticFilteredState, staticDataStore } from "./state";

export const useMapData = () => {
  const { stateData, stateMapSettings } = useSnapshot(state);
  const { timestamp } = useSnapshot(filterTimestampStore);
  const { 
    filteredBarns, 
    filteredPlantsData,
    filteredCompanies,
    filteredSales,
    filteredCaptureAreas,
    capturedAreas,
    totalFarms,
    plantAccess,
  } = staticFilteredState;

  const { 
    allPlants 
  } = staticDataStore || {};

  return {
    stateMapSettings,
    isDataLoaded: stateData.isDataLoaded,
    filteredCompanies,
    filteredSales,
    filteredCaptureAreas,
    capturedAreas,
    totalFarms,
    plantAccess,
    timestamp,
    filteredBarns,
    filteredPlantsData,
    allPlants,
  };
};
