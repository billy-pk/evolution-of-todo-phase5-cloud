import { Pool } from 'pg';
import { NextResponse } from 'next/server';

export async function GET() {
  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: process.env.DATABASE_URL?.includes('neon.tech')
      ? { rejectUnauthorized: false }
      : undefined,
  });

  try {
    const start = Date.now();
    const client = await pool.connect();
    const duration = Date.now() - start;

    const result = await client.query('SELECT NOW() as now, current_database() as db');
    client.release();
    await pool.end();

    return NextResponse.json({
      success: true,
      duration: `${duration}ms`,
      database: result.rows[0].db,
      timestamp: result.rows[0].now,
      connectionString: process.env.DATABASE_URL?.replace(/:[^:@]+@/, ':***@') // Hide password
    });
  } catch (error: any) {
    return NextResponse.json({
      success: false,
      error: error.message,
      code: error.code,
      connectionString: process.env.DATABASE_URL?.replace(/:[^:@]+@/, ':***@')
    }, { status: 500 });
  }
}
