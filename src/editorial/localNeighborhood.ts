const EXACT_NEIGHBORHOOD_LABELS: Record<string, string> = {
  "eado point": "EaDo",
  "eado place": "EaDo",
  "west university place": "West University",
  "hyde park main": "River Oaks",
  "hyde park / river oaks area": "River Oaks",
  "stuart terrace / midtown": "Midtown",
  "stuart terrace": "Midtown",
  "five hundred 05": "Montrose",
  "newer heights manor / brooke smith": "Brooke Smith",
  "houston heights annex": "Heights",
  "george heights": "Heights",
  "twenty 03 street manors rep 01": "Shady Acres",
  "cadogan place": "River Oaks"
};

const CONTAINS_NEIGHBORHOOD_LABELS: Array<[RegExp, string]> = [
  [/\beado\b/i, "EaDo"],
  [/\bwest university\b|\bwest u\b/i, "West University"],
  [/\briver oaks\b/i, "River Oaks"],
  [/\bcadogan place\b/i, "River Oaks"],
  [/\bmidtown\b/i, "Midtown"],
  [/\bmontrose\b|\bmenil\b|\bmuseum district\b/i, "Montrose"],
  [/\bbrooke smith\b/i, "Brooke Smith"],
  [/\bshady acres\b/i, "Shady Acres"],
  [/\bstudemont heights\b|\brice military\b|\bwashington corridor\b/i, "Rice Military"],
  [/\bheights\b/i, "Heights"]
];

export function localNeighborhoodLabel(neighborhood: string | undefined): string | undefined {
  const normalized = neighborhood?.trim();
  if (!normalized) {
    return undefined;
  }

  const exact = EXACT_NEIGHBORHOOD_LABELS[normalized.toLowerCase()];
  if (exact) {
    return exact;
  }

  for (const [pattern, label] of CONTAINS_NEIGHBORHOOD_LABELS) {
    if (pattern.test(normalized)) {
      return label;
    }
  }

  return normalized;
}
