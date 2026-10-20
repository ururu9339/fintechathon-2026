import { StyleSheet, View } from "react-native";
import Svg, { Defs, LinearGradient, Path, Rect, Stop } from "react-native-svg";
import { CircleHelp, LucideIcon, Package, Receipt, ShieldCheck, TriangleAlert, Users, Wallet } from "lucide-react-native";

import { api, Payment, Reserve } from "../api";
import { useApp } from "../AppContext";
import { ForecastChart } from "../components/ForecastChart";
import { PageHeader } from "../components/Shell";
import { LoadState } from "../components/States";
import { Button, Card, Divider, LinkButton, Pill, Row, T } from "../components/ui";
import { dayMonth, myr } from "../format";
import { approvalStatus, checkStatus, needsOwner, transferStatus } from "../status";
import { colors, isDark, radius, themed } from "../theme";
import { useResource } from "../useResource";

export const RESERVE_ICONS: Record<string, LucideIcon> = {
  payroll_epf: Users,
  sst_taxes: Receipt,
  suppliers: Package,
};

export function Overview() {
  const { workspace, refreshKey, navigate } = useApp();
  const { data, error, reload } = useResource(
    () => Promise.all([api.balances(), api.forecast(), api.payments(), api.reserves()]),
    [refreshKey],
  );

  return (
    <View>
      <PageHeader
        title="Business overview"
        subtitle="Your cash position and upcoming decisions, at a glance."
        right={workspace && <T v="caption" c="secondary">Updated {workspace.updated_at}</T>}
      />
      {!data ? (
        <LoadState error={error} onRetry={reload} />
      ) : (
        <OverviewContent data={data} onNavigate={navigate} />
      )}
    </View>
  );
}

function OverviewContent({
  data: [balances, forecast, payments, reserves],
  onNavigate,
}: {
  data: [
    Awaited<ReturnType<typeof api.balances>>,
    Awaited<ReturnType<typeof api.forecast>>,
    Awaited<ReturnType<typeof api.payments>>,
    Reserve[],
  ];
  onNavigate: ReturnType<typeof useApp>["navigate"];
}) {
  const { openPayment } = useApp();
  const gap = forecast.first_gap;
  const upcoming = payments.payments.filter(
    (payment) => payment.checks !== "not_run" && payment.approval !== "rejected",
  );

  return (
    <View style={{ gap: 20 }}>
      <Row gap={20} align="stretch">
        <AvailableCard amount={balances.available} />
        <MetricCard label="Cash balance" value={myr(balances.cash)} note={`As of ${dayMonth(balances.as_of, true)}`} />
        <MetricCard label="Protected reserves" value={myr(balances.reserved)} note="Reserved in your cash balance" />
      </Row>

      <Card>
        <Row justify="space-between">
          <T v="panelHeading">13-week cash flow forecast</T>
          <Row gap={8}>
            <Pill label="13 weeks" />
            <Pill label="Base case" />
          </Row>
        </Row>
        <Row justify="space-between" style={{ marginTop: 16, marginBottom: 12 }}>
          <T v="caption" c="secondary">
            Projected cash balance (MYR)
          </T>
          <T v="caption" c="secondary">
            Weekly closing balance · Oct 2026 – Jan 2027
          </T>
        </Row>
        <ForecastChart points={forecast.points} highlight={gap?.week_of} />
        {gap && (
          <Row gap={14} style={styles.gapAlert}>
            <TriangleAlert size={20} color={colors.warning} />
            <View style={{ flex: 1 }}>
              <T v="body" w="semibold" c="warning">
                {myr(gap.amount)} cash gap · {dayMonth(gap.week_of)}
              </T>
              <T v="caption">{gap.reason}</T>
            </View>
            <Button label="Review cash plan" onPress={() => onNavigate("cashflow")} />
          </Row>
        )}
      </Card>

      <Row gap={20} align="flex-start">
        <Card padding={20} style={{ flex: 728 }}>
          <Row justify="space-between">
            <T v="panelHeading">Upcoming payments</T>
            <LinkButton label="View all payments" onPress={() => onNavigate("payments")} />
          </Row>
          <Row style={[styles.tableHead, { marginTop: 18 }]}>
            <T v="small" c="secondary" style={styles.colPayee}>Payee / Purpose</T>
            <T v="small" c="secondary" style={styles.colDue}>Due</T>
            <T v="small" c="secondary" style={styles.colAmount} align="right">Amount</T>
            <T v="small" c="secondary" style={styles.colApproval}>Approval</T>
            <T v="small" c="secondary" style={styles.colTransfer}>Transfer</T>
            <T v="small" c="secondary" style={styles.colAction}>Action</T>
          </Row>
          {upcoming.map((payment, index) => (
            <UpcomingRow key={payment.id} payment={payment} last={index === upcoming.length - 1} onOpen={openPayment} />
          ))}
        </Card>

        <Card padding={20} style={{ flex: 404 }}>
          <Row justify="space-between">
            <T v="panelHeading">Protected reserves</T>
            <ShieldCheck size={20} color={colors.emerald} />
          </Row>
          <View style={{ gap: 12, marginTop: 18, marginBottom: 16 }}>
            {reserves.map((reserve) => {
              const Icon = RESERVE_ICONS[reserve.key] ?? ShieldCheck;
              return (
                <Row key={reserve.key} gap={10}>
                  <Icon size={17} color={colors.ink} strokeWidth={1.8} />
                  <T v="body" c="secondary" style={{ flex: 1 }}>
                    {reserve.name}
                  </T>
                  <T v="body" w="semibold" num>
                    {myr(reserve.allocated)}
                  </T>
                </Row>
              );
            })}
          </View>
          <Divider />
          <View style={{ marginTop: 18 }}>
            <LinkButton label="Manage reserves" arrow onPress={() => onNavigate("reserves")} />
          </View>
        </Card>
      </Row>
    </View>
  );
}

function AvailableCard({ amount }: { amount: number }) {
  return (
    <View style={styles.available}>
      <Svg style={StyleSheet.absoluteFill} viewBox="0 0 456 152" preserveAspectRatio="none">
        <Defs>
          <LinearGradient id="hero" x1="0" y1="0" x2="1" y2="0">
            <Stop offset="0" stopColor={colors.heroStart} />
            <Stop offset="0.6" stopColor={colors.heroMid} />
            <Stop offset="1" stopColor={colors.heroEnd} />
          </LinearGradient>
          <LinearGradient id="sheen" x1="0" y1="0" x2="1" y2="1">
            <Stop offset="0" stopColor={colors.emerald} stopOpacity="0" />
            <Stop offset="1" stopColor={colors.emeraldLight} stopOpacity="1" />
          </LinearGradient>
          <LinearGradient id="highlight" x1="174" y1="0" x2="456" y2="0" gradientUnits="userSpaceOnUse">
            <Stop offset="0" stopColor={colors.emerald} stopOpacity="0.015" />
            <Stop offset="0.62" stopColor={colors.emerald} stopOpacity="0.05" />
            <Stop offset="1" stopColor={colors.emerald} stopOpacity="0.12" />
          </LinearGradient>
        </Defs>
        <Rect width="456" height="152" fill="url(#hero)" />
        {isDark() ? (
          // "Quiet tonal curved highlight" from the Figma dark theme.
          <Path
            d="M174.2 151.6C289.2 149.6 359.2 101.6 455.2 49.6V151.6Z"
            fill="url(#highlight)"
            stroke={colors.heroLabel}
            strokeOpacity={0.16}
            strokeWidth={0.5}
          />
        ) : (
          <Path d="M180 152 C 300 120, 380 70, 456 40 L456 152 Z" fill="url(#sheen)" />
        )}
      </Svg>
      <Row justify="space-between" align="flex-start">
        <T v="body" w="medium" c="heroLabel">
          Available to spend
        </T>
        <Wallet size={17} color={colors.heroLabel} />
      </Row>
      <T v="mainAmount" c="heroText" num style={{ marginTop: 6 }}>
        {myr(amount)}
      </T>
      <T v="caption" c="heroLabel" style={{ marginTop: 6, opacity: isDark() ? 1 : 0.85 }}>
        After reserved amounts
      </T>
    </View>
  );
}

function MetricCard({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <Card style={{ flex: 328 }}>
      <Row justify="space-between">
        <T v="body" c="secondary">
          {label}
        </T>
        <CircleHelp size={17} color={colors.secondary} />
      </Row>
      <T v="metric" num style={{ marginTop: 8 }}>
        {value}
      </T>
      <T v="caption" c="secondary" style={{ marginTop: 6 }}>
        {note}
      </T>
    </Card>
  );
}

function UpcomingRow({ payment, last, onOpen }: { payment: Payment; last: boolean; onOpen: (id: string) => void }) {
  const approval = approvalStatus[payment.approval];
  return (
    <Row style={[styles.tableRow, !last && styles.rowDivider]}>
      <View style={styles.colPayee}>
        <T v="body" w="medium">{payment.payee}</T>
        <T v="caption" c="secondary">{payment.purpose}</T>
      </View>
      <T v="label" style={styles.colDue}>{dayMonth(payment.due_on)}</T>
      <T v="body" w="semibold" num align="right" style={styles.colAmount}>
        {myr(payment.amount)}
      </T>
      <View style={styles.colApproval}>
        <T v="label" w="medium" c={needsOwner(payment) ? "warning" : "emerald"}>
          {approval.label}
        </T>
        <T v="small" c="secondary">{checkStatus[payment.checks].label}</T>
      </View>
      <T v="label" c="secondary" style={styles.colTransfer}>{transferStatus[payment.transfer]}</T>
      <View style={styles.colAction}>
        <LinkButton label={needsOwner(payment) ? "Review" : "View"} onPress={() => onOpen(payment.id)} />
      </View>
    </Row>
  );
}

const styles = themed(() =>
  StyleSheet.create({
    available: {
      flex: 456,
      minHeight: 152,
      backgroundColor: colors.heroStart,
      borderWidth: 0.8,
      borderColor: colors.heroEdge,
      borderRadius: radius.card,
      overflow: "hidden",
      padding: 24,
    },
    gapAlert: {
      marginTop: 16,
      paddingVertical: 12,
      paddingHorizontal: 16,
      borderRadius: 16,
      backgroundColor: colors.warningSurface,
    },
    tableHead: { paddingBottom: 14 },
    tableRow: { paddingVertical: 14 },
    rowDivider: { borderBottomWidth: 1, borderBottomColor: colors.edge },
    colPayee: { flex: 1.8 },
    colDue: { flex: 0.7 },
    colAmount: { flex: 0.9, paddingRight: 12 },
    colApproval: { flex: 1.4 },
    colTransfer: { flex: 0.7 },
    colAction: { flex: 0.6 },
  }),
);
