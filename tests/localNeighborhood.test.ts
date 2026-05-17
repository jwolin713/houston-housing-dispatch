import { describe, expect, it } from "vitest";
import { localNeighborhoodLabel } from "../src/editorial/localNeighborhood.js";

describe("localNeighborhoodLabel", () => {
  it("uses local-facing labels instead of HAR subdivision names", () => {
    expect(localNeighborhoodLabel("Eado Point")).toBe("EaDo");
    expect(localNeighborhoodLabel("West University Place")).toBe("West University");
    expect(localNeighborhoodLabel("Hyde Park / River Oaks Area")).toBe("River Oaks");
    expect(localNeighborhoodLabel("Stuart Terrace / Midtown")).toBe("Midtown");
    expect(localNeighborhoodLabel("Twenty 03 Street Manors Rep 01")).toBe("Shady Acres");
    expect(localNeighborhoodLabel("Cadogan Place")).toBe("River Oaks");
  });

  it("keeps useful local neighborhood names when they are already reader-facing", () => {
    expect(localNeighborhoodLabel("Shady Acres")).toBe("Shady Acres");
    expect(localNeighborhoodLabel("Brooke Smith")).toBe("Brooke Smith");
  });
});
