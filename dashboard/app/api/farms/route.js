import { NextResponse } from "next/server";
import path from "path";
import fs from 'fs';

const DATA_DIR = "public/data/"
const FARMS = "test_barns_filtering.geojson";

const getJSON = async (dataPath) => {
    const response = await fetch(dataPath);
    return await response.json();
  };

export async function GET(_req) {
//   const jsonPath = path.join(process.cwd(), DATA_DIR, FARMS);
  const filePath = path.join(process.cwd(), 'public', 'data', 'test_barns_filtering.geojson');
  const fileContents = fs.readFileSync(filePath);
  const data = JSON.parse(fileContents);
//   const data = await getJSON(jsonPath)
  return NextResponse.json(data, { status: 200 });
}