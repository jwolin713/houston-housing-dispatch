import { describe, expect, it } from "vitest";
import { mapZillowDetails } from "../src/enrichment/zillowDetailsMapper.js";

describe("mapZillowDetails", () => {
  it("maps a Zillow-style payload into normalized enrichment fields", () => {
    const mapped = mapZillowDetails({
      price: "$725,000",
      livingArea: "2050",
      lotAreaValue: "6600",
      bedrooms: "3",
      bathrooms: 2.5,
      yearBuilt: "1920",
      homeType: "SingleFamily",
      description: "A Heights bungalow with a rare lot.",
      photos: [{ url: "https://example.com/photo.jpg" }]
    });

    expect(mapped).toMatchObject({
      price: 725000,
      squareFeet: 2050,
      lotSquareFeet: 6600,
      beds: 3,
      baths: 2.5,
      yearBuilt: 1920,
      propertyType: "SingleFamily"
    });
    expect(mapped.photoUrls).toEqual(["https://example.com/photo.jpg"]);
  });

  it("leaves missing optional fields undefined", () => {
    const mapped = mapZillowDetails({ price: 500000 });

    expect(mapped.lotSquareFeet).toBeUndefined();
    expect(mapped.yearBuilt).toBeUndefined();
  });

  it("maps address-based actor payload fields", () => {
    const mapped = mapZillowDetails({
      streetAddress: "2314 Huldy St B",
      photoUrls: ["https://example.com/photo-1.jpg"],
      lotSize: 1400
    });

    expect(mapped.address).toBe("2314 Huldy St B");
    expect(mapped.photoUrls).toEqual(["https://example.com/photo-1.jpg"]);
    expect(mapped.lotSquareFeet).toBe(1400);
  });

  it("maps nested address payload fields", () => {
    const mapped = mapZillowDetails({
      address: {
        streetAddress: "2314 Huldy St B",
        city: "Houston",
        state: "TX",
        zipcode: "77019"
      }
    });

    expect(mapped.address).toBe("2314 Huldy St B, Houston, TX, 77019");
  });
});
