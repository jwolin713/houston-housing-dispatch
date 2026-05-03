import { config as loadDotenv } from "dotenv";
import { z } from "zod";

loadDotenv();

const EnvSchema = z.object({
  DISPATCH_DB_PATH: z.string().min(1).default("./data/dispatch.sqlite"),
  DISPATCH_NEIGHBORHOODS: z.string().min(1).default("Heights,Montrose"),
  DISPATCH_RUN_CADENCE: z.enum(["weekly", "twice-weekly"]).default("weekly"),
  GMAIL_QUERY: z.string().min(1).default("from:(har.com) newer_than:14d"),
  GMAIL_CLIENT_ID: z.string().optional(),
  GMAIL_CLIENT_SECRET: z.string().optional(),
  GMAIL_REFRESH_TOKEN: z.string().optional(),
  APIFY_TOKEN: z.string().optional(),
  APIFY_ZILLOW_ACTOR_ID: z.string().optional(),
  SPIRAL_API_KEY: z.string().optional(),
  SUBSTACK_BASE_URL: z.string().url().optional().or(z.literal("")),
  SUBSTACK_SESSION_TOKEN: z.string().optional(),
  OPERATOR_ACCESS_TOKEN: z.string().optional()
});

export type AppConfig = ReturnType<typeof loadConfig>;

export function loadConfig(env: NodeJS.ProcessEnv = process.env) {
  const parsed = EnvSchema.parse(env);

  return {
    dbPath: parsed.DISPATCH_DB_PATH,
    neighborhoods: parsed.DISPATCH_NEIGHBORHOODS.split(",")
      .map((neighborhood) => neighborhood.trim())
      .filter(Boolean),
    runCadence: parsed.DISPATCH_RUN_CADENCE,
    gmail: {
      query: parsed.GMAIL_QUERY,
      clientId: parsed.GMAIL_CLIENT_ID,
      clientSecret: parsed.GMAIL_CLIENT_SECRET,
      refreshToken: parsed.GMAIL_REFRESH_TOKEN
    },
    apify: {
      token: parsed.APIFY_TOKEN,
      zillowActorId: parsed.APIFY_ZILLOW_ACTOR_ID
    },
    spiral: {
      apiKey: parsed.SPIRAL_API_KEY
    },
    substack: {
      baseUrl: parsed.SUBSTACK_BASE_URL || undefined,
      sessionToken: parsed.SUBSTACK_SESSION_TOKEN
    },
    operatorAccessToken: parsed.OPERATOR_ACCESS_TOKEN
  };
}

export function requireConfigValue(value: string | undefined, name: string): string {
  if (!value) {
    throw new Error(`Missing required configuration: ${name}`);
  }

  return value;
}
