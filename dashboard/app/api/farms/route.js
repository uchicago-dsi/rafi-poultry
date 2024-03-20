import { NextResponse } from "next/server";
import path from "path";
import fs from 'fs';

const FARMS = "test_barns.geojson";

export async function GET(_req) {
  const filePath = path.join(process.cwd(), 'public', 'data', FARMS);
  const fileContents = fs.readFileSync(filePath);
  const data = JSON.parse(fileContents);
  return NextResponse.json(data, { status: 200 });
}