import type { EditorialAngle, ListingRecord } from "../types/domain.js";
import type { EnrichmentMappedFields } from "../enrichment/enrichmentAdapter.js";

export interface ScoringInput {
  listing: ListingRecord;
  enrichment?: EnrichmentMappedFields;
}

export interface ScoringRuleHit {
  angle: EditorialAngle;
  points: number;
  note: string;
}

export interface ScoringResult {
  score: number;
  hits: ScoringRuleHit[];
}

const INNER_LOOP_PRICE_PER_SQFT_REFERENCE = 330;
const RARE_LOT_THRESHOLD = 5000;
const OLD_HOME_YEAR_THRESHOLD = 1940;
const STRONG_VALUE_MULTIPLIER = 0.76;
const MODEST_VALUE_MULTIPLIER = 0.88;

export function scoreListing(input: ScoringInput): ScoringResult {
  const facts = mergeFacts(input);
  const hits: ScoringRuleHit[] = [];

  if (facts.lotSquareFeet && facts.lotSquareFeet >= RARE_LOT_THRESHOLD) {
    hits.push({
      angle: "rarity",
      points: 2,
      note: `Rare lot signal: ${facts.lotSquareFeet.toLocaleString()} sq ft lot.`
    });
  }

  const pricePerSqft = facts.price && facts.squareFeet ? facts.price / facts.squareFeet : undefined;
  if (pricePerSqft && pricePerSqft < INNER_LOOP_PRICE_PER_SQFT_REFERENCE * STRONG_VALUE_MULTIPLIER) {
    hits.push({
      angle: "value_mismatch",
      points: 2.5,
      note: `Unusual value signal: about $${Math.round(pricePerSqft)}/sq ft.`
    });
  } else if (pricePerSqft && pricePerSqft < INNER_LOOP_PRICE_PER_SQFT_REFERENCE * MODEST_VALUE_MULTIPLIER) {
    hits.push({
      angle: "value_mismatch",
      points: 1.25,
      note: `Modest value signal: about $${Math.round(pricePerSqft)}/sq ft.`
    });
  }

  if (facts.yearBuilt && facts.yearBuilt <= OLD_HOME_YEAR_THRESHOLD) {
    hits.push({
      angle: "character",
      points: 2,
      note: `Character signal: older home built around ${facts.yearBuilt}.`
    });
  }

  if (facts.description && /featured|architect|published|custom|historic|bungalow|craftsman|mid[- ]century|london inspired/i.test(facts.description)) {
    hits.push({
      angle: "character",
      points: 2,
      note: "Character signal: description points to design, architectural, or old-house interest."
    });
  }

  if (facts.description && /teardown|as-is|needs work|renovation|investor|lot value|tradeoffs?|limited parking|congestion/i.test(facts.description)) {
    hits.push({
      angle: "tradeoff",
      points: 2,
      note: "Tradeoff signal: description suggests condition, redevelopment, or everyday-location tension."
    });
  }

  if (facts.neighborhood && /heights|montrose|rice military|museum|west university|eado/i.test(facts.neighborhood)) {
    hits.push({
      angle: "location_hook",
      points: 0.75,
      note: `Location hook: ${facts.neighborhood}.`
    });
  }

  if (facts.beds && facts.beds >= 3 && facts.baths && facts.baths >= 2 && facts.squareFeet && facts.squareFeet >= 1600) {
    hits.push({
      angle: "buyer_usefulness",
      points: 0.5,
      note: "Buyer-usefulness signal: practical bed/bath/size mix."
    });
  }

  if (facts.description && /private driveway|first floor|first-floor|corner unit|corner home|actual yard|backyard|balcony|garage apartment|guest quarters/i.test(facts.description)) {
    hits.push({
      angle: "buyer_usefulness",
      points: 1.25,
      note: "Buyer-usefulness signal: description names a specific layout, parking, or outdoor-life advantage."
    });
  }

  return {
    score: hits.reduce((sum, hit) => sum + hit.points, 0),
    hits
  };
}

function mergeFacts({ listing, enrichment }: ScoringInput) {
  return {
    neighborhood: listing.neighborhood,
    price: enrichment?.price ?? listing.price,
    beds: enrichment?.beds ?? listing.beds,
    baths: enrichment?.baths ?? listing.baths,
    squareFeet: enrichment?.squareFeet ?? listing.squareFeet,
    lotSquareFeet: enrichment?.lotSquareFeet ?? listing.lotSquareFeet,
    yearBuilt: enrichment?.yearBuilt,
    description: enrichment?.description
  };
}
