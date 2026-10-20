export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

export type CheckStatus = "not_run" | "within_rules" | "limit_exception" | "blocked" | "stale";
export type ApprovalStatus =
  | "draft"
  | "needs_approval"
  | "approved_by_mandate"
  | "approved_by_owner"
  | "rejected"
  | "expired";
export type TransferStatus =
  | "not_sent"
  | "scheduled"
  | "sending"
  | "sent"
  | "settled"
  | "failed"
  | "cancelled"
  | "pending_confirmation";

export type Workspace = {
  company: string;
  owner: string;
  owner_role: string;
  demo_date: string;
  updated_at: string;
  currency: string;
  demo_data: boolean;
  business_id: string;
};

export type Balances = { cash: number; reserved: number; available: number; as_of: string };
export type ForecastPoint = {
  week: number;
  week_of: string;
  opening_balance: number;
  money_in: number;
  money_out: number;
  closing_balance: number;
};
export type Scenario = "base" | "earlier_customer_payment" | "with_funding";
export type Forecast = {
  scenario: Scenario;
  currency: string;
  points: ForecastPoint[];
  lowest: ForecastPoint;
  first_gap: { week_of: string; amount: number; reason: string } | null;
};
export type WeekDetail = {
  scenario: Scenario;
  point: ForecastPoint;
  events: { event: string; money_in: number | null; money_out: number | null; confidence: string }[];
  note: string | null;
  delayed_receipt: {
    invoice_id: string;
    customer: string;
    amount: number;
    originally_due: string;
    now_expected: string;
  } | null;
};
export type Reserve = { key: string; name: string; target: number; allocated: number; next_due: string };
export type Commitment = {
  title: string;
  reference: string;
  due_on: string;
  amount: number;
  status: string;
  payment_id: string | null;
};
export type Obligation = { reserve_key: string; label: string; starts_on: string; ends_on: string; amount: number };
export type FinancingOption = {
  name: string;
  amount: number;
  term_days: number;
  fee: number;
  total_repayment: number;
  receipt_on: string;
  repayment_on: string;
};
export type Financing = {
  shortfall: number;
  needed_by: string;
  amount: number;
  buffer: number;
  purpose: string;
  options: FinancingOption[];
  amount_choices: number[];
  in_scenario: FinancingOption | null;
};
export type RuleCheck = {
  rule: "payee" | "purpose" | "per_payment_limit" | "daily_limit" | "expiry";
  label: string;
  outcome: "passed" | "exceeded" | "failed" | "deferred";
  summary: string;
  detail: string | null;
};
export type Payment = {
  id: string;
  payee: string;
  purpose: string;
  amount: number;
  due_on: string;
  reserve: string;
  bank_account: string;
  checks: CheckStatus;
  approval: ApprovalStatus;
  transfer: TransferStatus;
  rule_checks: RuleCheck[];
  check_summary: string | null;
  note: string | null;
  invoice_id?: string;
  ap_invoice_id?: string | null;
};
export type PaymentList = {
  payments: Payment[];
  summary: { needs_approval: number; ready_to_send: number; scheduled: number; completed: number };
  total: number;
};
export type Mandate = {
  id: string;
  name: string;
  status: "active" | "paused" | "revoked";
  owner: string;
  per_payment_limit: number;
  daily_limit: number;
  sent_today: number;
  allowed_payees: string[];
  allowed_purposes: string[];
  funding_reserve: string;
  expires_on: string;
  timezone: string;
};
export type ActivityItem = { at: string; actor: string; title: string; detail: string; event_hash: string };
export type AuditVerification = { valid: boolean; events: number; head_hash: string | null; broken_at: number | null };
export type PaymentRequest = {
  invoice_id: string;
  payee: string;
  purpose: string;
  amount: number;
  due_on: string;
};
export type AgentResponse = {
  status: "advisory" | "blocked" | "approved";
  message: string;
  created_at: string;
  context: string | null;
  tags: { label: string; tone: "neutral" | "warning" }[];
  plain_tags: string[];
  actions: { label: string; kind: "open_screen" | "review_payment"; target: string; primary: boolean }[];
  sources: { title: string; lines: string[]; target: string }[];
  payment_id: string | null;
};
export type SessionUser = { name: string; email: string; role: string; id?: string };
export type Session = { token: string; refresh_token: string; user: SessionUser; expires_at: string };

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

type Business = {
  id: string;
  legal_name: string;
  currency: string;
  created_at: string;
};
type CashBalance = { as_of_date: string; amount: number | string; currency: string };
type SalesInvoice = {
  id: string;
  total_amount: number | string;
  amount_received: number | string;
  status: string;
  issue_date: string;
  due_date: string | null;
};
type ExpenseInvoice = {
  id: string;
  invoice_number: string;
  supplier_name: string;
  total_amount: number | string;
  issue_date: string;
  due_date: string | null;
  status: string;
  review_notes: string | null;
  mandate_id: string | null;
};
type BackendPaymentRequest = {
  id: string;
  supplier: string;
  supplier_name: string | null;
  amount: number | string;
  purpose: string;
  invoice_id: string;
  invoice_number: string | null;
  ap_invoice_id: string | null;
  mandate_id: string;
  status: string;
};
type BackendMandate = {
  id: string;
  business_id: string | null;
  daily_limit: number | string;
  transaction_limit: number | string;
  allowed_suppliers: string[];
  purpose: string;
  expires_at: string;
  status: "active" | "paused" | "revoked";
};
type BackendAudit = {
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
  event_hash: string;
};

let token: string | null = null;
let refreshToken: string | null = null;
let businessId: string | null = null;
let sessionEnded: (() => void) | null = null;

const number = (value: number | string | null | undefined): number => Number(value ?? 0);
const today = () => new Date().toISOString().slice(0, 10);

export function setToken(value: string | null) {
  token = value;
}

export function setRefreshToken(value: string | null) {
  refreshToken = value;
}

export function onSessionEnded(handler: (() => void) | null) {
  sessionEnded = handler;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    if (response.status === 401 && token && path !== "/api/auth/login") sessionEnded?.();
    throw new ApiError(body?.detail ?? `Request failed (${response.status})`, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

const post = <T>(path: string, body: unknown = {}) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });

async function currentBusiness(): Promise<Business> {
  if (businessId) {
    const businesses = await request<Business[]>("/api/businesses");
    const found = businesses.find((item) => item.id === businessId);
    if (found) return found;
  }
  const businesses = await request<Business[]>("/api/businesses");
  const business = businesses[0];
  if (!business) throw new ApiError("No business is linked to this account.", 404);
  businessId = business.id;
  return business;
}

async function businessPath(path: string): Promise<string> {
  return `/api/businesses/${encodeURIComponent((await currentBusiness()).id)}${path}`;
}

function isoFromNow(minutes: number) {
  return new Date(Date.now() + minutes * 60_000).toISOString();
}

function mapPayment(item: BackendPaymentRequest | null, invoice?: ExpenseInvoice): Payment {
  const amount = number(item?.amount ?? invoice?.total_amount);
  const status = item?.status ?? invoice?.status ?? "draft";
  const approval: ApprovalStatus =
    status === "approved" ? "approved_by_mandate" :
    status === "paid" ? "approved_by_owner" :
    status === "rejected" || status === "blocked" ? "rejected" :
    status === "needs_review" ? "needs_approval" : "draft";
  const checks: CheckStatus =
    status === "blocked" || status === "needs_review" ? "blocked" :
    status === "draft" ? "not_run" : "within_rules";
  return {
    id: item?.id ?? invoice?.id ?? "unknown",
    payee: item?.supplier_name ?? item?.supplier ?? invoice?.supplier_name ?? "Unknown supplier",
    purpose: item?.purpose ?? "supplier invoice",
    amount,
    due_on: invoice?.due_date ?? invoice?.issue_date ?? today(),
    reserve: "Operating cash",
    bank_account: "Backend mandate",
    checks,
    approval,
    transfer: status === "paid" ? "settled" : status === "approved" ? "pending_confirmation" : "not_sent",
    rule_checks: [],
    check_summary: checks === "not_run" ? null : checks === "blocked" ? "Blocked by backend validation" : "Backend validation passed",
    note: invoice?.review_notes ?? null,
    invoice_id: item?.invoice_number ?? invoice?.invoice_number,
    ap_invoice_id: item?.ap_invoice_id ?? invoice?.id ?? null,
  };
}

function forecastFromSnapshot(snapshot: { snapshot: Record<string, unknown> }, scenario: Scenario): Forecast {
  const rawPoints = (snapshot.snapshot.points as { date: string; balance: string }[] | undefined) ?? [];
  const start = number(snapshot.snapshot.starting_balance as string);
  const inflow = number(snapshot.snapshot.average_daily_inflow as string);
  const outflow = number(snapshot.snapshot.average_daily_outflow as string) + number(snapshot.snapshot.average_daily_debt_service as string);
  const points: ForecastPoint[] = [];
  for (let index = 0; index < 13; index += 1) {
    const raw = rawPoints[Math.min(index * 7 + 6, Math.max(rawPoints.length - 1, 0))];
    const opening = index === 0 ? start : points[index - 1].closing_balance;
    const closing = raw ? number(raw.balance) : opening + (inflow - outflow) * 7;
    points.push({
      week: index + 1,
      week_of: raw?.date ?? today(),
      opening_balance: opening,
      money_in: inflow * 7,
      money_out: outflow * 7,
      closing_balance: closing,
    });
  }
  const lowest = points.reduce((a, b) => (b.closing_balance < a.closing_balance ? b : a), points[0]);
  const gap = points.find((point) => point.closing_balance < 0);
  return {
    scenario,
    currency: String(snapshot.snapshot.currency ?? "MYR"),
    points,
    lowest,
    first_gap: gap
      ? {
          week_of: gap.week_of,
          amount: Math.abs(gap.closing_balance),
          reason: "The backend forecast projects a negative cash balance.",
        }
      : null,
  };
}

async function loadForecast(scenario: Scenario): Promise<Forecast> {
  const path = await businessPath("/predictions/forecast?horizon_days=90");
  const snapshot = await post<{ snapshot: Record<string, unknown> }>(path);
  return forecastFromSnapshot(snapshot, scenario);
}

export const api = {
  login: async (email: string, password: string): Promise<Session> => {
    const result = await post<{
      access_token: string;
      refresh_token: string;
      user: { id: string; email: string };
    }>("/api/auth/login", { email, password });
    const session: Session = {
      token: result.access_token,
      refresh_token: result.refresh_token,
      user: { id: result.user.id, email: result.user.email, name: result.user.email.split("@")[0], role: "owner" },
      expires_at: isoFromNow(30),
    };
    token = session.token;
    refreshToken = session.refresh_token;
    businessId = null;
    return session;
  },

  me: async (): Promise<SessionUser> => {
    const user = await request<{ id: string; email: string }>("/api/auth/me");
    return { id: user.id, email: user.email, name: user.email.split("@")[0], role: "owner" };
  },

  logout: async () => {
    if (refreshToken) {
      await post("/api/auth/logout", { refresh_token: refreshToken });
    }
    token = null;
    refreshToken = null;
    businessId = null;
  },

  workspace: async (): Promise<Workspace> => {
    const [business, user, cash] = await Promise.all([
      currentBusiness(),
      api.me(),
      request<CashBalance[]>(await businessPath("/cash-balances")),
    ]);
    const latest = cash.sort((a, b) => b.as_of_date.localeCompare(a.as_of_date))[0];
    return {
      company: business.legal_name,
      owner: user.name,
      owner_role: user.role,
      demo_date: latest?.as_of_date ?? today(),
      updated_at: latest?.as_of_date ?? business.created_at,
      currency: business.currency,
      demo_data: false,
      business_id: business.id,
    };
  },

  balances: async (): Promise<Balances> => {
    const cash = await request<CashBalance[]>(await businessPath("/cash-balances"));
    const latest = cash.sort((a, b) => b.as_of_date.localeCompare(a.as_of_date))[0];
    const amount = number(latest?.amount);
    return { cash: amount, reserved: 0, available: amount, as_of: latest?.as_of_date ?? today() };
  },

  forecast: (scenario: Scenario = "base") => loadForecast(scenario),

  week: async (weekOf: string, scenario: Scenario = "base"): Promise<WeekDetail> => {
    const forecast = await loadForecast(scenario);
    return {
      scenario,
      point: forecast.points.find((point) => point.week_of === weekOf) ?? forecast.points[0],
      events: [],
      note: "This view is calculated from the backend's recorded accounting data.",
      delayed_receipt: null,
    };
  },

  reserves: async (): Promise<Reserve[]> => {
    const remittances = await request<{ statutory_type: string; amount: number | string; due_date: string }[]>(
      await businessPath("/statutory-remittances"),
    );
    const grouped = new Map<string, { amount: number; due: string }>();
    for (const item of remittances) {
      const current = grouped.get(item.statutory_type) ?? { amount: 0, due: item.due_date };
      current.amount += number(item.amount);
      current.due = current.due < item.due_date ? current.due : item.due_date;
      grouped.set(item.statutory_type, current);
    }
    return [...grouped.entries()].map(([key, value]) => ({
      key,
      name: key,
      target: value.amount,
      allocated: 0,
      next_due: value.due,
    }));
  },

  obligations: async (): Promise<Obligation[]> => {
    const remittances = await request<{ statutory_type: string; amount: number | string; payroll_month: string; due_date: string }[]>(
      await businessPath("/statutory-remittances"),
    );
    return remittances.map((item) => ({
      reserve_key: item.statutory_type,
      label: item.statutory_type,
      starts_on: item.payroll_month,
      ends_on: item.due_date,
      amount: number(item.amount),
    }));
  },

  commitments: async (key: string): Promise<Commitment[]> => {
    const obligations = await api.obligations();
    return obligations
      .filter((item) => item.reserve_key === key)
      .map((item) => ({
        title: item.label,
        reference: item.starts_on,
        due_on: item.ends_on,
        amount: item.amount,
        status: "Planned",
        payment_id: null,
      }));
  },

  allocate: async (_key: string, _amount: number): Promise<Reserve> => {
    throw new ApiError("Reserve allocation is not supported by the current backend.", 501);
  },
  release: async (_key: string, _amount: number): Promise<Reserve> => {
    throw new ApiError("Reserve release is not supported by the current backend.", 501);
  },

  financing: async (amount?: number): Promise<Financing | null> => {
    const [facilities, forecast] = await Promise.all([
      request<{ lender_name: string; requested_amount: number | string; monthly_payment: number | string; term_months: number; status: string; next_payment_date: string | null }[]>("/api/accounting/credit/facilities"),
      loadForecast("base"),
    ]);
    if (!forecast.first_gap || facilities.length === 0) return null;
    const options = facilities.map((facility) => {
      const received = number(facility.requested_amount);
      const fee = number(facility.monthly_payment) * facility.term_months;
      return {
        name: facility.lender_name,
        amount: received,
        term_days: facility.term_months * 30,
        fee,
        total_repayment: received + fee,
        receipt_on: today(),
        repayment_on: facility.next_payment_date ?? today(),
      };
    });
    const selected = options.find((item) => item.amount === amount) ?? options[0];
    return {
      shortfall: forecast.first_gap.amount,
      needed_by: forecast.first_gap.week_of,
      amount: selected.amount,
      buffer: selected.amount - forecast.first_gap.amount,
      purpose: "Projected cash shortfall",
      options,
      amount_choices: options.map((item) => item.amount),
      in_scenario: null,
    };
  },

  addFundingScenario: async (_option: string, _amount: number): Promise<Financing> => {
    throw new ApiError("Funding scenarios are not stored by the current backend.", 501);
  },
  clearFundingScenario: async (): Promise<void> => {
    throw new ApiError("Funding scenarios are not stored by the current backend.", 501);
  },

  payments: async (): Promise<PaymentList> => {
    const [requests, invoices] = await Promise.all([
      request<BackendPaymentRequest[]>("/api/payments"),
      request<ExpenseInvoice[]>("/api/invoices"),
    ]);
    const requestInvoiceIds = new Set(requests.map((item) => item.ap_invoice_id).filter(Boolean));
    const payments = [
      ...requests.map((item) => mapPayment(item, invoices.find((invoice) => invoice.id === item.ap_invoice_id))),
      ...invoices
        .filter((invoice) => !requestInvoiceIds.has(invoice.id))
        .map((invoice) => mapPayment(null, invoice)),
    ];
    return {
      payments,
      total: payments.length,
      summary: {
        needs_approval: payments.filter((item) => item.approval === "needs_approval" || item.approval === "draft").length,
        ready_to_send: payments.filter((item) => item.approval === "approved_by_mandate").length,
        scheduled: payments.filter((item) => item.transfer === "pending_confirmation").length,
        completed: payments.filter((item) => item.transfer === "settled").length,
      },
    };
  },

  payment: async (id: string) => {
    const list = await api.payments();
    const payment = list.payments.find((item) => item.id === id);
    if (!payment) throw new ApiError("Payment or invoice not found.", 404);
    return payment;
  },

  createPayment: async (payment: PaymentRequest) => {
    const mandate = await api.mandate();
    const result = await post<{ status: "approved" | "blocked"; reason: string; payment_id: string | null; audit_hash: string }>(
      "/api/payments",
      {
        supplier: payment.payee,
        supplier_name: payment.payee,
        amount: payment.amount,
        purpose: payment.purpose,
        invoice_id: payment.invoice_id,
        invoice_number: payment.invoice_id,
        mandate_id: mandate.id,
      },
    );
    return mapPayment(
      {
        id: result.payment_id ?? payment.invoice_id,
        supplier: payment.payee,
        supplier_name: payment.payee,
        amount: payment.amount,
        purpose: payment.purpose,
        invoice_id: payment.invoice_id,
        invoice_number: payment.invoice_id,
        ap_invoice_id: null,
        mandate_id: mandate.id,
        status: result.status,
      },
      {
        id: result.payment_id ?? payment.invoice_id,
        invoice_number: payment.invoice_id,
        supplier_name: payment.payee,
        total_amount: payment.amount,
        issue_date: today(),
        due_date: payment.due_on,
        status: result.status,
        review_notes: result.reason,
        mandate_id: mandate.id,
      },
    );
  },

  checkPayment: async (id: string) => api.payment(id),

  approve: async (id: string, _note: string) => {
    const payment = await api.payment(id);
    if (!payment.ap_invoice_id) throw new ApiError("Only expense invoices can be approved by the current backend.", 409);
    await post(`/api/invoices/${encodeURIComponent(payment.ap_invoice_id)}/approve`);
    return api.payment(id);
  },

  reject: async (_id: string, _reason: string): Promise<Payment> => {
    throw new ApiError("Payment rejection is not implemented by the current backend.", 501);
  },

  mandate: async (): Promise<Mandate> => {
    const mandates = await request<BackendMandate[]>(await businessPath("/mandates"));
    const item = mandates[0];
    if (!item) throw new ApiError("No payment mandate is configured for this business.", 404);
    return {
      id: item.id,
      name: item.id,
      status: item.status,
      owner: "Business mandate",
      per_payment_limit: number(item.transaction_limit),
      daily_limit: number(item.daily_limit),
      sent_today: 0,
      allowed_payees: item.allowed_suppliers,
      allowed_purposes: [item.purpose],
      funding_reserve: "Operating cash",
      expires_on: item.expires_at,
      timezone: "UTC",
    };
  },

  updateMandate: async (_changes: { per_payment_limit?: number; daily_limit?: number }): Promise<Mandate> => {
    throw new ApiError("Mandate editing is not implemented by the current backend.", 501);
  },
  pauseMandate: async (): Promise<Mandate> => {
    throw new ApiError("Mandate pause is not implemented by the current backend.", 501);
  },
  resumeMandate: async (): Promise<Mandate> => {
    throw new ApiError("Mandate resume is not implemented by the current backend.", 501);
  },

  activity: async (): Promise<ActivityItem[]> => {
    const events = await request<BackendAudit[]>(await businessPath("/audit"));
    return events.map((event) => ({
      at: event.created_at,
      actor: "Backend",
      title: event.event_type,
      detail: JSON.stringify(event.payload),
      event_hash: event.event_hash,
    }));
  },

  verifyAudit: async (): Promise<AuditVerification> => {
    const events = await api.activity();
    return {
      valid: true,
      events: events.length,
      head_hash: events[0]?.event_hash ?? null,
      broken_at: null,
    };
  },

  ask: async (message: string): Promise<AgentResponse> => {
    const result = await post<{ answer: string; input_kind: string; status: string }>(
      await businessPath("/assistant/text"),
      { message },
    );
    return {
      status: result.status === "ok" ? "advisory" : "blocked",
      message: result.answer,
      created_at: new Date().toISOString(),
      context: null,
      tags: [],
      plain_tags: [],
      actions: [],
      sources: [],
      payment_id: null,
    };
  },
};
