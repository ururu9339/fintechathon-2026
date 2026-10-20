import type { ApprovalStatus, CheckStatus, Payment, TransferStatus } from "./api";

type PillTone = "jade" | "muted" | "warning";

// Checks, approval and transfer are independent axes: approval never means money moved.
export const checkStatus: Record<CheckStatus, { label: string; tone: PillTone }> = {
  not_run: { label: "Not run", tone: "muted" },
  within_rules: { label: "Within rules", tone: "jade" },
  limit_exception: { label: "Limit exception", tone: "warning" },
  blocked: { label: "Blocked", tone: "warning" },
  stale: { label: "Stale", tone: "muted" },
};

export const approvalStatus: Record<ApprovalStatus, { label: string; tone: PillTone }> = {
  draft: { label: "Draft", tone: "muted" },
  needs_approval: { label: "Needs approval", tone: "warning" },
  approved_by_mandate: { label: "Approved by mandate", tone: "jade" },
  approved_by_owner: { label: "Approved by owner", tone: "jade" },
  rejected: { label: "Rejected", tone: "muted" },
  expired: { label: "Expired", tone: "muted" },
};

export const transferStatus: Record<TransferStatus, string> = {
  not_sent: "Not sent",
  scheduled: "Scheduled",
  sending: "Sending",
  sent: "Sent",
  settled: "Settled",
  failed: "Failed",
  cancelled: "Cancelled",
  pending_confirmation: "Pending confirmation",
};

export const needsOwner = (payment: Payment) => payment.approval === "needs_approval";

/** One-line rule-check result, e.g. "Amount exception · MYR 700 above limit". */
export function checkSummary(payment: Payment): string {
  if (payment.checks === "not_run") return "Draft · Not run";
  return payment.check_summary ?? checkStatus[payment.checks].label;
}
