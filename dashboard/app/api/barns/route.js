import { Storage } from '@google-cloud/storage';
import fs from 'fs';
import { NextResponse } from "next/server";
import path from "path";
import { unpack } from "msgpackr";

const bucketName = 'rafi-poultry';
const BARNS = "all_barns.msgpack";
const serviceAccountKey = JSON.parse(Buffer.from(process.env.GOOGLE_APPLICATION_CREDENTIALS_BASE64, 'base64').toString('ascii'));

const DATA_SOURCE = "cloud" // "local" or "cloud"

export async function GET(_req) {
  if (DATA_SOURCE == "local") {
    const filePath = path.join(process.cwd(), 'public', 'data', BARNS);
    const fileContents = fs.readFileSync(filePath);
    const data = unpack(fileContents);
    console.log(data)
    return NextResponse.json(data, { status: 200 });
  }
  else {
    const storage = new Storage({
        credentials: serviceAccountKey
      });
    const bucket = storage.bucket(bucketName);
    const file = bucket.file(BARNS);
    // const [fileContents] = await file.download();
    // const data = unpack(fileContents);
    // return NextResponse.json(data, { status: 200 });
    const readStream = file.createReadStream();
    const chunks = []; // This array will hold our data chunks

    return new Promise((resolve, reject) => {
      readStream.on('data', (chunk) => {
        chunks.push(chunk); // Collect data chunks in an array
      }).on('end', () => {
        // Combine all the chunks and unpack the data
        const combined = Buffer.concat(chunks);
        const data = unpack(combined); // Unpack data after all chunks are received
        resolve(NextResponse.json(data, { status: 200 }));
      }).on('error', (error) => {
        console.error('Error downloading the file', error);
        reject(NextResponse.json({ error: 'Failed to download file' }, { status: 500 }));
      });
    });
  }
}