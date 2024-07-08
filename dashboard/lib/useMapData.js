import { useSnapshot } from "valtio";
import {
  state,
  filterTimestampStore,
  filteredDataStore,
  staticDataStore,
} from "./state";

export const useMapData = () => {
  const { data: stateData, map: stateMapSettings } = useSnapshot(state);
  const { timestamp } = useSnapshot(filterTimestampStore);
  const {
    filteredBarns,
    filteredPlants,
    filteredCompanies,
    filteredSales,
    filteredIsochrones,
    percentCapturedBarns,
    totalCapturedBarns,
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
    percentCapturedBarns,
    totalCapturedBarns,
    plantAccess,
    timestamp,
    filteredBarns,
    filteredPlants,
    allPlants,
    HHI,
  };
};
