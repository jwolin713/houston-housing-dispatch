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

  it("extracts ordered listings from HAR saved search digests", () => {
    const listings = parseHarEmail({
      id: "msg-3",
      subject: "HAR.com Saved Search Notification (May 16, 2026)",
      text:
        "Saved Search Notification Report Date: 05/16/2026 HV Inner Loop - All New Listing " +
        "2314 Huldy St B&zwnj;, Houston TX 77019 Located in Hyde Park Main 3 bedrooms 2 full & 1 half bathroom 2,729 sqft $645,000 For Sale - Active View Listing " +
        "New Listing 505 W Alabama St C&zwnj;, Houston TX 77006 Located in Five Hundred 05 3 bedrooms 3 full & 1 half bathroom 2,905 sqft $750,000 For Sale - Active View Listing",
      html:
        '<a href="https://www.har.com/homedetail/2314-huldy-st-b-houston-tx-77019/8096007?lid=10887164">View Listing</a>' +
        '<a href="https://www.har.com/homedetail/505-w-alabama-st-c-houston-tx-77006/9663817?lid=10883588">View Listing</a>'
    });

    expect(listings).toEqual([
      {
        sourceUrl: "https://www.har.com/homedetail/2314-huldy-st-b-houston-tx-77019/8096007?lid=10887164",
        address: "2314 Huldy St B",
        neighborhood: "Hyde Park Main",
        price: 645000,
        beds: 3,
        baths: 2.5,
        squareFeet: 2729
      },
      {
        sourceUrl: "https://www.har.com/homedetail/505-w-alabama-st-c-houston-tx-77006/9663817?lid=10883588",
        address: "505 W Alabama St C",
        neighborhood: "Five Hundred 05",
        price: 750000,
        beds: 3,
        baths: 3.5,
        squareFeet: 2905
      }
    ]);
  });
});
