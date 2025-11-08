import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { chat_id, role, content } = body;

    const result = await query(
      `INSERT INTO messages (chat_id, role, content, created_at)
       VALUES ($1, $2, $3, NOW())
       RETURNING *`,
      [chat_id, role, content]
    );

    return NextResponse.json(result.rows[0]);
  } catch (error: any) {
    console.error('Error creating message:', error);
    return NextResponse.json(
      { error: error.message || 'Failed to create message' },
      { status: 500 }
    );
  }
}

