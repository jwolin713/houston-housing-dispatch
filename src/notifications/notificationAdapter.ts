export interface DispatchReadyNotification {
  issueRunId: string;
  selected: number;
  rejected: number;
  draftPath: string;
  calibrationReportPath: string;
  spiralInputPath: string;
  substackTouched: boolean;
}

export interface NotificationAdapter {
  notifyDispatchReady(notification: DispatchReadyNotification): Promise<void>;
}

export class NoopNotificationAdapter implements NotificationAdapter {
  async notifyDispatchReady(): Promise<void> {
    return undefined;
  }
}

export class WebhookNotificationAdapter implements NotificationAdapter {
  constructor(
    private readonly webhookUrl: string,
    private readonly fetchImpl: typeof fetch = fetch
  ) {}

  async notifyDispatchReady(notification: DispatchReadyNotification): Promise<void> {
    const response = await this.fetchImpl(this.webhookUrl, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        event: "dispatch_draft_ready",
        text: `Houston Housing Dispatch draft is ready: ${notification.draftPath}`,
        ...notification
      })
    });

    if (!response.ok) {
      throw new Error(`Notification webhook failed: HTTP ${response.status}`);
    }
  }
}
