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

export async function GET(req, reqParams) {
  if (data.length == 0) {
    await getData();
  }

  return NextResponse.json(data, { status: 200 });
}
