"use client";
import { useMapData } from "@/lib/useMapData";
import PieChart from "@/components/PieChart";
import PieChartSales from "@/components/PieChartSales";

export function SummaryStats() {
  const { isDataLoaded, filteredSales, HHI } = useMapData();

  if (!isDataLoaded) {
    return "";
  }

  return (
    <div className="overflow-y-auto flex flex-row py-2 my-2">
      {HHI ? (
        <div className="p-2">
          <h2 className="text-center text-xl font-bold">
            Percentage of Barns in Captured Areas in Selected States
          </h2>
          <div className="flex flex-row justify-center h-[25vh]">
            <PieChart />
          </div>
          {/* {totalCapturedBarns > 0 &&
          Object.keys(percentCapturedBarns).length > 0 ? (
            <div className="max-h-[75%] overflow-y-auto">
              <div className="flex justify-center m-10">
                <div className="w-full">
                  <h5 className="text-center">
                    % of Barns with Access to Integrators in Selected Area
                  </h5>
                  <table className="table table-sm">
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
          )} */}
          <div className="m-2">
            <h2 className="text-2xl font-bold text-center">
              HHI for Selected States
            </h2>
            <p className="text-center text-xl">{HHI.toFixed(0)}</p>
          </div>
          <h2 className="text-2xl font-bold text-center">
            Percentage of Sales by Integrator in Selected States
          </h2>
          <div className="flex flex-row justify-center h-[25vh]">
            <PieChartSales />
          </div>
          <div className="max-h-[50vh] overflow-y-auto">
            {filteredSales && Object.keys(filteredSales).length > 0 ? (
              <table className="table table-sm">
                <thead className="sticky">
                  <tr>
                    <th>Company</th>
                    <th>Sales</th>
                    <th>Percent of Sales</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(filteredSales).map(([key, item]) => (
                    <tr key={key}>
                      <td>{key}</td>
                      <td>
                        {item.sales.toLocaleString("en-US", {
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
              <p className="text-center">No data available</p>
            )}
          </div>
        </div>
      ) : (
        <p className="text-center">No data available</p>
      )}
    </div>
  );
}
