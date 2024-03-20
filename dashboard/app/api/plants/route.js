import { NextResponse } from "next/server";
import path from "path";
import fs from 'fs';

const PLANTS = "test_plants.geojson";

export async function GET(_req) {
    const filePath = path.join(process.cwd(), 'public', 'data', PLANTS);
    const fileContents = fs.readFileSync(filePath);
    const data = JSON.parse(fileContents);
    return NextResponse.json(data, { status: 200 });
  }