import { Storage } from "@google-cloud/storage";
import { NextResponse } from "next/server";
import pako from "pako";

const BARNS = "barns.geojson.gz";
const bucketName = "rafi-poultry";
const serviceAccountKey = JSON.parse(
  Buffer.from(
    process.env.GOOGLE_APPLICATION_CREDENTIALS_BASE64,
    "base64"
  ).toString("ascii")
);

let data = [];

const getData = async () => {
  const storage = new Storage({
    credentials: serviceAccountKey,
  });
  const bucket = storage.bucket(bucketName);
  const file = bucket.file(BARNS);
  try {
    const [fileContents] = await file.download();
    const decompressed = pako.inflate(fileContents, { to: "string" });
    data = JSON.parse(decompressed);
  } catch (error) {
    console.error("Error downloading or decompressing file:", error);
  }
};

const processBarns = (barns) => {
  let processedBarns = {
    type: "FeatureCollection",
    features: barns.features.filter(
      (feature) =>
        feature.properties.exclude === 0 &&
        feature.properties.integrator_access !== null
    ),
  };
  return processedBarns;
};

const calculateCapturedBarns = (data) => {
  const countsByState = {};

  data.features.forEach((feature) => {
    const state = feature.properties.state;
    const plantAccess =
      feature.properties.integrator_access === 4
        ? 3
        : feature.properties.integrator_access || 0; // Convert 4 to 3, default to 0 if null

    if (!countsByState[state]) {
      countsByState[state] = {
        totalBarns: 0,
        plantAccessCounts: {
          0: 0, // '0' represents NaN or no access
          1: 0,
          2: 0,
          3: 0,
        },
      };
    }

    const stateCounts = countsByState[state];
    stateCounts.totalBarns += 1;
    stateCounts.plantAccessCounts[plantAccess] += 1;
  });

  return countsByState;
};

export async function GET(req, reqParams) {
  if (data.length == 0) {
    await getData();
  }

  data = processBarns(data);

  if (reqParams.params.datatype == "barns") {
    return NextResponse.json(data, { status: 200 });
  }

  if (reqParams.params.datatype == "counts") {
    const barnCounts = calculateCapturedBarns(data);
    return NextResponse.json(barnCounts, { status: 200 });
  }
}
