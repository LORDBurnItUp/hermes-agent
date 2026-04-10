import { NextRequest, NextResponse } from "next/server";
import { search } from "@/lib/search";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("q") || "";

  if (!query.trim()) {
    return NextResponse.json([]);
  }

  const results = search(query);
  return NextResponse.json(results);
}
