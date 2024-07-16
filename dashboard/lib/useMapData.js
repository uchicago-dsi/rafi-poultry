import { useSnapshot } from "valtio";
import {
  state,
  filterTimestampStore,
  filteredDataStore,
  staticDataStore,
} from "@/lib/state";

export const useMapData = () => {
  const stateMapSettings = useSnapshot(state.map);
  const stateData = useSnapshot(state.data);

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
