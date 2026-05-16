import { describe, expect, it } from "vitest";
import { GmailApiClient, type GmailMessagesResource } from "../src/integrations/gmail/client.js";

function encodeBase64Url(value: string): string {
  return Buffer.from(value, "utf8").toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

describe("GmailApiClient", () => {
  it("paginates Gmail message search results", async () => {
    const queries: Array<{ q: string; pageToken?: string }> = [];
    const resource: GmailMessagesResource = {
      async list(params) {
        queries.push({ q: params.q, pageToken: params.pageToken });
        if (!params.pageToken) {
          return {
            data: {
              messages: [{ id: "msg-1", threadId: "thread-1" }],
              nextPageToken: "page-2"
            }
          };
        }

        return {
          data: {
            messages: [{ id: "msg-2" }, { threadId: "missing-id" }]
          }
        };
      },
      async get() {
        throw new Error("not used");
      }
    };

    const messages = await new GmailApiClient({ query: "", clientId: undefined, clientSecret: undefined, refreshToken: undefined }, resource).listMessages(
      "from:(har.com)"
    );

    expect(messages).toEqual([{ id: "msg-1", threadId: "thread-1" }, { id: "msg-2" }]);
    expect(queries).toEqual([{ q: "from:(har.com)" }, { q: "from:(har.com)", pageToken: "page-2" }]);
  });

  it("extracts headers and recursive text/html bodies", async () => {
    const resource: GmailMessagesResource = {
      async list() {
        return { data: {} };
      },
      async get(params) {
        return {
          data: {
            id: params.id,
            payload: {
              headers: [
                { name: "Subject", value: "New HAR listings" },
                { name: "From", value: "alerts@har.com" },
                { name: "Date", value: "Sun, 03 May 2026 10:00:00 -0500" }
              ],
              parts: [
                {
                  mimeType: "multipart/alternative",
                  parts: [
                    {
                      mimeType: "text/plain",
                      body: { data: encodeBase64Url("Address: 1234 Harvard St") }
                    },
                    {
                      mimeType: "text/html",
                      body: { data: encodeBase64Url("<p>Address: <strong>1234 Harvard St</strong></p>") }
                    }
                  ]
                }
              ]
            }
          }
        };
      }
    };

    const message = await new GmailApiClient({ query: "", clientId: undefined, clientSecret: undefined, refreshToken: undefined }, resource).getMessage(
      "msg-1"
    );

    expect(message).toEqual({
      id: "msg-1",
      subject: "New HAR listings",
      from: "alerts@har.com",
      date: "Sun, 03 May 2026 10:00:00 -0500",
      text: "Address: 1234 Harvard St",
      html: "<p>Address: <strong>1234 Harvard St</strong></p>"
    });
  });

  it("uses stripped HTML as text when a text/plain part is unavailable", async () => {
    const resource: GmailMessagesResource = {
      async list() {
        return { data: {} };
      },
      async get() {
        return {
          data: {
            id: "msg-html",
            payload: {
              parts: [
                {
                  mimeType: "text/html",
                  body: { data: encodeBase64Url("<p>Price: $725,000 &amp; private driveway</p>") }
                }
              ]
            }
          }
        };
      }
    };

    const message = await new GmailApiClient({ query: "", clientId: undefined, clientSecret: undefined, refreshToken: undefined }, resource).getMessage(
      "msg-html"
    );

    expect(message.text).toBe("Price: $725,000 & private driveway");
    expect(message.html).toBe("<p>Price: $725,000 &amp; private driveway</p>");
  });
});
