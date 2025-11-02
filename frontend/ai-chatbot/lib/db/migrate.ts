import { config } from "dotenv";
import { drizzle } from "drizzle-orm/postgres-js";
import { migrate } from "drizzle-orm/postgres-js/migrator";
import postgres from "postgres";

import {
  describeMigrationSkipDecision,
  shouldSkipMigrations,
} from "./helpers/should-skip-migrations";

config({
  path: ".env.local",
});

const runMigrate = async () => {
  const skipDecision = shouldSkipMigrations(process.env);

  if (skipDecision.skip) {
    // Provide explicit context so CI contributors immediately understand why
    // the migrations step was skipped. This dramatically cuts down on
    // confusion when Playwright toggles the in-memory DB path.
    console.log(describeMigrationSkipDecision(skipDecision));
    process.exit(0);
  }

  if (!process.env.POSTGRES_URL) {
    throw new Error(
      "POSTGRES_URL is not defined. Provide the variable or set SKIP_DB_MIGRATIONS=1 to bypass migrations during offline builds.",
    );
  }

  const connection = postgres(process.env.POSTGRES_URL, { max: 1 });
  const db = drizzle(connection);

  console.log("⏳ Running migrations...");

  const start = Date.now();
  await migrate(db, { migrationsFolder: "./lib/db/migrations" });
  const end = Date.now();

  console.log("✅ Migrations completed in", end - start, "ms");
  process.exit(0);
};

runMigrate().catch((err) => {
  console.error("❌ Migration failed");
  console.error(err);
  process.exit(1);
});
