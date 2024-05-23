import { Storage } from '@google-cloud/storage';
import { NextResponse } from "next/server";

// const PLANTS = "test_plants.geojson";
const PLANTS = "plants.geojson";
const bucketName = 'rafi-poultry';
const serviceAccountKey = JSON.parse(Buffer.from(process.env.GOOGLE_APPLICATION_CREDENTIALS_BASE64, 'base64').toString('ascii'));

let data = []
let cleanedData = []
let salesData = []

const getData = async () => {
    const storage = new Storage({
        credentials: serviceAccountKey
    });
    const bucket = storage.bucket(bucketName);
    const file = bucket.file(PLANTS);
    const [fileContents] = await file.download();
    data = JSON.parse(fileContents.toString('utf-8'));
}

// cleaned data {
//   "geometry": {
//     "type": "Point",
//     "coordinates": [
//       -75.857209030472,
//       38.634687992108
//     ]
//   },
//   "properties": {
//     "Parent Corporation": "Amick",
//     "Establishment Name": "AMICK FARMS, LLC",
//     "Address": "274 NEALSON STREET ",
//     "City": "HURLOCK",
//     "State": "MD",
//     "Zip": "21643",
//     "Sales": 16286400
//   }
// }

// plants data example {
//   "type": "Feature",
//   "properties": {
//     "EstNumber": "P1317 + V1317",
//     "EstID": 4495,
//     "Parent Corporation": "Cargill",
//     "Establishment Name": "Wayne Farms LLC",
//     "State": "Alabama",
//     "Size": "Large",
//     "Animals Processed": "Chicken",
//     "Processed\nVolume\nCategory": 5,
//     "Slaughter\nVolume\nCategory": 5,
//     "Full Address": "700 McDonald Avenue, Albertville, AL 35950",
//     "latitude": 34.2607264,
//     "longitude": -86.203222,
//     "Sales Volume (Location)": 438268
//   },
//   "geometry": {
//     "type": "Point",
//     "coordinates": [
//       -86.203222,
//       34.2607264
//     ]
//   }
// }

const getCleanData = (data) => {
    let cleanedArray = data.features.map((plant) => {
        return {
            geometry: plant.geometry,
            properties: {...plant.properties, "Sales Volume (Location)": undefined,}
        }
    })

    cleanedData = {
        type: "FeatureCollection",
        features: cleanedArray
    }
}

const getSalesData = (data) => {
      let stateSales = {};
      
      // Group sales volume by state and then by parent corporation
      data.features.forEach(feature => {
        const state = feature.properties["State"];
        const parentCorp = feature.properties["Parent Corporation"];
        // const salesVolume = Number(feature.properties["Sales Volume (Location)"]);
        const salesVolume = Number(feature.properties["Sales"]);

        
        if (!stateSales[state]) {
          stateSales[state] = {};
        }
        
        if (!stateSales[state][parentCorp]) {
          stateSales[state][parentCorp] = 0;
        }
        
        if (!Number.isNaN(salesVolume)) {
          stateSales[state][parentCorp] += salesVolume;
        }
      });
      
      Object.keys(stateSales).forEach(state => {
        const totalSales = Object.values(stateSales[state]).reduce((sum, current) => sum + current, 0);
        
        Object.keys(stateSales[state]).forEach(corp => {
          stateSales[state][corp] = {
            sales: stateSales[state][corp],
            percent: (stateSales[state][corp] / totalSales) * 100
          };
        });
        
      });
      
      salesData = stateSales;

}

export async function GET(req, reqParams) {
    if (data.length == 0) {
        await getData()
    }

    if (reqParams.params.datatype == "plants") {
        if (cleanedData.length == 0) {
            getCleanData(data)
        }
        return NextResponse.json(cleanedData, { status: 200 });
    }

    if (reqParams.params.datatype == "sales") {
        if (salesData.length == 0) {
            getSalesData(data)
        }
        return NextResponse.json(salesData, { status: 200 });
    }
}