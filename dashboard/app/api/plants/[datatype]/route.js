import { Storage } from '@google-cloud/storage';
import { NextResponse } from "next/server";
import path from "path";
import fs from 'fs';

const PLANTS = "test_plants.geojson";
const bucketName = 'rafi-poultry';
const serviceAccountKey = JSON.parse(Buffer.from(process.env.GOOGLE_APPLICATION_CREDENTIALS_BASE64, 'base64').toString('ascii'));


// TODO: This is the version for loading the files locally
// export async function GET(_req) {
//     const filePath = path.join(process.cwd(), 'public', 'data', PLANTS);
//     const fileContents = fs.readFileSync(filePath);
//     const data = JSON.parse(fileContents);
//     return NextResponse.json(data, { status: 200 });
//   }

// folder/[datatype]

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

const cleanData = (data) => {
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

export async function GET(req, reqParams) {
    // const storage = new Storage({
    //     credentials: serviceAccountKey
    // });
    // const bucket = storage.bucket(bucketName);
    // const file = bucket.file(PLANTS);
    // console.log(file)
    // //accessing params: reqParams.params.datatype
    // const [fileContents] = await file.download();
    // const data = JSON.parse(fileContents.toString('utf-8'));

    if (data.length == 0) {
        await getData()
    }

    console.log("data", JSON.stringify(data.features[0], null, 2))

    if (cleanedData.length == 0) {
        cleanData(data)
    }

    console.log("cleanData", cleanData)

    if (reqParams.params.datatype == "plants") {
        return NextResponse.json(cleanedData, { status: 200 });
    }

    //include logic for returning either plants or HHI here
    return NextResponse.json(data, { status: 200 });
}