/**
 * Migration script to run SQL migrations on PostgreSQL database
 * Usage: node scripts/migrate.js
 */

// Load environment variables from .env.local (Next.js convention) or .env
const fs = require("fs");
const path = require("path");
const dotenv = require("dotenv");

const envPath = path.join(__dirname, "../.env.local");
if (fs.existsSync(envPath)) {
  dotenv.config({ path: envPath });
  console.log("Loaded environment from .env.local");
} else {
  dotenv.config(); // Fallback to .env
  console.log("Loaded environment from .env");
}

const { Pool } = require("pg");

const pool = new Pool({
  host: process.env.POSTGRES_HOST || "localhost",
  port: parseInt(process.env.POSTGRES_PORT || "5433"),
  database: process.env.POSTGRES_DB || "lola_db",
  user: process.env.POSTGRES_USER || "lola",
  password: process.env.POSTGRES_PASSWORD || "lola_dev_password",
});

// Test connection first
pool.on("error", (err) => {
  console.error("Unexpected error on idle client", err);
  process.exit(-1);
});

async function runMigrations() {
  // Test connection first
  try {
    await pool.query("SELECT NOW()");
    console.log("✓ Database connection successful");
  } catch (error) {
    console.error("✗ Database connection failed:", error.message);
    console.error("Connection details:", {
      host: process.env.POSTGRES_HOST || "localhost",
      port: process.env.POSTGRES_PORT || "5433",
      database: process.env.POSTGRES_DB || "lola_db",
      user: process.env.POSTGRES_USER || "lola",
    });
    await pool.end();
    process.exit(1);
  }

  const migrationsDir = path.join(__dirname, "../supabase/migrations");
  const files = fs
    .readdirSync(migrationsDir)
    .filter((file) => file.endsWith(".sql"))
    .sort();

  console.log(`Found ${files.length} migration files`);

  for (const file of files) {
    console.log(`Running migration: ${file}`);
    const sql = fs.readFileSync(path.join(migrationsDir, file), "utf8");

    try {
      await pool.query(sql);
      console.log(`✓ Successfully applied: ${file}`);
    } catch (error) {
      console.error(`✗ Error applying ${file}:`, error.message);
      // Continue with other migrations
    }
  }

  await pool.end();
  console.log("Migration complete!");
}

runMigrations().catch(console.error);
