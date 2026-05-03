CREATE TABLE IF NOT EXISTS listings (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  source_url TEXT NOT NULL UNIQUE,
  source_message_id TEXT,
  address TEXT,
  neighborhood TEXT,
  price INTEGER,
  beds REAL,
  baths REAL,
  square_feet INTEGER,
  lot_square_feet INTEGER,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS enrichment_snapshots (
  id TEXT PRIMARY KEY,
  listing_id TEXT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  mapped_fields_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS editorial_scores (
  listing_id TEXT PRIMARY KEY REFERENCES listings(id) ON DELETE CASCADE,
  selected INTEGER NOT NULL,
  score REAL NOT NULL,
  angles_json TEXT NOT NULL,
  rationale TEXT NOT NULL,
  rejection_reason TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS issue_runs (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  neighborhoods_json TEXT NOT NULL,
  selected_listing_ids_json TEXT NOT NULL,
  rejected_listing_ids_json TEXT NOT NULL,
  calibration_report_path TEXT,
  spiral_artifact_path TEXT,
  draft_artifact_path TEXT,
  substack_draft_url TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS run_events (
  id TEXT PRIMARY KEY,
  issue_run_id TEXT REFERENCES issue_runs(id) ON DELETE SET NULL,
  stage TEXT NOT NULL,
  level TEXT NOT NULL,
  message TEXT NOT NULL,
  metadata_json TEXT,
  created_at TEXT NOT NULL
);
