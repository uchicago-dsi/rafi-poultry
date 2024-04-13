import { Storage } from '@google-cloud/storage';
import fs from 'fs';
import { NextResponse } from "next/server";
import path from "path";

const bucketName = 'rafi-poultry';
// const FARMS = "test_barns_filtering_NC_MS_AR.geojson";
const BARNS = "filtered_barns.geojson";
const serviceAccountKey = JSON.parse(Buffer.from(process.env.GOOGLE_APPLICATION_CREDENTIALS_BASE64, 'base64').toString('ascii'));

const DATA_SOURCE = "cloud" // "local" or "cloud"

export async function GET(_req) {
  if (DATA_SOURCE == "local") {
    const filePath = path.join(process.cwd(), 'public', 'data', BARNS);
    const fileContents = fs.readFileSync(filePath);
    const data = JSON.parse(fileContents);
    return NextResponse.json(data, { status: 200 });
  }
  else {
    const storage = new Storage({
        credentials: serviceAccountKey
      });
    const bucket = storage.bucket(bucketName);
    const file = bucket.file(BARNS);
    console.log(file)
    const [fileContents] = await file.download();
    const data = JSON.parse(fileContents.toString('utf-8'));
    return NextResponse.json(data, { status: 200 });
  }
}