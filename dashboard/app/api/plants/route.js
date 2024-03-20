import { Storage } from '@google-cloud/storage';
import { NextResponse } from "next/server";
import path from "path";
import fs from 'fs';

// const PLANTS = "test_plants.geojson";

// TODO: This is the version for loading the files locally
// export async function GET(_req) {
//     const filePath = path.join(process.cwd(), 'public', 'data', PLANTS);
//     const fileContents = fs.readFileSync(filePath);
//     const data = JSON.parse(fileContents);
//     return NextResponse.json(data, { status: 200 });
//   }

const PLANTS = "test_plants.geojson";
const bucketName = 'rafi-poultry';

export async function GET(_req) {
  const storage = new Storage();
  const bucket = storage.bucket(bucketName);
  const file = bucket.file(PLANTS);
  console.log(file)
  const [fileContents] = await file.download();
  const data = JSON.parse(fileContents.toString('utf-8'));
  return NextResponse.json(data, { status: 200 });
}