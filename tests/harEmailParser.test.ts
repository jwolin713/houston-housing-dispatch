import { describe, expect, it } from "vitest";
import { parseHarEmail } from "../src/intake/harEmailParser.js";

describe("parseHarEmail", () => {
  it("extracts a representative HAR listing from email text", () => {
    const listings = parseHarEmail({
      id: "msg-1",
      subject: "New HAR listing",
      text: "Address: 1234 Harvard St Neighborhood: Heights Price: $725,000 Beds: 3 Baths: 2.5 2,050 sqft https://www.har.com/homedetail/1234-harvard-st/123456"
    });

    expect(listings).toEqual([
      {
        sourceUrl: "https://www.har.com/homedetail/1234-harvard-st/123456",
        address: "1234 Harvard St",
        neighborhood: "Heights",
        price: 725000,
        beds: 3,
        baths: 2.5,
        squareFeet: 2050
      }
    ]);
  });

  it("deduplicates repeated listing links in one message", () => {
    const listings = parseHarEmail({
      id: "msg-2",
      text: "See https://www.har.com/homedetail/example/1 and again https://www.har.com/homedetail/example/1."
    });

    expect(listings).toHaveLength(1);
    expect(listings[0].sourceUrl).toBe("https://www.har.com/homedetail/example/1");
  });
});
