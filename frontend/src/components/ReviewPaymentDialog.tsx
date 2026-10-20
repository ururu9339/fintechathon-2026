import { useState } from "react";
import { StyleSheet, TextInput, View } from "react-native";
import { Check, Clock, Info, TriangleAlert, X } from "lucide-react-native";

import { api, Payment, RuleCheck } from "../api";
import { useApp } from "../AppContext";
import { dayMonth, myr } from "../format";
import { approvalStatus, checkSummary, needsOwner, transferStatus } from "../status";
import { colors, fonts, noFocusRing, radius, themed } from "../theme";
import { useResource } from "../useResource";
import { Dialog, DialogTitle } from "./Dialog";
import { LoadState } from "./States";
import { Button, Divider, LinkButton, Pill, Row, Select, T } from "./ui";

const REJECT_REASONS = [
  { value: "Invoice needs correction", label: "Invoice needs correction" },
  { value: "Duplicate invoice", label: "Duplicate invoice" },
  { value: "Payee details changed", label: "Payee details changed" },
  { value: "Not a business expense", label: "Not a business expense" },
];

export function ReviewPaymentDialog({ paymentId, onClose }: { paymentId: string; onClose: () => void }) {
  const { data: payment, error, reload } = useResource(() => api.payment(paymentId), [paymentId]);

  return (
    <Dialog label="Review payment" onClose={onClose}>
      {payment ? (
        <DialogBody payment={payment} onClose={onClose} onChecked={reload} />
      ) : (
        <LoadState error={error} onRetry={reload} />
      )}
    </Dialog>
  );
}

function DialogBody({ payment, onClose, onChecked }: { payment: Payment; onClose: () => void; onChecked: () => void }) {
  const { refresh, notify } = useApp();
  const [note, setNote] = useState("");
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState(REJECT_REASONS[0].value);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const approval = approvalStatus[payment.approval];
  const limitCheck = payment.rule_checks.find((check) => check.rule === "per_payment_limit");
  const waiting = needsOwner(payment);
  // Blocked payments can't be approved, but the owner can still reject them.
  const blocked = payment.checks === "blocked" && payment.approval === "draft";
  const unchecked = payment.checks === "not_run";

  async function act(action: () => Promise<Payment>, success: string) {
    setBusy(true);
    setFailure(null);
    try {
      await action();
      refresh();
      notify(success, "success");
      onClose();
    } catch (reasonError) {
      setFailure((reasonError as Error).message);
      setBusy(false);
    }
  }

  // Stays open so the owner sees the result, then can approve or reject from here.
  async function runCheck() {
    setBusy(true);
    setFailure(null);
    try {
      const checked = await api.checkPayment(payment.id);
      refresh();
      onChecked();
      notify(
        `${checked.id}: ${checkSummary(checked)}. No funds have been sent.`,
        checked.checks === "blocked" ? "info" : "success",
      );
    } catch (reasonError) {
      setFailure((reasonError as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <View>
      <DialogTitle title="Review payment" subtitle={`${payment.payee} · ${payment.id}`} onClose={onClose} />

      <Row justify="space-between" align="flex-end" style={{ marginTop: 18 }}>
        <View>
          <T style={styles.amount} num>
            {myr(payment.amount)}
          </T>
          <T v="caption" c="secondary">
            Due {dayMonth(payment.due_on, true)}
          </T>
        </View>
        <View style={{ marginBottom: 22 }}>
          <Pill label={approval.label} tone={approval.tone} />
        </View>
      </Row>

      <View style={styles.details}>
        <Detail label="Purpose" value={payment.purpose} />
        <Detail label="Recipient" value={payment.payee} />
        <Detail label="Reserved from" value={payment.reserve} />
        <Detail label="Bank details" value={payment.bank_account} />
      </View>

      <T v="title" style={{ marginTop: 22, marginBottom: 4 }}>
        Rule check
      </T>
      {payment.rule_checks.length === 0 ? (
        <T v="body" c="secondary" style={{ paddingVertical: 10 }}>
          Rules haven't been checked for this draft yet.
        </T>
      ) : (
        payment.rule_checks.map((check) => <CheckRow key={check.rule} check={check} />)
      )}

      {waiting && limitCheck?.outcome === "exceeded" && (
        <Row gap={10} style={styles.alert}>
          <Info size={17} color={colors.warning} />
          <T v="label" c="warning" style={{ flex: 1 }}>
            Owner approval is required because this payment exceeds the per-payment limit.
          </T>
        </Row>
      )}

      {failure && (
        <T v="label" c="danger" style={{ marginTop: 12 }}>
          {failure}
        </T>
      )}

      {waiting && !rejecting && (
        <>
          <T v="caption" c="secondary" style={{ marginTop: 22, marginBottom: 8 }}>
            Approval note (optional)
          </T>
          <View style={styles.field}>
            <TextInput
              value={note}
              onChangeText={setNote}
              placeholder="Add context for the activity log"
              placeholderTextColor={colors.secondary}
              style={styles.input}
            />
          </View>
          <Row justify="space-between" style={{ marginTop: 14 }}>
            <LinkButton label="Reject" tone="danger" onPress={() => setRejecting(true)} />
            <Row gap={10}>
              <Button label="Cancel" variant="secondary" onPress={onClose} />
              <Button
                label="Approve exception"
                disabled={busy}
                onPress={() =>
                  act(() => api.approve(payment.id, note), "Payment approved. No funds have been sent.")
                }
              />
            </Row>
          </Row>
          <T v="caption" c="secondary" align="right" style={{ marginTop: 14 }}>
            This approves this payment only. No funds will be sent.
          </T>
        </>
      )}

      {blocked && !rejecting && (
        <>
          <Divider style={{ marginTop: 18 }} />
          <Row justify="space-between" style={{ marginTop: 16 }}>
            <LinkButton label="Reject" tone="danger" onPress={() => setRejecting(true)} />
            <Button label="Close" variant="secondary" onPress={onClose} />
          </Row>
          <T v="caption" c="secondary" align="right" style={{ marginTop: 14 }}>
            This payment is outside your rules, so it can't be approved.
          </T>
        </>
      )}

      {(waiting || blocked) && rejecting && (
        <View style={{ zIndex: 5 }}>
          <T v="caption" c="secondary" style={{ marginTop: 22, marginBottom: 8 }}>
            Reason for rejection
          </T>
          <Select value={reason} options={REJECT_REASONS} onChange={setReason} />
          <Row justify="flex-end" gap={10} style={{ marginTop: 14, zIndex: -1 }}>
            <Button label="Back" variant="secondary" onPress={() => setRejecting(false)} />
            <Button
              label="Reject payment"
              disabled={busy}
              onPress={() => act(() => api.reject(payment.id, reason), `${payment.id} rejected. Rules unchanged.`)}
            />
          </Row>
          <T v="caption" c="secondary" align="right" style={{ marginTop: 14, zIndex: -1 }}>
            Rejecting stops this payment. Your rules stay the same.
          </T>
        </View>
      )}

      {unchecked && (
        <>
          <Divider style={{ marginTop: 18 }} />
          <Row justify="flex-end" gap={10} style={{ marginTop: 16 }}>
            <Button label="Close" variant="secondary" onPress={onClose} />
            <Button label="Run rule check" disabled={busy} onPress={runCheck} />
          </Row>
          <T v="caption" c="secondary" align="right" style={{ marginTop: 14 }}>
            Checks this draft against your payment rules. No funds will be sent.
          </T>
        </>
      )}

      {!waiting && !blocked && !unchecked && (
        <>
          <Divider style={{ marginTop: 18 }} />
          <Row justify="space-between" style={{ marginTop: 16 }}>
            <T v="caption" c="secondary">
              Transfer: {transferStatus[payment.transfer]}
              {payment.note ? ` · Note: ${payment.note}` : ""}
            </T>
            <Button label="Close" variant="secondary" onPress={onClose} />
          </Row>
        </>
      )}
    </View>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <View style={{ width: "50%", paddingVertical: 6 }}>
      <T v="small" c="secondary">
        {label}
      </T>
      <T v="body" w="medium">
        {value}
      </T>
    </View>
  );
}

function CheckRow({ check }: { check: RuleCheck }) {
  const look = {
    passed: { Icon: Check, tone: "ink" as const, color: colors.ink },
    deferred: { Icon: Clock, tone: "secondary" as const, color: colors.secondary },
    exceeded: { Icon: TriangleAlert, tone: "warning" as const, color: colors.warning },
    failed: { Icon: X, tone: "danger" as const, color: colors.danger },
  }[check.outcome];
  // Payee and purpose details only add noise when they pass.
  const detail = check.outcome === "passed" && (check.rule === "payee" || check.rule === "purpose") ? null : check.detail;
  return (
    <Row justify="space-between" align="flex-start" style={styles.checkRow}>
      <View style={{ flex: 1 }}>
        <T v="body" w="medium">
          {check.label}
        </T>
        {detail && (
          <T v="caption" c="secondary">
            {detail}
          </T>
        )}
      </View>
      <Row gap={6}>
        <look.Icon size={15} color={look.color} strokeWidth={2.2} />
        <T v="label" w="medium" c={look.tone}>
          {check.summary}
        </T>
      </Row>
    </Row>
  );
}

const styles = themed(() =>
  StyleSheet.create({
    amount: { fontFamily: fonts.semibold, fontSize: 38, lineHeight: 46, color: colors.ink },
    details: {
      flexDirection: "row",
      flexWrap: "wrap",
      marginTop: 16,
      paddingVertical: 10,
      paddingHorizontal: 16,
      borderRadius: 16,
      backgroundColor: colors.limestone,
    },
    checkRow: { paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.edge },
    alert: {
      marginTop: 16,
      paddingVertical: 14,
      paddingHorizontal: 16,
      borderRadius: 14,
      backgroundColor: colors.warningSurface,
    },
    field: {
      height: 44,
      justifyContent: "center",
      paddingHorizontal: 14,
      borderRadius: radius.field,
      borderWidth: 1,
      borderColor: colors.edge,
    },
    input: { fontFamily: fonts.regular, fontSize: 14, color: colors.ink, height: "100%", ...noFocusRing },
  }),
);
