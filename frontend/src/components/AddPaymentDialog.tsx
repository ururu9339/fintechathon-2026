import { ReactNode, useState } from "react";
import { StyleSheet, TextInput, View } from "react-native";

import { api, Mandate } from "../api";
import { useApp } from "../AppContext";
import { checkSummary } from "../status";
import { colors, fonts, noFocusRing, themed } from "../theme";
import { useResource } from "../useResource";
import { Dialog, DialogTitle } from "./Dialog";
import { LoadState } from "./States";
import { Button, Divider, Row, Select, shared, T } from "./ui";

// Picking "Other" lets the owner enter a payee or purpose outside the mandate; the rule check blocks it.
const OTHER = "__other";

/** Creates a supplier payment and runs the rule check straight away. Nothing is sent. */
export function AddPaymentDialog({ onClose }: { onClose: () => void }) {
  const { data: mandate, error, reload } = useResource(() => api.mandate(), []);
  return (
    <Dialog label="Add payment" onClose={onClose} width={600}>
      <DialogTitle
        title="Add payment"
        subtitle="Amanah checks it against your payment rules. Nothing is sent."
        onClose={onClose}
      />
      {mandate ? (
        <PaymentForm mandate={mandate} onClose={onClose} />
      ) : (
        <View style={{ marginTop: 20 }}>
          <LoadState error={error} onRetry={reload} />
        </View>
      )}
    </Dialog>
  );
}

function PaymentForm({ mandate, onClose }: { mandate: Mandate; onClose: () => void }) {
  const { workspace, refresh, notify, openPayment } = useApp();
  const [invoiceId, setInvoiceId] = useState("");
  const [amount, setAmount] = useState("");
  const [payee, setPayee] = useState(mandate.allowed_payees[0] ?? OTHER);
  const [otherPayee, setOtherPayee] = useState("");
  const [purpose, setPurpose] = useState(mandate.allowed_purposes[0] ?? OTHER);
  const [otherPurpose, setOtherPurpose] = useState("");
  const [dueOn, setDueOn] = useState(workspace ? addDays(workspace.demo_date, 7) : "");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const payeeName = (payee === OTHER ? otherPayee : payee).trim();
  const purposeName = (purpose === OTHER ? otherPurpose : purpose).trim();
  const value = Number(amount.replace(/,/g, ""));

  function problem(): string | null {
    if (!invoiceId.trim()) return "Enter the invoice number.";
    if (!payeeName) return "Enter the payee.";
    if (!purposeName) return "Enter the purpose.";
    if (!amount.trim() || !Number.isFinite(value) || value <= 0) return "Enter an amount above zero.";
    if (!isDate(dueOn)) return "Enter the due date as YYYY-MM-DD.";
    return null;
  }

  async function submit() {
    const invalid = problem();
    if (invalid) return setFailure(invalid);
    setBusy(true);
    setFailure(null);
    try {
      const created = await api.createPayment({
        invoice_id: invoiceId.trim(),
        payee: payeeName,
        purpose: purposeName,
        amount: value,
        due_on: dueOn,
      });
      refresh();
      onClose();
      openPayment(created.id);
      notify(
        `${created.id} added: ${checkSummary(created)}. No funds have been sent.`,
        created.checks === "blocked" ? "info" : "success",
      );
    } catch (error) {
      setFailure((error as Error).message);
      setBusy(false);
    }
  }

  const choices = (values: string[], other: string) => [
    ...values.map((item) => ({ value: item, label: item })),
    { value: OTHER, label: other },
  ];

  return (
    <View>
      <Row gap={12} align="flex-start" style={{ marginTop: 22 }}>
        <Field label="Invoice number">
          <Input value={invoiceId} onChange={setInvoiceId} placeholder="e.g. AC-1025" />
        </Field>
        <Field label="Amount (MYR)">
          <Input value={amount} onChange={setAmount} placeholder="e.g. 1,200" numeric />
        </Field>
      </Row>

      <Row gap={12} align="flex-start" style={{ marginTop: 16, zIndex: 10 }}>
        <Field label="Payee">
          <Select value={payee} options={choices(mandate.allowed_payees, "Other payee…")} onChange={setPayee} />
          {payee === OTHER && <Input value={otherPayee} onChange={setOtherPayee} placeholder="Payee name" />}
        </Field>
        <Field label="Purpose">
          <Select value={purpose} options={choices(mandate.allowed_purposes, "Other purpose…")} onChange={setPurpose} />
          {purpose === OTHER && <Input value={otherPurpose} onChange={setOtherPurpose} placeholder="Purpose" />}
        </Field>
      </Row>

      <Row gap={12} align="flex-start" style={{ marginTop: 16 }}>
        <Field label="Due date">
          <Input value={dueOn} onChange={setDueOn} placeholder="YYYY-MM-DD" />
        </Field>
        <Field label="Reserved from">
          <View style={[shared.field, { backgroundColor: colors.limestone }]}>
            <T v="body">{mandate.funding_reserve}</T>
          </View>
        </Field>
      </Row>

      <T v="caption" c="secondary" style={{ marginTop: 14 }}>
        Approved payees and purposes come from your payment rules. Anything else is blocked by the rule check.
      </T>

      {failure && (
        <T v="label" c="danger" style={{ marginTop: 12 }}>
          {failure}
        </T>
      )}

      <Divider style={{ marginTop: 20 }} />
      <Row justify="flex-end" gap={10} style={{ marginTop: 16 }}>
        <Button label="Cancel" variant="secondary" onPress={onClose} />
        <Button label="Add and check" disabled={busy} onPress={submit} />
      </Row>
    </View>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <View style={{ flex: 1, gap: 8 }}>
      <T v="caption" c="secondary">{label}</T>
      {children}
    </View>
  );
}

function Input({
  value,
  onChange,
  placeholder,
  numeric,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  numeric?: boolean;
}) {
  return (
    <View style={shared.field}>
      <TextInput
        value={value}
        onChangeText={onChange}
        placeholder={placeholder}
        placeholderTextColor={colors.secondary}
        keyboardType={numeric ? "decimal-pad" : "default"}
        style={styles.input}
      />
    </View>
  );
}

/** "2026-10-16" plus a number of days, without going through the browser's time zone. */
function addDays(iso: string, days: number): string {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day + days)).toISOString().slice(0, 10);
}

/** A real calendar date in YYYY-MM-DD form (rejects e.g. 2026-02-30, which would roll over). */
function isDate(iso: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(iso) && addDays(iso, 0) === iso;
}

const styles = themed(() =>
  StyleSheet.create({
    input: { flex: 1, height: "100%", fontFamily: fonts.regular, fontSize: 14, color: colors.ink, ...noFocusRing },
  }),
);
