"use client";
// app.js
import React, { useState, useEffect } from "react";
import { useSnapshot } from "valtio";

import { state, updateFilteredData } from "../lib/state";

// import "tailwindcss/tailwind.css";
// import "../styles/styles.css";

export default function ControlPanel() {
  const snapshot = useSnapshot(state.stateData);
  const [expanded, setExpanded] = useState(true);

  //TODO: still not totally confident on when to use state vs snapshot and what triggers a reload

  if (!snapshot.isDataLoaded) {
    return <div>Loading...</div>;
  }

  const handleCheckboxChange = (event) => {
    const { checked, value } = event.target;

    // adjust filtered states
    if (checked) {
      state.stateData.filteredStates.push(value);
    } else {
      const index = state.stateData.filteredStates.indexOf(value);
      if (index !== -1) {
        state.stateData.filteredStates.splice(index, 1);
      }
    }

    updateFilteredData();
  };

  const selectAll = () => {
    state.stateData.filteredStates = [...state.stateData.allStates];
    updateFilteredData();
  };

  const selectNone = () => {
    state.stateData.filteredStates.length = 0;
    updateFilteredData();
  };

  const updateFarmDisplay = () => {
    state.stateMapSettings.displayFarms = !state.stateMapSettings.displayFarms;
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
        {snapshot.allStates.map((option, index) => (
          <label key={index} className="label cursor-pointer py-1">
            <span className="block label-text">{option}</span>
            <input
              className="checkbox checkbox-xs block"
              value={option}
              type="checkbox"
              checked={snapshot.filteredStates.includes(option)}
              onChange={handleCheckboxChange}
            />
          </label>
        ))}
      </div>
      <div>
        <button>Select All</button>
      </div>
      <div>
        <button>Select None</button>
      </div>
      <div>
        <button onClick={updateFarmDisplay}>Change Farm Display</button>
      </div>
    </div>
  );
}
