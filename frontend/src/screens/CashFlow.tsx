import { useState } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import { CalendarDays, Clock } from "lucide-react-native";

import { api, Forecast, Scenario, WeekDetail } from "../api";
import { NOT_IN_BUILD, useApp } from "../AppContext";
import { ForecastChart } from "../components/ForecastChart";
import { PageHeader } from "../components/Shell";
import { LoadState } from "../components/States";
import { Button, Card, Divider, LinkButton, Pill, Row, T } from "../components/ui";
import { amount, dayMonth, myr, weekRange } from "../format";
import { colors, radius, themed } from "../theme";
import { useResource } from "../useResource";

const SCENARIO_LABELS: Record<Scenario, string> = {
  base: "Base case",
  earlier_customer_payment: "Earlier customer payment",
  with_funding: "With funding",
};

export function CashFlow() {
  const { refreshKey, notify, workspace } = useApp();
  const { data, error, reload } = useResource(
    async () => {
      const [base, earlier, financing] = await Promise.all([
        api.forecast("base"),
        api.forecast("earlier_customer_payment"),
        api.financing(),
      ]);
      const funded = financing?.in_scenario ? await api.forecast("with_funding") : null;
      return { base, earlier, funded, fundingAmount: financing?.in_scenario?.amount ?? null };
    },
    [refreshKey],
  );

  return (
    <View>
      <PageHeader
        title="Cash flow"
        subtitle="See what changes your next 13 weeks."
        right={<Button label="Edit assumptions" variant="secondary" onPress={() => notify(NOT_IN_BUILD, "info")} />}
      />
      {!data ? (
        <LoadState error={error} onRetry={reload} />
      ) : (
        <CashFlowContent {...data} updatedAt={workspace?.updated_at ?? ""} />
      )}
    </View>
  );
}

function CashFlowContent({
  base,
  earlier,
  funded,
  fundingAmount,
  updatedAt,
}: {
  base: Forecast;
  earlier: Forecast;
  funded: Forecast | null;
  fundingAmount: number | null;
  updatedAt: string;
}) {
  const { params } = useApp();
  const scenarios: Record<Scenario, Forecast | null> = {
    base,
    earlier_customer_payment: earlier,
    with_funding: funded,
  };
  const initialScenario = params.scenario && scenarios[params.scenario] ? params.scenario : "base";
  const [scenario, setScenario] = useState<Scenario>(initialScenario);
  const [week, setWeek] = useState(params.week ?? base.first_gap?.week_of ?? base.lowest.week_of);
  const [tableOpen, setTableOpen] = useState(false);

  const label = (key: Scenario) =>
    key === "with_funding" && fundingAmount ? `With ${myr(fundingAmount)} funding` : SCENARIO_LABELS[key];
  // The base case is always the solid line; the dashed line is the scenario being compared.
  const comparisonKey: Scenario = scenario === "base" ? "earlier_customer_payment" : scenario;
  const comparison = scenarios[comparisonKey] ?? earlier;
  const tabs = (Object.keys(scenarios) as Scenario[]).filter((key) => scenarios[key]);

  return (
    <View style={{ gap: 20 }}>
      <Row align="flex-end" gap={40} style={{ paddingHorizontal: 4 }}>
        <Kpi label="Current cash" value={myr(base.points[0].closing_balance)} />
        <Kpi
          label="Lowest projected balance"
          value={myr(base.lowest.closing_balance)}
          warning={base.lowest.closing_balance < 0}
        />
        <Kpi label="First cash gap" value={base.first_gap ? dayMonth(base.first_gap.week_of, true) : "None"} />
        <T v="caption" c="secondary" align="right" style={{ flex: 1, marginBottom: 6 }}>
          Updated {updatedAt}
        </T>
      </Row>

      <Row gap={20} align="stretch">
        <Card style={{ flex: 780 }}>
          <Row justify="space-between">
            <T v="panelHeading">13-week cash flow forecast</T>
            <LinkButton label={tableOpen ? "Hide weekly table" : "View weekly table"} onPress={() => setTableOpen(!tableOpen)} />
          </Row>
          <Row gap={8} style={{ marginTop: 16 }}>
            {tabs.map((key) => (
              <Pressable
                key={key}
                onPress={() => setScenario(key)}
                accessibilityRole="tab"
                accessibilityState={{ selected: key === scenario }}
                style={[styles.tab, key === scenario && styles.tabActive]}
              >
                <T v="label" w={key === scenario ? "semibold" : "regular"} c={key === scenario ? "ink" : "secondary"}>
                  {label(key)}
                </T>
              </Pressable>
            ))}
          </Row>
          <T v="caption" c="secondary" style={{ marginTop: 16, marginBottom: 12 }}>
            Scenario only · Your base forecast is unchanged · Projected cash balance (MYR)
          </T>
          <ForecastChart points={base.points} comparison={comparison.points} highlight={week} band onSelect={setWeek} />
          <Row gap={24} style={{ marginTop: 16 }}>
            <Legend label="Base case" />
            <Legend label={label(comparisonKey)} dashed />
          </Row>
        </Card>

        <WeekPanel week={week} scenario={scenario} scenarioLabel={label(scenario)} />
      </Row>

      {tableOpen && (
        <WeeklyTable base={base} comparison={comparison} selected={week} onSelect={setWeek} />
      )}

      <WeekEvents week={week} scenario={scenario} />
    </View>
  );
}

function Kpi({ label, value, warning }: { label: string; value: string; warning?: boolean }) {
  return (
    <View style={{ gap: 2 }}>
      <T v="caption" c="secondary">{label}</T>
      <T v="amount" c={warning ? "warning" : "ink"} num style={{ fontSize: 24, lineHeight: 32 }}>
        {value}
      </T>
    </View>
  );
}

function Legend({ label, dashed }: { label: string; dashed?: boolean }) {
  return (
    <Row gap={8}>
      <View style={[styles.legendLine, dashed && styles.legendDashed]} />
      <T v="caption" c="secondary">{label}</T>
    </Row>
  );
}

function useWeek(week: string, scenario: Scenario) {
  const { refreshKey } = useApp();
  return useResource(() => api.week(week, scenario), [week, scenario, refreshKey]);
}

function WeekPanel({ week, scenario, scenarioLabel }: { week: string; scenario: Scenario; scenarioLabel: string }) {
  const { navigate, askAbout } = useApp();
  const { data, error, reload } = useWeek(week, scenario);

  return (
    <Card style={{ flex: 316 }}>
      {!data ? (
        <LoadState error={error} onRetry={reload} />
      ) : (
        <WeekSummary
          detail={data}
          scenarioLabel={scenarioLabel}
          onCompareFunding={() => navigate("financing")}
          onAsk={() => askAbout(`What happens in the week of ${dayMonth(week)}?`)}
        />
      )}
    </Card>
  );
}

function WeekSummary({
  detail,
  scenarioLabel,
  onCompareFunding,
  onAsk,
}: {
  detail: WeekDetail;
  scenarioLabel: string;
  onCompareFunding: () => void;
  onAsk: () => void;
}) {
  const point = detail.point;
  const negative = point.closing_balance < 0;
  return (
    <View style={{ flex: 1 }}>
      <Row justify="space-between">
        <T v="panelHeading">Week of {dayMonth(point.week_of)}</T>
        <Row gap={10}>
          <T v="caption" c="secondary">{scenarioLabel}</T>
          <CalendarDays size={17} color={colors.ink} />
        </Row>
      </Row>
      <View style={{ gap: 12, marginTop: 16, marginBottom: 16 }}>
        <Line label="Opening" value={myr(point.opening_balance)} />
        <Line label="Money in" value={myr(point.money_in)} />
        <Line label="Money out" value={myr(point.money_out)} />
      </View>
      <Divider />
      <View style={{ marginTop: 16 }}>
        <Line label="Closing" value={myr(point.closing_balance)} warning={negative} />
      </View>
      {detail.note && (
        <T v="label" c="secondary" style={{ marginTop: 14 }}>
          {detail.note}
        </T>
      )}
      <View style={{ flex: 1 }} />
      <View style={{ marginTop: 18, gap: 16, alignItems: "flex-start" }}>
        {negative && <Button label="Compare funding options" onPress={onCompareFunding} />}
        <LinkButton label="Ask about this week" arrow onPress={onAsk} />
      </View>
    </View>
  );
}

function Line({ label, value, warning }: { label: string; value: string; warning?: boolean }) {
  return (
    <Row justify="space-between">
      <T v="body" c="secondary">{label}</T>
      <T v="body" w="semibold" num c={warning ? "warning" : "ink"}>{value}</T>
    </Row>
  );
}

function WeeklyTable({
  base,
  comparison,
  selected,
  onSelect,
}: {
  base: Forecast;
  comparison: Forecast | null;
  selected: string;
  onSelect: (week: string) => void;
}) {
  // Summarise where the scenario differs, e.g. "W4 21,200 / W5 12,200; rejoin W6".
  const changed = comparison
    ? comparison.points.filter((point, index) => point.week && point.closing_balance !== base.points[index].closing_balance)
    : [];
  const lastChanged = changed[changed.length - 1];
  const rejoin = lastChanged && base.points[lastChanged.week + 1];
  const listed = changed.length > 3 ? changed.slice(0, 2) : changed;
  const scenarioNote = changed.length
    ? ` Scenario: ${listed.map((p) => `W${p.week} ${amount(p.closing_balance)}`).join(" / ")}` +
      (rejoin ? `; rejoins base in W${rejoin.week}.` : changed.length > listed.length ? "; differs through W13." : ".")
    : "";

  return (
    <Card padding={20}>
      <T v="panelHeading">Weekly table</T>
      <Row style={[styles.weekRow, { marginTop: 14 }]}>
        <T v="caption" c="secondary" style={{ flex: 1 }}>Week of</T>
        <T v="caption" c="secondary" align="right" style={styles.money}>Money in</T>
        <T v="caption" c="secondary" align="right" style={styles.money}>Money out</T>
        <T v="caption" c="secondary" align="right" style={styles.money}>Closing · MYR</T>
      </Row>
      {base.points.slice(1).map((point) => {
        const negative = point.closing_balance < 0;
        const active = point.week_of === selected;
        return (
          <Pressable
            key={point.week_of}
            onPress={() => onSelect(point.week_of)}
            style={[styles.weekRow, negative && styles.weekRowGap, active && !negative && styles.weekRowActive]}
          >
            <T v="label" w={active ? "semibold" : "regular"} c={negative ? "warning" : "ink"} style={{ flex: 1 }}>
              {dayMonth(point.week_of, point.week_of.startsWith("2027"))}
            </T>
            <T v="label" num align="right" c={negative ? "warning" : "ink"} style={styles.money}>{amount(point.money_in)}</T>
            <T v="label" num align="right" c={negative ? "warning" : "ink"} style={styles.money}>{amount(point.money_out)}</T>
            <T v="label" w="semibold" num align="right" c={negative ? "warning" : "ink"} style={styles.money}>
              {amount(point.closing_balance)}
            </T>
          </Pressable>
        );
      })}
      <T v="caption" c="secondary" style={{ marginTop: 12 }}>
        Today · {myr(base.points[0].closing_balance)}.{scenarioNote}
      </T>
    </Card>
  );
}

function WeekEvents({ week, scenario }: { week: string; scenario: Scenario }) {
  const { data, error, reload } = useWeek(week, scenario);
  if (!data) return <LoadState error={error} onRetry={reload} />;

  const range = weekRange(week);
  const totalIn = data.events.reduce((sum, event) => sum + (event.money_in ?? 0), 0);
  const totalOut = data.events.reduce((sum, event) => sum + (event.money_out ?? 0), 0);
  const delayed = data.delayed_receipt;

  return (
    <Card padding={20}>
      <Row justify="space-between">
        <T v="panelHeading">Events affecting this week</T>
        <Pill label={weekRange(week, true)} />
      </Row>
      <Row style={[styles.eventRow, { marginTop: 14, borderBottomWidth: 0 }]}>
        <T v="caption" c="secondary" style={styles.eventDate}>Date</T>
        <T v="caption" c="secondary" style={{ flex: 1 }}>Event</T>
        <T v="caption" c="secondary" align="right" style={styles.money}>Money in</T>
        <T v="caption" c="secondary" align="right" style={styles.money}>Money out</T>
        <T v="caption" c="secondary" style={styles.confidence}>Confidence</T>
      </Row>
      {data.events.map((event) => (
        <Row key={event.event} style={styles.eventRow}>
          <T v="label" c="secondary" style={styles.eventDate}>{range}</T>
          <T v="body" style={{ flex: 1 }}>{event.event}</T>
          <T v="body" num align="right" style={styles.money}>{event.money_in ? amount(event.money_in) : "—"}</T>
          <T v="body" num align="right" style={styles.money}>{event.money_out ? amount(event.money_out) : "—"}</T>
          <T v="caption" c="secondary" style={styles.confidence}>{event.confidence}</T>
        </Row>
      ))}
      <Row style={[styles.eventRow, { borderBottomWidth: 0 }]}>
        <T v="label" w="semibold" style={[styles.eventDate, { flex: 1 }]}>Total · MYR</T>
        <T v="body" w="semibold" num align="right" style={styles.money}>{amount(totalIn)}</T>
        <T v="body" w="semibold" num align="right" style={styles.money}>{amount(totalOut)}</T>
        <View style={styles.confidence} />
      </Row>
      {delayed && (
        <Row gap={10} style={{ marginTop: 12 }}>
          <Clock size={16} color={colors.warning} />
          <T v="label" c="emerald">
            Delayed: {delayed.customer} · {myr(delayed.amount)} · {dayMonth(delayed.originally_due)} → {dayMonth(delayed.now_expected)}
          </T>
          <T v="caption" c="secondary">Already in base case · not included above</T>
        </Row>
      )}
    </Card>
  );
}

const styles = themed(() =>
  StyleSheet.create({
    tab: { paddingVertical: 7, paddingHorizontal: 10, borderRadius: radius.pill, backgroundColor: colors.muted },
    tabActive: { backgroundColor: colors.selected },
    legendLine: { width: 22, height: 2, backgroundColor: colors.emerald },
    legendDashed: {
      height: 0,
      backgroundColor: "transparent",
      borderTopWidth: 2,
      borderStyle: "dashed",
      borderColor: colors.sage,
    },
    weekRow: {
      flexDirection: "row",
      alignItems: "center",
      paddingVertical: 7,
      paddingHorizontal: 8,
      borderRadius: 8,
    },
    weekRowGap: { backgroundColor: colors.warningSurface },
    weekRowActive: { backgroundColor: colors.selected },
    money: { width: 140 },
    eventRow: { paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.edge },
    eventDate: { width: 136 },
    confidence: { width: 180, paddingLeft: 16 },
  }),
);
