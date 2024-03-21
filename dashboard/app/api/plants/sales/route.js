import { Storage } from '@google-cloud/storage';
import { NextResponse } from "next/server";

const PLANTS = "test_plants.geojson";
const bucketName = 'rafi-poultry';
const serviceAccountKey = JSON.parse(Buffer.from(process.env.GOOGLE_APPLICATION_CREDENTIALS_BASE64, 'base64').toString('ascii'));

console.log("in the upside down")

// function getFilteredSales(filteredData) {
//     const salesSummary = filteredData.features.reduce((acc, item) => {
//         const corporation = item.properties['Parent Corporation'];
//         const salesVolume = item.properties['Sales Volume (Location)'];

//         // Filter data with missing corporations or NaN values
//         if (!corporation || isNaN(salesVolume) ) {
//             return acc;
//           }
  
//         if (acc[corporation]) {
//           acc[corporation] += salesVolume;
//         } else {
//           acc[corporation] = salesVolume;
//         }
  
//         return acc;
//       }, {});

//     const totalSales = Object.values(salesSummary).reduce((total, salesVolume ) => total + salesVolume, 0);

//     // create nested object for each corporation
//     let nestedSales = {};
//     for (let key in salesSummary) {
//         nestedSales[key] = {
//         sales: salesSummary[key],
//         percent: salesSummary[key] / totalSales,
//         };
//     }
    
//     return nestedSales;
// }

// export async function GET(req) {
//     const url = new URL(req.url, `http://${req.headers.host}`);
//     const stateNamesParam = url.searchParams.get('state');
//     const stateNames = stateNamesParam ? stateNamesParam.split(',').map(name => name.trim()) : [];

//     const storage = new Storage({
//         credentials: serviceAccountKey
//     });
//     const bucket = storage.bucket(bucketName);
//     const file = bucket.file(PLANTS);
//     const [fileContents] = await file.download();
//     const data = JSON.parse(fileContents.toString('utf-8'));
//     let filteredData = data;
//     if (stateNames.length) {
//         filteredData.features = data.features.filter(item => stateNames.includes(item.properties.State))
//     }
//     let salesSummary = getFilteredSales(filteredData);
//     return NextResponse.json(salesSummary, { status: 200 });
// }

export async function GET(_req) {
    // const storage = new Storage({
    //     credentials: serviceAccountKey
    // });
    // const bucket = storage.bucket(bucketName);
    // const file = bucket.file(PLANTS);
    // console.log(file)
    // const [fileContents] = await file.download();
    // const data = JSON.parse(fileContents.toString('utf-8'));

    let lol = {}

    // TODO: Make this change once the other endpoint is working in context
    // Remove sales data (proprietary data that can't be exposed disaggregated)
    // const modifiedData = data.features.map(item => {
    //     const newItem = {...item}; // Shallow copy to avoid mutating the original data
    //     delete newItem.properties['Sales Volume (Location)']; // Remove the sales data
    //     return newItem;
    // });
    return NextResponse.json(lol, { status: 200 });
}