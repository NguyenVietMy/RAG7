/**
 * Test script to debug PostgreSQL connection issues
 * Run with: npx tsx src/lib/db-connection-test.ts
 */

import { Pool } from 'pg';
import dotenv from 'dotenv';

dotenv.config({ path: '.env.local' });

const configs = [
  {
    name: 'From .env.local',
    config: {
      host: process.env.POSTGRES_HOST || 'localhost',
      port: parseInt(process.env.POSTGRES_PORT || '5433'),
      database: process.env.POSTGRES_DB || 'lola_db',
      user: process.env.POSTGRES_USER || 'lola',
      password: process.env.POSTGRES_PASSWORD || 'lola_dev_password',
      ssl: false,
    },
  },
  {
    name: 'Hardcoded values',
    config: {
      host: '127.0.0.1',
      port: 5433,
      database: 'lola_db',
      user: 'lola',
      password: 'lola_dev_password',
      ssl: false,
    },
  },
  {
    name: 'Connection string',
    config: {
      connectionString: 'postgresql://lola:lola_dev_password@127.0.0.1:5433/lola_db',
      ssl: false,
    },
  },
];

async function testConnections() {
  for (const { name, config } of configs) {
    console.log(`\nTesting: ${name}`);
    console.log('Config:', JSON.stringify(config, null, 2));
    
    const pool = new Pool(config as any);
    
    try {
      const result = await pool.query('SELECT version()');
      console.log('✓ SUCCESS!');
      console.log('Result:', result.rows[0].version);
      await pool.end();
      return; // Stop on first success
    } catch (error: any) {
      console.error('✗ FAILED:', error.message);
      console.error('Code:', error.code);
      await pool.end();
    }
  }
}

testConnections().catch(console.error);

