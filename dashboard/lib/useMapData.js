import { derive } from "valtio/utils";
import { useSnapshot } from "valtio";
import {
  state,
} from "./state";
import {
  staticDataStore
} from "./data";
import { state2abb } from "./constants";

export const staticFilteredState = {
  filteredFarmsData: [],
  filteredPlantsData: [],
};

const filterPlantsData = (states, isDataLoaded) => {
  if (!isDataLoaded) {
    return null;
  }
  const features = staticDataStore.allPlants.features
    ? staticDataStore.allPlants.features.filter((row) =>
        states.includes(row.properties.State)
      )
    : [];
  staticFilteredState.filteredPlantsData = features;
  return performance.now();
};

const filterFarmsData = (states, isDataLoaded) => {
  if (!isDataLoaded) {
    return null;
  }
  const stateabbrevs = states.map((state) => state2abb[state]);

  if (staticDataStore?.allFarms?.features?.length) {
    const _features=  staticDataStore.allFarms.features
    const features = []
    for (let i = 0; i < _features.length; i++) {
      const isInState = stateabbrevs.includes(_features[i].properties.state);
      const isExcluded = _features[i].properties.exclude === 0;
      const hasPlantAccess = _features[i].properties.plant_access !== null;
      if (isInState && isExcluded && hasPlantAccess) {
        features.push(_features[i]);
      }
    }

    staticFilteredState.filteredFarmsData = features;
  }
  return performance.now();
};

export const filteredDataStore = derive({
  filteredFarmsData: (get) =>
    filterFarmsData(
      get(state).stateData.filteredStates,
      get(state).stateData.isDataLoaded
    ),
  filteredPlantsData: (get) =>
    filterPlantsData(
      get(state).stateData.filteredStates,
      get(state).stateData.isDataLoaded
    ),
});


export const useMapData = () => {
  const { stateData, stateMapSettings } = useSnapshot(state);

  const {
    filteredFarmsData,
    filteredPlantsData,
  } = staticFilteredState;

  const {
    poultryPlants
  } = staticDataStore || {};

  return {
    stateMapSettings,
    isDataLoaded: stateData.isDataLoaded,
    timestampState: filteredDataStore,
    filteredFarmsData,
    filteredPlantsData,
    filteredCaptureAreas: [],
    poultryPlants,
  }
}