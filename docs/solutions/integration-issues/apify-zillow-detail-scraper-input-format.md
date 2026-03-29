---
title: "Apify zillow-detail-scraper: correct input format and response parsing"
date: 2026-03-01
category: integration-issues
tags: [apify, zillow, enrichment, api-integration]
components: [src/enrichment/apify_client.py]
severity: high
symptoms:
  - "Apify run fails with 'No Zillow details to scrape'"
  - "TypeError: expected string or bytes-like object, got 'dict' in address_normalizer.py"
  - "Enrichment returns 0 matches for all listings"
---

# Apify zillow-detail-scraper: correct input format and response parsing

## Problem

The Zillow enrichment pipeline via Apify's `maxcopell/zillow-detail-scraper` actor was completely non-functional. Two separate issues:

1. **Wrong input field**: We were sending `searchUrls` with constructed Zillow search URLs. The actor silently ignored them and reported "No Zillow details to scrape."
2. **Wrong response parsing**: When the input was fixed, the actor returned `address` as a dict (not a string), crashing `usaddress.tag()` with a TypeError. Invalid addresses returned `isValid: false` objects that also weren't handled.

## Symptoms

- Apify actor status message: `No Zillow details to scrape`
- All listings fell back to `har_only` enrichment (0% match rate)
- After fixing input: `TypeError: expected string or bytes-like object, got 'dict'` in `address_normalizer.py:92`

## Root Cause

The actor's input schema (retrieved via Apify API `client.build(build_id).get()['inputSchema']`) showed:

```json
{
  "addresses": {
    "title": "Addresses",
    "type": "array",
    "description": "Addresses to scrape - should be in format 123 Main St, City, State",
    "editor": "stringList"
  },
  "startUrls": {
    "title": "Home detail URLs",
    "type": "array",
    "description": "URLs to scrape - should be in format https://www.zillow.com/homedetails/Address/12345678_zpid/"
  },
  "propertyStatus": {
    "title": "Status of properties in Start URLs",
    "type": "string",
    "enum": ["FOR_SALE", "RECENTLY_SOLD", "FOR_RENT"]
  }
}
```

We were using a non-existent `searchUrls` field. The actor accepts either `addresses` (plain strings) or `startUrls` (detail page URLs with ZPIDs).

The response format for valid results:
```json
{
  "address": {
    "streetAddress": "2501 Yupon St",
    "city": "Houston",
    "state": "TX",
    "zipcode": "77006"
  },
  "description": "Welcome to the epitome of luxury...",
  "hdpUrl": "/homedetails/2501-Yupon-St-Houston-TX-77006/27788954_zpid/"
}
```

For invalid addresses:
```json
{
  "addressOrUrlFromInput": "3917 Tennyson St, West University Place TX 77005",
  "invalidReason": "Invalid address or Zillow has no data for this address",
  "isValid": false
}
```

## Solution

### 1. Fixed input format (use `addresses` field)

```python
# Before (broken)
run_input = {
    "searchUrls": [
        {"url": f"https://www.zillow.com/homes/{query}_rb/"}
        for query in search_queries
    ],
    "maxItems": len(search_queries) * 3,
}

# After (working)
run_input = {
    "addresses": search_queries,
    "propertyStatus": "FOR_SALE",
}
```

### 2. Handle dict `address` field in response

```python
raw_address = item.get("address")
if isinstance(raw_address, dict):
    parts = [
        raw_address.get("streetAddress", ""),
        raw_address.get("city", ""),
        raw_address.get("state", ""),
        raw_address.get("zipcode", ""),
    ]
    address = ", ".join(p for p in parts if p)
else:
    address = raw_address or item.get("streetAddress", "")
```

### 3. Handle `isValid: false` responses

```python
if item.get("isValid") is False:
    return ZillowResult(
        success=False,
        address=item.get("addressOrUrlFromInput", ""),
        error=item.get("invalidReason", "Invalid address"),
    )
```

## How to discover actor input schemas

The Apify web docs didn't render properly. The reliable method is querying the API directly:

```python
from apify_client import ApifyClient
import json

client = ApifyClient(token="your_token")
actor = client.actor("maxcopell/zillow-detail-scraper").get()
build_id = actor["taggedBuilds"]["latest"]["buildId"]
build = client.build(build_id).get()
schema = json.loads(build["inputSchema"])
print(json.dumps(schema, indent=2))
```

## Prevention

- Always retrieve and verify actor input schemas via the Apify API before writing integration code
- Test with a small batch (3-5 items) before running full batches
- Log raw API responses during development to catch schema mismatches early
- Check for `isValid` or error indicators in responses from any external API
