"use client";
import { useMapData } from "@/lib/useMapData";
import PieChart from "@/components/PieChart";
import PieChartSales from "@/components/PieChartSales";

export function SummaryStats() {
  const { isDataLoaded, filteredSales, HHI, filteredBarns } = useMapData();

  if (!isDataLoaded) {
    return "";
  }

  return (
    <div className="overflow-y-scroll overflow-x-hidden flex flex-row py-2 my-2">
      {filteredSales && Object.keys(filteredSales).length > 0 ? (
        <div className="p-2 w-[342px]">
          {filteredBarns && Object.keys(filteredBarns).length > 0 ? (
            <div>
              <h2 className="text-center text-xl font-bold px-3">
                Percentage of Barns in Captured Areas in Selected States
              </h2>
              <div className="flex flex-row justify-center h-[25vh]">
                <PieChart />
              </div>
            </div>
          ) : (
            <p className="text-center ml-4">No barn data available</p>
          )}
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
          <div className="max-h-[50vh]">
            <table className="table table-sm">
              <thead className="sticky">
                <tr>
                  <th className="max-w-xs whitespace-normal">Company</th>
                  <th className="max-w-xs whitespace-normal">Sales</th>
                  <th className="max-w-xs whitespace-normal">
                    Percent of Sales
                  </th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(filteredSales).map(([key, item]) => (
                  <tr key={key}>
                    <td className="break-words max-w-xs">{key}</td>
                    <td className="break-words max-w-xs">
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
          </div>
        </div>
      ) : (
        <p className="text-center ml-4">No data available</p>
      )}
    </div>
  );
}
