import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';

export async function GET() {
  try {
    const result = await query(
      `SELECT * FROM chats 
       WHERE is_archived = false 
       ORDER BY last_message_at DESC NULLS LAST, updated_at DESC 
       LIMIT 50`
    );
    return NextResponse.json(result.rows);
  } catch (error: any) {
    console.error('Error fetching chats:', error);
    return NextResponse.json(
      { error: error.message || 'Failed to fetch chats' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { title, collection_name } = body;

    const result = await query(
      `INSERT INTO chats (title, collection_name, created_at, updated_at)
       VALUES ($1, $2, NOW(), NOW())
       RETURNING *`,
      [title, collection_name || null]
    );

    return NextResponse.json(result.rows[0]);
  } catch (error: any) {
    console.error('Error creating chat:', error);
    return NextResponse.json(
      { error: error.message || 'Failed to create chat' },
      { status: 500 }
    );
  }
}

