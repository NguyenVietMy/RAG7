import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';

export async function GET() {
  try {
    const result = await query(
      `SELECT * FROM rag_settings 
       ORDER BY created_at DESC 
       LIMIT 1`
    );

    if (result.rows.length === 0) {
      // Return defaults if no config exists
      return NextResponse.json({
        rag_n_results: 3,
        rag_similarity_threshold: 0.0,
        rag_max_context_tokens: 2000,
      });
    }

    return NextResponse.json(result.rows[0]);
  } catch (error: any) {
    console.error('Error fetching RAG settings:', error);
    return NextResponse.json(
      { error: error.message || 'Failed to fetch RAG settings' },
      { status: 500 }
    );
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const { rag_n_results, rag_similarity_threshold, rag_max_context_tokens } = body;

    // Check if config exists
    const checkResult = await query('SELECT id FROM rag_settings LIMIT 1');

    let result;
    if (checkResult.rows.length > 0) {
      // Update existing
      result = await query(
        `UPDATE rag_settings 
         SET rag_n_results = $1, 
             rag_similarity_threshold = $2, 
             rag_max_context_tokens = $3,
             updated_at = NOW()
         WHERE id = $4
         RETURNING *`,
        [
          rag_n_results,
          rag_similarity_threshold,
          rag_max_context_tokens,
          checkResult.rows[0].id,
        ]
      );
    } else {
      // Insert new
      result = await query(
        `INSERT INTO rag_settings (rag_n_results, rag_similarity_threshold, rag_max_context_tokens, created_at, updated_at)
         VALUES ($1, $2, $3, NOW(), NOW())
         RETURNING *`,
        [rag_n_results, rag_similarity_threshold, rag_max_context_tokens]
      );
    }

    return NextResponse.json(result.rows[0]);
  } catch (error: any) {
    console.error('Error upserting RAG settings:', error);
    return NextResponse.json(
      { error: error.message || 'Failed to save RAG settings' },
      { status: 500 }
    );
  }
}

