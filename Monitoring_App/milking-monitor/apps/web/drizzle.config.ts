import type { Config } from "drizzle-kit";
import * as dotenv from "dotenv";

dotenv.config({ path: ".env.local" });

const config: Config = {
  schema: ["./lib/db/schema/*.ts"],
  out: "./drizzle",
  dialect: "postgresql",
  verbose: true,

  dbCredentials: {
    url: process.env.DATABASE_URL!,
  },
};

export default config;
