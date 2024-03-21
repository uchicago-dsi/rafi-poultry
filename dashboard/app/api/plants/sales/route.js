import { Storage } from '@google-cloud/storage';
import { NextResponse } from "next/server";

const PLANTS = "test_plants.geojson";
const bucketName = 'rafi-poultry';
const serviceAccountKey = JSON.parse(Buffer.from(process.env.GOOGLE_APPLICATION_CREDENTIALS_BASE64, 'base64').toString('ascii'));



function getFilteredSales(filteredData) {
    const salesSummary = filteredData.reduce((acc, item) => {
        const corporation = item.properties['Parent Corporation'];
        const salesVolume = item.properties['Sales Volume (Location)'];
  
        if (acc[corporation]) {
          acc[corporation] += salesVolume;
        } else {
          acc[corporation] = salesVolume;
        }
  
        return acc;
      }, {});

    return salesSummary;
}


//     // build dictionary for each company
//     let companySales = {};
//     for (let i = 0; i < state.stateData.filteredCompanies.length; i++) {
//       companySales[state.stateData.filteredCompanies[i]] = 0;
//     }
  
//     for (let i = 0; i < state.stateData.filteredPlants.length; i++) {
//       let salesVolume =
//         state.stateData.filteredPlants[i].properties["Sales Volume (Location)"];
//       if (!Number.isNaN(salesVolume)) {
//         companySales[
//           state.stateData.filteredPlants[i].properties["Parent Corporation"]
//         ] += salesVolume;
//       }
//     }
  
//     // filter NaN values and return dictionary
//     let filtered = Object.entries(companySales).reduce(
//       (filtered, [key, value]) => {
//         if (!Number.isNaN(value)) {
//           filtered[key] = value;
//         }
//         return filtered;
//       },
//       {}
//     );
  
//     // sort on value and convert to object
//     let sorted = Object.entries(filtered).sort((a, b) => b[1] - a[1]);
//     let unnestedSales = Object.fromEntries(sorted);
  
//     const totalSales = Object.values(unnestedSales).reduce(
//       (accumulator, value) => {
//         return accumulator + value;
//       },
//       0
//     );
  
//     // create nested object for each corporation
//     let nestedSales = {};
//     for (let key in unnestedSales) {
//       nestedSales[key] = {
//         sales: unnestedSales[key],
//         percent: unnestedSales[key] / totalSales,
//       };
//     }
//     state.stateData.filteredSales = nestedSales;
//   }

export async function GET(req) {
    const url = new URL(req.url, `http://${req.headers.host}`);
    const stateName = url.searchParams.get('state');

    const storage = new Storage({
        credentials: serviceAccountKey
    });
    const bucket = storage.bucket(bucketName);
    const file = bucket.file(PLANTS);
    const [fileContents] = await file.download();
    const data = JSON.parse(fileContents.toString('utf-8'));
    let filteredData = data;
    if (stateName) {
        filteredData = data.features.filter(item => item.properties.State === stateName);
    }
    let salesSummary = getFilteredSales(filteredData);
    console.log(salesSummary);
    return NextResponse.json(salesSummary, { status: 200 });
}