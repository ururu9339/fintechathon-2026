import { useState } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import { Info } from "lucide-react-native";

import { api, Financing as FinancingData, FinancingOption, Forecast, ForecastPoint } from "../api";
import { useApp } from "../AppContext";
import { ForecastChart } from "../components/ForecastChart";
import { PageHeader } from "../components/Shell";
import { LoadState } from "../components/States";
import { Button, Card, Divider, LinkButton, Pill, Row, Select, T } from "../components/ui";
import { amount as plain, dayMonth, myr } from "../format";
import { colors, themed } from "../theme";
import { useResource } from "../useResource";

export function Financing() {
  const { refreshKey, navigate } = useApp();
  const [chosenAmount, setChosenAmount] = useState<number | undefined>(undefined);
  const { data, error, reload } = useResource(
    () => Promise.all([api.financing(chosenAmount), api.forecast("base")]),
    [chosenAmount, refreshKey],
  );

  return (
    <View>
      <PageHeader
        title="Financing options"
        subtitle="Compare the cost and cash-flow effect before deciding."
        right={<LinkButton label="Back to cash plan" arrow onPress={() => navigate("cashflow")} />}
      />
      {!data ? (
        <LoadState error={error} onRetry={reload} />
      ) : data[0] ? (
        <FinancingContent financing={data[0]} base={data[1]} onAmount={setChosenAmount} />
      ) : (
        <Card>
          <T v="caption" w="semibold" c="secondary">No financing matches</T>
          <T v="body" style={{ marginTop: 4, marginBottom: 12 }}>
            Your base forecast has no cash gap, so there's nothing to fund.
          </T>
          <LinkButton label="Back to cash plan" arrow onPress={() => navigate("cashflow")} />
        </Card>
      )}
    </View>
  );
}

/** Base forecast plus the funding received (and repaid, if inside the 13 weeks). */
function withFunding(points: ForecastPoint[], option: FinancingOption): ForecastPoint[] {
  return points.map((point) => {
    let closing = point.closing_balance;
    if (point.week && point.week_of >= weekStart(option.receipt_on)) closing += option.amount;
    if (point.week && point.week_of >= weekStart(option.repayment_on)) closing -= option.total_repayment;
    return { ...point, closing_balance: closing };
  });
}

/** Monday of the week containing an ISO date. */
function weekStart(iso: string): string {
  const [year, month, day] = iso.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  date.setUTCDate(date.getUTCDate() - ((date.getUTCDay() + 6) % 7));
  return date.toISOString().slice(0, 10);
}

function FinancingContent({
  financing,
  base,
  onAmount,
}: {
  financing: FinancingData;
  base: Forecast;
  onAmount: (value: number) => void;
}) {
  const { workspace, navigate, refresh, notify } = useApp();
  const inScenario = financing.in_scenario;
  const [selectedName, setSelectedName] = useState(inScenario?.name ?? financing.options[0].name);
  const [busy, setBusy] = useState(false);
  const selected = financing.options.find((option) => option.name === selectedName) ?? financing.options[0];
  const letter = (option: FinancingOption) => option.name.split(" ").pop();

  const funded = withFunding(base.points, selected);
  const gapWeek = financing.needed_by;
  const gapAfter = funded.find((point) => point.week_of === gapWeek)?.closing_balance ?? 0;
  const lastWeek = base.points[base.points.length - 1].week_of;
  const repaidOutside = financing.options.every((option) => weekStart(option.repayment_on) > lastWeek);
  const added = inScenario?.name === selected.name && inScenario.amount === selected.amount;

  async function run(action: () => Promise<unknown>, message: string) {
    setBusy(true);
    try {
      await action();
      refresh();
      notify(message, "success");
    } catch (error) {
      notify((error as Error).message, "info");
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={{ gap: 20 }}>
      <Row gap={20} align="center">
        <View style={{ flex: 1, gap: 4 }}>
          <T v="body" w="semibold" c="warning">{myr(financing.shortfall)} projected shortfall</T>
          <T v="label" c="secondary">
            {dayMonth(financing.needed_by, true)} · {myr(financing.buffer)} buffer with this scenario
          </T>
        </View>
        <Card padding={18} style={{ flex: 1.15, zIndex: 10 }}>
          <Row gap={24} align="flex-start">
            <View style={{ width: 170, gap: 6 }}>
              <T v="caption" c="secondary">Amount</T>
              <Select
                value={financing.amount}
                options={financing.amount_choices.map((value) => ({ value, label: myr(value) }))}
                onChange={onAmount}
              />
            </View>
            <View style={{ flex: 1, gap: 6 }}>
              <T v="caption" c="secondary">Needed by</T>
              <T v="body" w="semibold" style={{ marginTop: 10 }}>{dayMonth(financing.needed_by)}</T>
            </View>
            <View style={{ gap: 6, alignItems: "flex-end" }}>
              <T v="caption" c="secondary">Purpose</T>
              <T v="body" w="semibold" style={{ marginTop: 10 }}>{financing.purpose}</T>
            </View>
          </Row>
        </Card>
      </Row>

      <Row justify="space-between">
        <Row gap={8}>
          <Info size={17} color={colors.ink} />
          <T v="body" w="semibold">Illustrative scenarios — not live offers</T>
        </Row>
        <T v="caption" c="secondary">Updated {workspace?.updated_at}</T>
      </Row>

      <Row gap={20} align="stretch">
        {financing.options.map((option) => (
          <OptionCard
            key={option.name}
            option={option}
            selected={option.name === selected.name}
            inScenario={inScenario?.name === option.name && inScenario.amount === option.amount}
            onSelect={() => setSelectedName(option.name)}
          />
        ))}
      </Row>

      <Card>
        <Row justify="space-between">
          <T v="panelHeading">Cash-flow impact</T>
          <Row gap={20}>
            <Legend label="Base case" />
            <Legend label={`With ${myr(selected.amount)} funding`} dashed />
          </Row>
        </Row>
        <Row justify="space-between" style={{ marginTop: 14, marginBottom: 12 }}>
          <T v="body" w="semibold" num>
            {dayMonth(gapWeek)} balance: {plain(-financing.shortfall)} → {plain(gapAfter)}
          </T>
          <T v="caption" c="secondary">Projected cash balance (MYR) · Scenario {letter(selected)}</T>
        </Row>
        <ForecastChart points={base.points} comparison={funded} highlight={gapWeek} band />
        <Divider style={{ marginTop: 16 }} />
        <Row justify="space-between" style={{ marginTop: 16 }}>
          <View style={{ gap: 2 }}>
            <T v="label" w="medium">
              {repaidOutside ? "Repayment falls outside this 13-week view." : "Repayment is included in this view."}
            </T>
            <T v="caption" c="secondary">
              {financing.options
                .map((option) => `${letter(option)}: ${myr(option.total_repayment)} on ${dayMonth(option.repayment_on, true)}`)
                .join(" · ")}
            </T>
          </View>
          <Row gap={10}>
            <Button
              label="Compare earlier customer payment"
              variant="secondary"
              onPress={() => navigate("cashflow", { scenario: "earlier_customer_payment" })}
            />
            {added ? (
              <>
                <Button
                  label="Remove from scenario"
                  variant="secondary"
                  disabled={busy}
                  onPress={() => run(api.clearFundingScenario, "Scenario removed. Your base forecast is unchanged.")}
                />
                <Button label="View in cash flow" onPress={() => navigate("cashflow", { scenario: "with_funding" })} />
              </>
            ) : (
              <Button
                label="Add to scenario"
                disabled={busy}
                onPress={() =>
                  run(
                    () => api.addFundingScenario(selected.name, selected.amount),
                    "Scenario updated. No application has been submitted.",
                  )
                }
              />
            )}
          </Row>
        </Row>
      </Card>

      <T v="caption" c="secondary">
        Adding a scenario changes a forecast assumption only. No application is submitted and no funding is approved.
      </T>
    </View>
  );
}

function OptionCard({
  option,
  selected,
  inScenario,
  onSelect,
}: {
  option: FinancingOption;
  selected: boolean;
  inScenario: boolean;
  onSelect: () => void;
}) {
  return (
    <Pressable
      onPress={onSelect}
      accessibilityRole="radio"
      accessibilityState={{ checked: selected }}
      style={[styles.option, selected && styles.optionSelected]}
    >
      <Row justify="space-between">
        <T v="panelHeading">{option.name}</T>
        <Pill
          label={inScenario ? "In forecast scenario" : selected ? "Selected for comparison" : "Illustrative scenario"}
          tone={selected || inScenario ? "jade" : "muted"}
        />
      </Row>
      <View style={{ gap: 10, marginTop: 18, marginBottom: 14 }}>
        <Term label="Amount received" value={myr(option.amount)} />
        <Term label="Illustrative term" value={`${option.term_days} days`} />
        <Term label="Illustrative total fee" value={myr(option.fee)} />
        <Term label="Total repayment" value={myr(option.total_repayment)} />
      </View>
      <Divider />
      <View style={{ gap: 10, marginTop: 14 }}>
        <Term label="Assumed receipt" value={dayMonth(option.receipt_on, true)} />
        <Term label="Assumed repayment" value={dayMonth(option.repayment_on, true)} />
      </View>
    </Pressable>
  );
}

function Term({ label, value }: { label: string; value: string }) {
  return (
    <Row justify="space-between">
      <T v="body" c="secondary">{label}</T>
      <T v="body" w="semibold" num>{value}</T>
    </Row>
  );
}

function Legend({ label, dashed }: { label: string; dashed?: boolean }) {
  return (
    <Row gap={8}>
      <View
        style={
          dashed
            ? { width: 22, borderTopWidth: 2, borderStyle: "dashed", borderColor: colors.sage }
            : { width: 22, height: 2, backgroundColor: colors.emerald }
        }
      />
      <T v="caption" c="secondary">{label}</T>
    </Row>
  );
}

const styles = themed(() =>
  StyleSheet.create({
    option: {
      flex: 1,
      padding: 20,
      borderRadius: 28,
      borderWidth: 1,
      borderColor: colors.edge,
      backgroundColor: colors.porcelain,
    },
    optionSelected: { borderColor: colors.sage },
  }),
);
