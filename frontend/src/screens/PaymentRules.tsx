import { useEffect, useState } from "react";
import { StyleSheet, View } from "react-native";
import { CircleCheck, FileCheck, Lock, ShieldCheck } from "lucide-react-native";

import { api, Mandate, Payment } from "../api";
import { useApp } from "../AppContext";
import { PageHeader } from "../components/Shell";
import { LoadState } from "../components/States";
import { Button, Card, Divider, IconBadge, LinkButton, Pill, Row, Select, T } from "../components/ui";
import { dayMonth, myr } from "../format";
import { checkSummary, needsOwner } from "../status";
import { colors, themed } from "../theme";
import { useResource } from "../useResource";

const PER_PAYMENT_LIMITS = [1000, 2500, 3500, 5000];
const DAILY_LIMITS = [5000, 10000, 15000];

const limitOptions = (values: number[], current: number) =>
  [...new Set([...values, current])].sort((a, b) => a - b).map((value) => ({ value, label: myr(value) }));

export function PaymentRules() {
  const { refreshKey } = useApp();
  const { data, error, reload } = useResource(
    () => Promise.all([api.mandate(), api.payments()]),
    [refreshKey],
  );

  return (
    <View>
      <PageHeader title="Payment rules" subtitle="Define what Amanah can approve on your behalf." />
      {!data ? <LoadState error={error} onRetry={reload} /> : <RulesContent mandate={data[0]} payments={data[1].payments} />}
    </View>
  );
}

function RulesContent({ mandate, payments }: { mandate: Mandate; payments: Payment[] }) {
  const { refresh, notify, navigate, openPayment } = useApp();
  const [editing, setEditing] = useState(false);
  const [confirmPause, setConfirmPause] = useState(false);
  const [perPayment, setPerPayment] = useState(mandate.per_payment_limit);
  const [daily, setDaily] = useState(mandate.daily_limit);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setPerPayment(mandate.per_payment_limit);
    setDaily(mandate.daily_limit);
  }, [mandate]);

  const paused = mandate.status === "paused";
  const left = mandate.daily_limit - mandate.sent_today;

  /** Resolves to whether the action succeeded; failures are shown as a toast. */
  async function run(action: () => Promise<unknown>, message: string): Promise<boolean> {
    setBusy(true);
    try {
      await action();
      refresh();
      notify(message, "success");
      return true;
    } catch (reason) {
      notify((reason as Error).message, "info");
      return false;
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={{ gap: 20 }}>
      <Card>
        <Row gap={16}>
          <IconBadge icon={FileCheck} />
          <View style={{ flex: 1, gap: 4 }}>
            <Row gap={10}>
              <T v="panelHeading">{mandate.name}</T>
              <Pill label={paused ? "Paused" : "Active"} tone={paused ? "warning" : "jade"} />
            </Row>
            <T v="label" c="secondary">
              {paused ? "Paused mandate" : "Active mandate"} · Owner: {mandate.owner} · Expires{" "}
              {dayMonth(mandate.expires_on, true)}
            </T>
          </View>
          <Row gap={10}>
            {paused ? (
              <Button
                label="Resume mandate"
                variant="secondary"
                disabled={busy}
                onPress={() => run(api.resumeMandate, "Mandate resumed. Payments within rules are approved automatically.")}
              />
            ) : (
              <Button label="Pause mandate" variant="secondary" onPress={() => setConfirmPause(true)} />
            )}
            {!editing && <Button label="Edit rules" onPress={() => setEditing(true)} />}
          </Row>
        </Row>
        {confirmPause && (
          <View style={styles.confirm}>
            <T v="body" w="semibold">Pause new automatic approvals?</T>
            <T v="label" c="secondary" style={{ marginTop: 2 }}>
              Payments already approved stay approved. Confirmed bank settlements are not cancelled.
            </T>
            <Row gap={10} style={{ marginTop: 12 }}>
              <Button
                label="Pause mandate"
                disabled={busy}
                onPress={() => {
                  setConfirmPause(false);
                  run(api.pauseMandate, "Mandate paused. New payments will need your approval.");
                }}
              />
              <Button label="Cancel" variant="secondary" onPress={() => setConfirmPause(false)} />
            </Row>
          </View>
        )}
      </Card>

      <Row gap={20} align="flex-start" style={{ zIndex: 10 }}>
        <Card style={{ flex: 1, zIndex: 10 }}>
          <T v="panelHeading">Approval limits</T>
          <Row gap={16} style={{ marginTop: 18, zIndex: 10 }}>
            <View style={{ flex: 1, gap: 8 }}>
              <T v="caption" c="secondary">Per-payment limit</T>
              <Select
                value={perPayment}
                options={limitOptions(PER_PAYMENT_LIMITS, mandate.per_payment_limit)}
                onChange={setPerPayment}
                disabled={!editing}
              />
            </View>
            <View style={{ flex: 1, gap: 8 }}>
              <T v="caption" c="secondary">Daily sending limit</T>
              <Select
                value={daily}
                options={limitOptions(DAILY_LIMITS, mandate.daily_limit)}
                onChange={setDaily}
                disabled={!editing}
              />
            </View>
          </Row>
          <Row justify="space-between" style={{ marginTop: 18, marginBottom: 16 }}>
            <T v="body" c="secondary">Expiry</T>
            <T v="body" w="semibold">{dayMonth(mandate.expires_on, true)}</T>
          </Row>
          <Divider />
          {editing ? (
            <View style={{ marginTop: 16 }}>
              <Row gap={10}>
                <Button
                  label="Save changes"
                  disabled={busy}
                  onPress={async () => {
                    const saved = await run(
                      () => api.updateMandate({ per_payment_limit: perPayment, daily_limit: daily }),
                      "Rules saved. Unfinished payments were checked again.",
                    );
                    if (saved) setEditing(false);
                  }}
                />
                <Button
                  label="Cancel"
                  variant="secondary"
                  onPress={() => {
                    setPerPayment(mandate.per_payment_limit);
                    setDaily(mandate.daily_limit);
                    setEditing(false);
                  }}
                />
              </Row>
              <T v="caption" c="secondary" style={{ marginTop: 10 }}>
                Unfinished payments will be checked again. Unsent approvals that no longer fit come back to you.
              </T>
            </View>
          ) : (
            <>
              <Row justify="space-between" style={{ marginTop: 16 }}>
                <T v="body" w="semibold" num>
                  Today: {myr(mandate.sent_today)} sent of {myr(mandate.daily_limit)}
                </T>
                <Pill label={`${myr(left)} left`} />
              </Row>
              <T v="caption" c="secondary" style={{ marginTop: 14 }}>
                Calendar day · {mandate.timezone}
              </T>
            </>
          )}
        </Card>

        <Card style={{ flex: 1 }}>
          <T v="panelHeading">Allowed scope</T>
          <T v="caption" c="secondary" style={{ marginTop: 18 }}>Approved payees</T>
          <T v="body" style={{ marginTop: 6 }}>{mandate.allowed_payees.join(", ")}</T>
          <T v="caption" c="secondary" style={{ marginTop: 18 }}>Allowed purposes</T>
          <T v="body" style={{ marginTop: 6, marginBottom: 16 }}>{mandate.allowed_purposes.join(", ")}</T>
          <Divider />
          <Row gap={10} style={{ marginTop: 16 }}>
            <ShieldCheck size={16} color={colors.emerald} />
            <T v="label" w="medium">Funding: Allocated from the {mandate.funding_reserve} reserve</T>
          </Row>
        </Card>
      </Row>

      <Card padding={22}>
        <Row align="flex-start" gap={24}>
          <View style={{ flex: 1 }}>
            <T v="title">When a payment falls outside these rules</T>
            <Row gap={8} style={{ marginTop: 8 }}>
              <CircleCheck size={17} color={colors.emerald} />
              <T v="body" w="semibold" c="emerald">Request owner approval</T>
            </Row>
            <T v="caption" c="secondary" style={{ marginTop: 8 }}>
              An exception approves one payment. It does not change these rules.
            </T>
          </View>
          <View style={{ flex: 1 }}>
            <T v="caption" c="secondary">Sending permissions</T>
            <Row gap={8} style={{ marginTop: 8 }}>
              <Lock size={17} color={colors.ink} />
              <T v="body" w="semibold">Owner confirmation required before sending.</T>
            </Row>
            <T v="caption" c="secondary" style={{ marginTop: 8 }}>
              Approvals do not use the daily limit. Checks run again before sending.
            </T>
          </View>
        </Row>
      </Card>

      <Card padding={20}>
        <Row justify="space-between">
          <T v="panelHeading">Recent rule checks</T>
          <LinkButton label="View payments" arrow onPress={() => navigate("payments")} />
        </Row>
        <View style={{ marginTop: 12 }}>
          {payments.map((payment, index) => (
            <Row key={payment.id} style={[styles.checkRow, index < payments.length - 1 && styles.divider]}>
              <T v="body" w="medium" style={{ width: 234 }}>{payment.payee}</T>
              <T v="label" c="secondary" style={{ width: 134 }}>{payment.id}</T>
              <T v="body" c={needsOwner(payment) || payment.checks === "blocked" ? "warning" : "ink"} style={{ flex: 1 }}>
                {checkSummary(payment)}
              </T>
              <View style={{ width: 265 }}>
                <LinkButton
                  label={needsOwner(payment) ? "Review payment" : "View payment"}
                  onPress={() => openPayment(payment.id)}
                />
              </View>
            </Row>
          ))}
        </View>
      </Card>
    </View>
  );
}

const styles = themed(() =>
  StyleSheet.create({
    confirm: {
      marginTop: 18,
      padding: 16,
      borderRadius: 16,
      backgroundColor: colors.limestone,
    },
    checkRow: { paddingVertical: 12 },
    divider: { borderBottomWidth: 1, borderBottomColor: colors.edge },
  }),
);
