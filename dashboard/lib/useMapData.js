import { useSnapshot } from "valtio";
import { state, filterTimestampStore, staticFilteredState, staticDataStore } from "./state";

export const useMapData = () => {
  const { stateData, stateMapSettings } = useSnapshot(state);
  const { timestamp } = useSnapshot(filterTimestampStore);
  const { 
    filteredFarmsData, 
    filteredPlantsData,
    filteredCompanies,
    filteredSales,
    filteredCaptureAreas,
    capturedAreas,
    totalFarms,
    plantAccess,
  } = staticFilteredState;

  const { 
    poultryPlants 
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
    filteredFarmsData,
    filteredPlantsData,
    poultryPlants,
  };
};