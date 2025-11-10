import { NextRequest, NextResponse } from 'next/server';

// This route handles ToG queries with increased timeout for long-running operations
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Get authorization header
    const authHeader = request.headers.get('authorization');

    // Forward request to backend with extended timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000); // 120 seconds timeout

    try {
      const backendResponse = await fetch('http://localhost:8000/api/tog/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authHeader && { 'Authorization': authHeader }),
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!backendResponse.ok) {
        const errorText = await backendResponse.text();
        return NextResponse.json(
          { error: errorText || 'Backend request failed' },
          { status: backendResponse.status }
        );
      }

      const data = await backendResponse.json();
      return NextResponse.json(data);

    } catch (fetchError) {
      clearTimeout(timeoutId);

      if (fetchError instanceof Error && fetchError.name === 'AbortError') {
        return NextResponse.json(
          { error: 'Request timeout - query took longer than 120 seconds' },
          { status: 504 }
        );
      }
      throw fetchError;
    }

  } catch (error) {
    console.error('ToG query API route error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}

// Increase the route segment config timeout
export const maxDuration = 120; // 120 seconds for Vercel/Next.js
export const dynamic = 'force-dynamic';
