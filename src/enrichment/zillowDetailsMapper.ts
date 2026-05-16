import { z } from "zod";

const ZillowDetailsSchema = z
  .object({
    price: z.union([z.number(), z.string()]).optional(),
    livingArea: z.union([z.number(), z.string()]).optional(),
    lotAreaValue: z.union([z.number(), z.string()]).optional(),
    lotSize: z.union([z.number(), z.string()]).optional(),
    bedrooms: z.union([z.number(), z.string()]).optional(),
    bathrooms: z.union([z.number(), z.string()]).optional(),
    yearBuilt: z.union([z.number(), z.string()]).optional(),
    homeType: z.string().optional(),
    propertyType: z.string().optional(),
    description: z.string().optional(),
    address: z.union([
      z.string(),
      z.object({
        streetAddress: z.string().optional(),
        city: z.string().optional(),
        state: z.string().optional(),
        zipcode: z.string().optional()
      })
    ]).optional(),
    streetAddress: z.string().optional(),
    photoUrls: z.array(z.string()).optional(),
    photos: z.array(z.union([z.string(), z.object({ url: z.string().optional() })])).optional()
  })
  .passthrough();

export type ZillowDetailsPayload = z.infer<typeof ZillowDetailsSchema>;

export function mapZillowDetails(payload: unknown) {
  const parsed = ZillowDetailsSchema.parse(payload);

  return {
    address: normalizeAddress(parsed.address) ?? parsed.streetAddress,
    price: toNumber(parsed.price),
    beds: toNumber(parsed.bedrooms),
    baths: toNumber(parsed.bathrooms),
    squareFeet: toNumber(parsed.livingArea),
    lotSquareFeet: toNumber(parsed.lotAreaValue ?? parsed.lotSize),
    yearBuilt: toNumber(parsed.yearBuilt),
    propertyType: parsed.propertyType ?? parsed.homeType,
    description: parsed.description,
    photoUrls:
      parsed.photoUrls ?? parsed.photos?.map((photo) => (typeof photo === "string" ? photo : photo.url)).filter(isString)
  };
}

function normalizeAddress(address: ZillowDetailsPayload["address"]): string | undefined {
  if (!address) return undefined;
  if (typeof address === "string") return address;

  return [address.streetAddress, address.city, address.state, address.zipcode].filter(isString).join(", ");
}

function toNumber(value: string | number | undefined): number | undefined {
  if (value === undefined) return undefined;
  if (typeof value === "number") return Number.isFinite(value) ? value : undefined;
  const parsed = Number(value.replace(/[$,\s]/g, ""));
  return Number.isFinite(parsed) ? parsed : undefined;
}

function isString(value: string | undefined): value is string {
  return typeof value === "string" && value.length > 0;
}
