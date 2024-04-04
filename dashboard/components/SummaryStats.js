"use client";
import { useMapData } from "@/lib/useMapData";

function calculateHHI(filteredSales) {
  // TODO: should probably make total sales part of the state
  // calculate total sales in selected area
  if (Object.keys(filteredSales).length) {
    let totalSales = Object.values(filteredSales).reduce(
      (acc, item) => acc + item.sales,
      0
    );

    // calculate HHI
    return Object.values(filteredSales).reduce(
      (acc, item) => acc + Math.pow((item.sales * 100) / totalSales, 2),
      0
    );
  } else {
    return 0;
  }
}

export function SummaryStats() {
  const {
    isDataLoaded,
    filteredSales,
    percentCapturedBarns,
    totalCapturedBarns
  } = useMapData();

  if (!isDataLoaded) {
    return "";
  }

  const calculatedHHI = calculateHHI(filteredSales);

  return (
    <div>
      {calculatedHHI ? (
        <div className="m-2">
          <h2 className="text-2xl font-bold text-center">
            HHI for Selected States
          </h2>
          <p className="text-center text-xl">{calculatedHHI.toFixed(0)}</p>
        </div>
      ) : (
        <p className="text-center">No data available</p>
      )}
      {percentCapturedBarns &&
      Object.keys(percentCapturedBarns).length > 0 ? (
        <div className="max-h-[75%] overflow-y-auto">
          <div className="flex justify-center m-10 ">
            <div>
              <table className="table table-sm">
                <tr>
                  <thead>
                    <th>% of Barns with Access to Integrators in Selected Area</th>
                  </thead>
                </tr>
                <tbody>
                  {Object.entries(percentCapturedBarns).map(([key, item]) => (
                    <tr key={key}>
                      <td>{key} Integrator(s)</td>
                      <td>{(item * 100).toFixed(1) + "%"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p>Total Barns: {totalCapturedBarns}</p>
            </div>
          </div>
        </div>
      ) : (
        ""
      )}
      <div className="max-h-[50vh] overflow-y-auto">
        {filteredSales &&
        Object.keys(filteredSales).length > 0 ? (
          <table className="table table-sm">
            <tr>
              <thead className="sticky">
                <tr>
                  <th>Company</th>
                  <th>Sales</th>
                  <th>Percent of Sales</th>
                </tr>
              </thead>
            </tr>
            <tbody>
              {Object.entries(filteredSales).map(([key, item]) => (
                <tr key={key}>
                  <td>{key}</td>
                  <td>
                    {(item.sales * 1000).toLocaleString("en-US", {
                      style: "currency",
                      currency: "USD",
                      minimumFractionDigits: 0,
                    })}
                  </td>
                  <td>{(item.percent * 100).toFixed(1) + "%"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          ""
        )}
      </div>
    </div>
  );
}
