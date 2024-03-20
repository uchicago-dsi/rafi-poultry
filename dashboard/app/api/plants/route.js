import { NextResponse } from "next/server";
import Papa from "papaparse";
import path from "path";
import fs from 'fs';

const PLANTS = "location_match_fullest.csv";

export async function GET(_req) {
    const filePath = path.join(process.cwd(), 'public', 'data', PLANTS);
    const fileContents = fs.readFileSync(filePath);
    return NextResponse.json(fileContents, { status: 200 });
}