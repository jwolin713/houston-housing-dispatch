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
  SPIRAL_DRAFT_MODE: z.enum(["manual", "cli"]).default("manual"),
  SPIRAL_GENERATION_MODE: z.enum(["instant", "interactive"]).default("instant"),
  SUBSTACK_BASE_URL: z.string().url().optional().or(z.literal("")),
  SUBSTACK_SESSION_TOKEN: z.string().optional(),
  NOTIFICATION_WEBHOOK_URL: z.string().url().optional().or(z.literal("")),
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
      apiKey: parsed.SPIRAL_API_KEY,
      draftMode: parsed.SPIRAL_DRAFT_MODE,
      generationMode: parsed.SPIRAL_GENERATION_MODE
    },
    substack: {
      baseUrl: parsed.SUBSTACK_BASE_URL || undefined,
      sessionToken: parsed.SUBSTACK_SESSION_TOKEN
    },
    notifications: {
      webhookUrl: parsed.NOTIFICATION_WEBHOOK_URL || undefined
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
