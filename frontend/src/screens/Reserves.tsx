import { useState } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import { Ellipsis, ShieldCheck } from "lucide-react-native";

import { api, Balances, Commitment, Obligation, Reserve } from "../api";
import { useApp } from "../AppContext";
import { PageHeader } from "../components/Shell";
import { LoadState } from "../components/States";
import { Card, Divider, LinkButton, Pill, Row, T } from "../components/ui";
import { dayMonth, myr } from "../format";
import { approvalStatus } from "../status";
import { colors, themed } from "../theme";
import { useResource } from "../useResource";
import { RESERVE_ICONS } from "./Overview";

// One colour per reserve, shared by the summary bar and each card's progress bar.
const RESERVE_COLORS = themed(
  (): Record<string, string> => ({
    payroll_epf: colors.emerald,
    sst_taxes: colors.reserveSecondary,
    suppliers: colors.reserveTertiary,
  }),
);

export function Reserves() {
  const { refreshKey, workspace, notify } = useApp();
  const { data, error, reload } = useResource(
    () => Promise.all([api.balances(), api.reserves(), api.obligations()]),
    [refreshKey],
  );
  const [selected, setSelected] = useState("suppliers");

  const openDialog = () =>
    notify("Reserve allocation and release are not supported by the current backend.", "info");

  return (
    <View>
      <PageHeader
        title="Protected reserves"
        subtitle="Set money aside for the commitments that matter."
        right={<T v="caption" c="secondary">Read-only backend data</T>}
      />
      {!data ? (
        <LoadState error={error} onRetry={reload} />
      ) : (
        <View style={{ gap: 20 }}>
          <Summary balances={data[0]} reserves={data[1]} updatedAt={workspace?.updated_at ?? ""} />
          <Row gap={20} align="stretch" style={{ zIndex: 10 }}>
            {data[1].map((reserve) => (
              <ReserveCard
                key={reserve.key}
                reserve={reserve}
                selected={reserve.key === selected}
                onSelect={() => setSelected(reserve.key)}
                onAction={openDialog}
              />
            ))}
          </Row>
          <Row gap={20} align="flex-start">
            <Commitments reserve={data[1].find((item) => item.key === selected) ?? data[1][0]} />
            <Obligations obligations={data[2]} reserves={data[1]} />
          </Row>
        </View>
      )}
    </View>
  );
}

function Summary({ balances, reserves, updatedAt }: { balances: Balances; reserves: Reserve[]; updatedAt: string }) {
  const share = balances.cash ? (balances.reserved / balances.cash) * 100 : 0;
  return (
    <Card>
      <Row justify="space-between" align="flex-start">
        <Row gap={20} align="center">
          <T v="metric" num>{myr(balances.reserved)}</T>
          <View>
            <T v="body" w="semibold">reserved · {share.toFixed(1)}% of your cash balance</T>
            <T v="caption" c="secondary">{myr(balances.available)} available · Reserved in your cash balance</T>
          </View>
        </Row>
        <T v="caption" c="secondary">Updated {updatedAt}</T>
      </Row>
      <View style={styles.bar}>
        {reserves.map((reserve) => (
          <View
            key={reserve.key}
            style={{ flex: reserve.allocated, backgroundColor: RESERVE_COLORS[reserve.key] ?? colors.sage }}
          />
        ))}
        <View style={{ flex: Math.max(0, balances.available), backgroundColor: colors.muted }} />
      </View>
      <Row justify="space-between" style={{ marginTop: 14 }}>
        <T v="caption" c="secondary">
          Reserved amounts are included in your cash balance. These are not separate bank accounts.
        </T>
        <T v="caption" c="secondary">Total cash · {myr(balances.cash)}</T>
      </Row>
    </Card>
  );
}

function ReserveCard({
  reserve,
  selected,
  onSelect,
  onAction,
}: {
  reserve: Reserve;
  selected: boolean;
  onSelect: () => void;
  onAction: (mode: "add" | "release") => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const Icon = RESERVE_ICONS[reserve.key] ?? ShieldCheck;
  const funded = reserve.allocated >= reserve.target;
  const progress = reserve.target ? Math.min(1, reserve.allocated / reserve.target) : 1;

  return (
    <Pressable
      onPress={onSelect}
      accessibilityRole="button"
      accessibilityState={{ selected }}
      style={[styles.reserveCard, selected && styles.reserveCardSelected, { zIndex: menuOpen ? 20 : 1 }]}
    >
      <Row justify="space-between">
        <Row gap={10}>
          <Icon size={19} color={colors.ink} strokeWidth={1.8} />
          <T v="title">{reserve.name}</T>
        </Row>
        <Pressable onPress={() => setMenuOpen(!menuOpen)} hitSlop={8} accessibilityLabel={`${reserve.name} actions`}>
          <Ellipsis size={20} color={colors.ink} />
        </Pressable>
      </Row>
      {menuOpen && (
        <View style={styles.menu}>
          {(["add", "release"] as const).map((mode) => (
            <Pressable
              key={mode}
              onPress={() => {
                setMenuOpen(false);
                onAction(mode);
              }}
              style={(state) => [styles.menuItem, (state as { hovered?: boolean }).hovered && { backgroundColor: colors.limestone }]}
            >
              <T v="body">{mode === "add" ? "Add money" : "Release money"}</T>
            </Pressable>
          ))}
        </View>
      )}
      <Row align="flex-end" gap={6} style={{ marginTop: 18 }}>
        <T v="amount" num>{myr(reserve.allocated)}</T>
        <T v="label" c="secondary" style={{ marginBottom: 5 }}>/ {reserve.target.toLocaleString("en-US")}</T>
      </Row>
      <View style={styles.progress}>
        <View
          style={{ width: `${progress * 100}%`, height: "100%", borderRadius: 3, backgroundColor: RESERVE_COLORS[reserve.key] ?? colors.sage }}
        />
      </View>
      <Row justify="space-between" style={{ marginTop: 16 }}>
        <Pill
          label={funded ? "Fully funded" : `${myr(reserve.target - reserve.allocated)} short`}
          tone={funded ? "jade" : "warning"}
        />
        <T v="caption" c="secondary">Next due {dayMonth(reserve.next_due)}</T>
      </Row>
    </Pressable>
  );
}

function Commitments({ reserve }: { reserve: Reserve }) {
  const { refreshKey, navigate, openPayment } = useApp();
  const { data, error, reload } = useResource(() => api.commitments(reserve.key), [reserve.key, refreshKey]);
  const total = (data ?? []).reduce((sum, item) => sum + item.amount, 0);
  const isPayments = (data ?? []).some((item) => item.payment_id);

  return (
    <Card style={{ flex: 738 }}>
      <Row justify="space-between">
        <T v="panelHeading">Commitments in {reserve.name}</T>
        <Pill label="Selected reserve" />
      </Row>
      {!data ? (
        <View style={{ marginTop: 16 }}>
          <LoadState error={error} onRetry={reload} />
        </View>
      ) : (
        <>
          <Row style={[styles.commitRow, { marginTop: 14, borderBottomWidth: 0, paddingBottom: 4 }]}>
            <T v="caption" c="secondary" style={{ flex: 1 }}>{isPayments ? "Payee / Invoice" : "Commitment"}</T>
            <T v="caption" c="secondary" style={styles.commitDue}>Due</T>
            <T v="caption" c="secondary" align="right" style={styles.commitAmount}>Amount</T>
            <T v="caption" c="secondary" style={styles.commitStatus}>{isPayments ? "Approval" : "Status"}</T>
          </Row>
          {data.map((item) => (
            <CommitmentRow key={item.reference} item={item} onOpen={openPayment} />
          ))}
          <Row justify="space-between" style={{ marginTop: 14 }}>
            <T v="body" w="semibold" num>Total · {myr(total)}</T>
            {isPayments && <LinkButton label="View related payments" arrow onPress={() => navigate("payments")} />}
          </Row>
        </>
      )}
    </Card>
  );
}

function CommitmentRow({ item, onOpen }: { item: Commitment; onOpen: (id: string) => void }) {
  const approval = item.payment_id ? approvalStatus[item.status as keyof typeof approvalStatus] : null;
  const row = (
    <Row style={styles.commitRow}>
      <T v="body" style={{ flex: 1 }}>{item.title} · {item.reference}</T>
      <T v="body" style={styles.commitDue}>{dayMonth(item.due_on)}</T>
      <T v="body" w="semibold" num align="right" style={styles.commitAmount}>{myr(item.amount)}</T>
      <T v="caption" c={approval?.tone === "warning" ? "warning" : "secondary"} style={styles.commitStatus}>
        {approval?.label ?? item.status}
      </T>
    </Row>
  );
  return item.payment_id ? <Pressable onPress={() => onOpen(item.payment_id!)}>{row}</Pressable> : row;
}

function Obligations({ obligations, reserves }: { obligations: Obligation[]; reserves: Reserve[] }) {
  const allFunded = reserves.every((reserve) => reserve.allocated >= reserve.target);
  const range = (o: Obligation) =>
    o.starts_on === o.ends_on ? dayMonth(o.starts_on) : `${dayMonth(o.starts_on).split(" ")[0]}–${dayMonth(o.ends_on)}`;
  return (
    <Card style={{ flex: 390 }}>
      <T v="panelHeading">Upcoming obligations</T>
      <View style={{ gap: 14, marginTop: 16 }}>
        {obligations.map((obligation) => (
          <View key={obligation.reserve_key}>
            <T v="caption" c="secondary">{range(obligation)}</T>
            <Row justify="space-between">
              <T v="body" c="secondary">{obligation.label}</T>
              <T v="body" w="semibold" num>{myr(obligation.amount)}</T>
            </Row>
          </View>
        ))}
      </View>
      <Divider style={{ marginVertical: 16 }} />
      <T v="caption" c={allFunded ? "secondary" : "warning"}>
        {allFunded
          ? "Current goals are fully funded. November payroll is a separate future obligation after the 30 Oct payout."
          : "Some reserves are below their goal. Add money before the next due date."}
      </T>
    </Card>
  );
}

const styles = themed(() =>
  StyleSheet.create({
    bar: { flexDirection: "row", height: 14, gap: 3, marginTop: 18, borderRadius: 4, overflow: "hidden" },
    reserveCard: {
      flex: 1,
      padding: 20,
      borderRadius: 28,
      borderWidth: 1,
      borderColor: colors.edge,
      backgroundColor: colors.porcelain,
    },
    reserveCardSelected: { borderColor: colors.sage },
    progress: { height: 6, marginTop: 14, borderRadius: 3, backgroundColor: colors.muted, overflow: "hidden" },
    menu: {
      position: "absolute",
      top: 48,
      right: 16,
      width: 170,
      padding: 6,
      borderRadius: 12,
      borderWidth: 1,
      borderColor: colors.edge,
      backgroundColor: colors.raised,
      shadowColor: colors.shadow,
      shadowOffset: { width: 0, height: 10 },
      shadowOpacity: 0.1,
      shadowRadius: 24,
      zIndex: 30,
    },
    menuItem: { paddingVertical: 9, paddingHorizontal: 10, borderRadius: 8 },
    commitRow: { paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: colors.edge, alignItems: "center", flexDirection: "row" },
    commitDue: { width: 110 },
    commitAmount: { width: 110 },
    commitStatus: { width: 150, paddingLeft: 32 },
  }),
);
