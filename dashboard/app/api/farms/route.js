import { Storage } from '@google-cloud/storage';
import { NextResponse } from "next/server";
import path from "path";
import fs from 'fs';

const FARMS = "test_barns.geojson";

// TODO: This is the version for loading locally
// export async function GET(_req) {
//   const filePath = path.join(process.cwd(), 'public', 'data', FARMS);
//   const fileContents = fs.readFileSync(filePath);
//   const data = JSON.parse(fileContents);
//   return NextResponse.json(data, { status: 200 });
// }

export async function GET(_req) {
    const storage = new Storage();
    const bucket = storage.bucket(bucketName);
    const file = bucket.file(FARMS);
    console.log(file)
    const [fileContents] = await file.download();
    const data = JSON.parse(fileContents.toString('utf-8'));
    return NextResponse.json(data, { status: 200 });
  }