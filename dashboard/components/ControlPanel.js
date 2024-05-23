"use client";
// app.js
import React, { useState } from "react";
import { useSnapshot } from "valtio";
import { abb2state } from "@/lib/constants";

import { state, updateFilteredData, staticDataStore } from "../lib/state";


export default function ControlPanel() {
  const snapshot = useSnapshot(state.data);
  const [expanded, setExpanded] = useState(true);

  if (!snapshot.isDataLoaded) {
    return <div>Loading...</div>;
  }

  const handleCheckboxChange = (event) => {
    const { checked, value } = event.target;

    // adjust filtered states
    if (checked) {
      state.data.selectedStates.push(value);
    } else {
      const index = state.data.selectedStates.indexOf(value);
      if (index !== -1) {
        state.data.selectedStates.splice(index, 1);
      }
    }

    // TODO: does this need to be here also? Shouldn't this get triggered elsewhere?
    updateFilteredData();
  };

  const selectAll = () => {
    state.data.selectedStates = [...staticDataStore.allStates];
    // TODO: Is this the right way to do this?
    updateFilteredData();
  };

  const selectNone = () => {
    state.data.selectedStates.length = 0;
    // TODO: Is this the right way to do this?
    updateFilteredData();
  };

  const updateFarmDisplay = () => {
    state.map.displayFarms = !state.map.displayFarms;
  };

  return (
    <div className="w-full max-w-xs mx-auto">
      <p className="text-center">Select States</p>
      <div className="flex justify-center">
        <button
          className="btn btn-sm normal-case"
          onClick={() => setExpanded((e) => !e)}
        >
          {expanded ? "Collapse Menu" : "Show Menu"}
        </button>
      </div>
      <div
        className={`form-control h-0 overflow-hidden ${
          expanded && "h-auto overflow-auto max-h-full"
        }`}
      >
        <div className="divider m-0"></div>
        <div className="join justify-center">
          <button
            className="btn join-item btn-sm normal-case"
            onClick={selectAll}
          >
            All
          </button>
          <button
            className="btn join-item btn-sm normal-case"
            onClick={selectNone}
          >
            None
          </button>
        </div>
        {staticDataStore.allStates.map((option, index) => (
          <label key={index} className="label cursor-pointer py-1">
            <span className="block label-text">{abb2state[option]}</span>
            <input
              className="checkbox checkbox-xs block"
              value={option}
              type="checkbox"
              checked={snapshot.selectedStates.includes(option)}
              onChange={handleCheckboxChange}
            />
          </label>
        ))}
      </div>
      <div>
        <button onClick={updateFarmDisplay}>Change Farm Display</button>
      </div>
    </div>
  );
}
