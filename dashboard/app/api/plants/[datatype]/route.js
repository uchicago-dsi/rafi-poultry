import { Storage } from '@google-cloud/storage';
import { NextResponse } from "next/server";
import path from "path";
import fs from 'fs';

const PLANTS = "test_plants.geojson";
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
        const salesVolume = Number(feature.properties["Sales Volume (Location)"]);
        
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
      
      // Calculate total sales for each state and percentages
      Object.keys(stateSales).forEach(state => {
        const totalSales = Object.values(stateSales[state]).reduce((sum, current) => sum + current, 0);
        
        Object.keys(stateSales[state]).forEach(corp => {
          // Optionally, sort corporations by sales volume here if needed
          // Convert sales volume to a nested object including percentage
          stateSales[state][corp] = {
            sales: stateSales[state][corp],
            percent: (stateSales[state][corp] / totalSales) * 100
          };
        });
        
        // Sort corporations within each state by sales volume, if needed
        // This step can be adjusted based on whether sorting is required and how you want to handle the sorted data
      });
      
      salesData = stateSales;

}

export async function GET(req, reqParams) {
    if (data.length == 0) {
        await getData()
    }

    console.log("data", JSON.stringify(data.features[0], null, 2))

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