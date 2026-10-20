import { useMemo, useState } from "react";
import { Pressable, StyleSheet, TextInput, View } from "react-native";
import { ChevronDown, ChevronUp, Lock, Search } from "lucide-react-native";

import { api, ActivityItem, AuditVerification, Payment, PaymentList } from "../api";
import { NOT_IN_BUILD, useApp } from "../AppContext";
import { AddPaymentDialog } from "../components/AddPaymentDialog";
import { PageHeader } from "../components/Shell";
import { LoadState } from "../components/States";
import { Button, Card, LinkButton, Pill, Row, Select, shared, T } from "../components/ui";
import { clock, dayMonth, myr } from "../format";
import { approvalStatus, checkStatus, needsOwner, transferStatus } from "../status";
import { colors, fonts, noFocusRing, radius, themed } from "../theme";
import { useResource } from "../useResource";

type Sort = "due_asc" | "due_desc" | "amount_desc";

const SORTS: { value: Sort; label: string }[] = [
  { value: "due_asc", label: "Due date · Earliest first" },
  { value: "due_desc", label: "Due date · Latest first" },
  { value: "amount_desc", label: "Amount · Largest first" },
];

export function Payments() {
  const { refreshKey, workspace, present } = useApp();
  const { data, error, reload } = useResource(
    () => Promise.all([api.payments(), api.activity(), api.verifyAudit()]),
    [refreshKey],
  );

  return (
    <View>
      <PageHeader
        title="Payments"
        subtitle="Review decisions, then track each transfer."
        right={
          <Button label="Add payment" onPress={() => present(<AddPaymentDialog onClose={() => present(null)} />)} />
        }
      />
      {!data ? (
        <LoadState error={error} onRetry={reload} />
      ) : (
        <View style={{ gap: 20 }}>
          <SummaryStrip summary={data[0].summary} />
          <AllPayments list={data[0]} updatedAt={workspace?.updated_at ?? ""} />
          <Activity items={data[1]} audit={data[2]} />
        </View>
      )}
    </View>
  );
}

function SummaryStrip({ summary }: { summary: PaymentList["summary"] }) {
  const segments = [
    { label: "Needs approval", count: summary.needs_approval, attention: summary.needs_approval > 0 },
    { label: "Ready to send", count: summary.ready_to_send },
    { label: "Scheduled", count: summary.scheduled },
    { label: "Completed", count: summary.completed, dashWhenEmpty: true },
  ];
  return (
    <Card padding={16}>
      <Row gap={12}>
        {segments.map((segment) => (
          <Row
            key={segment.label}
            justify="space-between"
            style={[styles.segment, segment.attention && { backgroundColor: colors.jade }]}
          >
            <T v="body" w={segment.attention ? "semibold" : "regular"} c={segment.attention ? "ink" : "secondary"}>
              {segment.label}
            </T>
            <T v="title" num>
              {segment.dashWhenEmpty && segment.count === 0 ? "—" : segment.count}
            </T>
          </Row>
        ))}
      </Row>
    </Card>
  );
}

function AllPayments({ list, updatedAt }: { list: PaymentList; updatedAt: string }) {
  const { openPayment, notify } = useApp();
  const [query, setQuery] = useState("");
  const [payee, setPayee] = useState("all");
  const [sort, setSort] = useState<Sort>("due_asc");

  const payees = useMemo(
    () => [{ value: "all", label: "All payees" }, ...[...new Set(list.payments.map((p) => p.payee))].map((name) => ({ value: name, label: name }))],
    [list],
  );

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const rows = list.payments.filter(
      (payment) =>
        (payee === "all" || payment.payee === payee) &&
        (!needle || payment.payee.toLowerCase().includes(needle) || payment.id.toLowerCase().includes(needle)),
    );
    return rows.sort((a, b) =>
      sort === "amount_desc"
        ? b.amount - a.amount
        : sort === "due_desc"
          ? b.due_on.localeCompare(a.due_on)
          : a.due_on.localeCompare(b.due_on),
    );
  }, [list, query, payee, sort]);

  const total = visible.reduce((sum, payment) => sum + (payment.approval === "rejected" ? 0 : payment.amount), 0);

  return (
    <Card style={{ zIndex: 10 }}>
      <Row justify="space-between">
        <T v="panelHeading">All payments</T>
        <T v="caption" c="secondary">Updated {updatedAt}</T>
      </Row>

      <Row gap={12} style={{ marginTop: 18, zIndex: 20 }}>
        <View style={[shared.field, { width: 344 }]}>
          <Search size={17} color={colors.secondary} />
          <TextInput
            value={query}
            onChangeText={setQuery}
            placeholder="Search payee or invoice"
            placeholderTextColor={colors.secondary}
            style={styles.input}
          />
        </View>
        <Select value={payee} options={payees} onChange={setPayee} style={{ width: 188 }} />
        <Select value={sort} options={SORTS} onChange={setSort} style={{ width: 246 }} />
        <T v="caption" c="secondary" align="right" style={{ flex: 1 }}>
          {visible.length} payment{visible.length === 1 ? "" : "s"} · {myr(total)}
        </T>
      </Row>

      <Row style={styles.head}>
        <T v="caption" c="secondary" style={styles.colPayee}>Payee</T>
        <T v="caption" c="secondary" style={styles.colPurpose}>Purpose</T>
        <T v="caption" c="secondary" style={styles.colDue}>Due</T>
        <T v="caption" c="secondary" align="right" style={styles.colAmount}>Amount</T>
        <T v="caption" c="secondary" style={styles.colChecks}>Checks</T>
        <T v="caption" c="secondary" style={styles.colApproval}>Approval</T>
        <T v="caption" c="secondary" style={styles.colTransfer}>Transfer</T>
        <T v="caption" c="secondary" style={styles.colAction}>Action</T>
      </Row>
      {visible.map((payment) => (
        <PaymentRow key={payment.id} payment={payment} onOpen={openPayment} />
      ))}
      {visible.length === 0 && (
        <T v="body" c="secondary" style={{ paddingVertical: 28 }}>
          No payments match these filters.
        </T>
      )}

      <Row justify="space-between" style={{ marginTop: 20 }}>
        <Row gap={10}>
          <Lock size={16} color={colors.secondary} />
          <T v="caption" c="secondary">
            Approval is not a transfer. Owner confirmation is required before sending.
          </T>
        </Row>
        <LinkButton label="Prepare transfer" arrow v="label" onPress={() => notify(NOT_IN_BUILD, "info")} />
      </Row>
    </Card>
  );
}

function PaymentRow({ payment, onOpen }: { payment: Payment; onOpen: (id: string) => void }) {
  const check = checkStatus[payment.checks];
  const approval = approvalStatus[payment.approval];
  return (
    <Row style={styles.row}>
      <View style={styles.colPayee}>
        <T v="body" w="semibold">{payment.payee}</T>
        <T v="caption" c="secondary">{payment.id}</T>
      </View>
      <T v="label" style={styles.colPurpose}>{payment.purpose}</T>
      <T v="label" style={styles.colDue}>{dayMonth(payment.due_on)}</T>
      <T v="body" w="semibold" num align="right" style={styles.colAmount}>
        {myr(payment.amount)}
      </T>
      <View style={styles.colChecks}>
        <Pill label={check.label} tone={check.tone} />
      </View>
      <T
        v="label"
        w={payment.approval === "draft" ? "regular" : "medium"}
        c={needsOwner(payment) ? "warning" : payment.approval === "draft" ? "secondary" : "emerald"}
        style={styles.colApproval}
      >
        {approval.label}
      </T>
      <T v="label" c="secondary" style={styles.colTransfer}>{transferStatus[payment.transfer]}</T>
      <View style={styles.colAction}>
        <LinkButton label={needsOwner(payment) ? "Review" : "View"} onPress={() => onOpen(payment.id)} />
      </View>
    </Row>
  );
}

function Activity({ items, audit }: { items: ActivityItem[]; audit: AuditVerification }) {
  const [open, setOpen] = useState(true);
  const [showHashes, setShowHashes] = useState(false);
  return (
    <Card padding={20}>
      <Row justify="space-between">
        <Pressable onPress={() => setOpen(!open)} style={{ flex: 1 }}>
          <Row gap={12}>
            <T v="panelHeading">Activity</T>
            <Pill
              label={
                audit.valid
                  ? `Audit chain verified · ${audit.events} events`
                  : `Audit chain broken at entry ${(audit.broken_at ?? 0) + 1}`
              }
              tone={audit.valid ? "jade" : "warning"}
            />
          </Row>
        </Pressable>
        <Row gap={18}>
          {open && (
            <LinkButton label={showHashes ? "Hide hashes" : "Show hashes"} v="label" onPress={() => setShowHashes(!showHashes)} />
          )}
          <Pressable onPress={() => setOpen(!open)} accessibilityLabel={open ? "Collapse activity" : "Expand activity"}>
            {open ? <ChevronUp size={18} color={colors.ink} /> : <ChevronDown size={18} color={colors.ink} />}
          </Pressable>
        </Row>
      </Row>
      {open && showHashes && audit.head_hash && (
        <T v="caption" c="secondary" style={{ marginTop: 10 }}>
          Latest hash <T v="caption" style={styles.hash}>{audit.head_hash.slice(0, 16)}</T>. Each entry's hash
          includes the one before it, so changing any entry breaks the chain.
        </T>
      )}
      {open && (
        <View style={{ marginTop: 14, gap: 12 }}>
          {items.map((item, index) => (
            <Row key={`${item.at}-${index}`} align="flex-start">
              <T v="label" c="secondary" num style={{ width: 66 }}>{clock(item.at)}</T>
              <T v="label" w="medium" style={{ width: 101 }}>{item.actor}</T>
              <T v="label" w="medium" style={{ width: 256 }}>{item.title}</T>
              <T v="label" c="secondary" style={{ flex: 1 }}>{item.detail}</T>
              {showHashes && (
                <T v="small" c="secondary" align="right" style={[styles.hash, { width: 112 }]}>
                  {item.event_hash.slice(0, 12)}
                </T>
              )}
            </Row>
          ))}
        </View>
      )}
    </Card>
  );
}

const styles = themed(() =>
  StyleSheet.create({
    segment: {
      flex: 1,
      height: 46,
      paddingHorizontal: 16,
      borderRadius: radius.field,
    },
    input: {
      flex: 1,
      height: "100%",
      fontFamily: fonts.regular,
      fontSize: 14,
      color: colors.ink,
      ...noFocusRing,
    },
    head: { marginTop: 22, paddingBottom: 16, borderBottomWidth: 1, borderBottomColor: colors.edge },
    row: { paddingVertical: 22, borderBottomWidth: 1, borderBottomColor: colors.edge },
    colPayee: { flex: 1, minWidth: 180 },
    colPurpose: { width: 156 },
    colDue: { width: 100 },
    colAmount: { width: 100 },
    colChecks: { width: 147, paddingLeft: 32 },
    colApproval: { width: 182 },
    colTransfer: { width: 106 },
    colAction: { width: 62 },
    hash: { fontFamily: "monospace", color: colors.secondary },
  }),
);
