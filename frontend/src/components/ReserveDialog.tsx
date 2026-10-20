import { useState } from "react";
import { View } from "react-native";
import { TriangleAlert } from "lucide-react-native";

import { api, Balances, Commitment, Reserve } from "../api";
import { useApp } from "../AppContext";
import { myr } from "../format";
import { colors, radius } from "../theme";
import { useResource } from "../useResource";
import { Dialog, DialogTitle } from "./Dialog";
import { Button, Divider, Row, Select, shared, T } from "./ui";

const STEPS = [500, 1000, 2000, 5000, 10000];

export type ReserveDialogMode = "add" | "release";

/** "Add to reserve" and "Release from reserve" from the Foundations sheet. Cash never changes. */
export function ReserveDialog({
  mode,
  reserves,
  balances,
  initialKey,
  onClose,
}: {
  mode: ReserveDialogMode;
  reserves: Reserve[];
  balances: Balances;
  initialKey: string;
  onClose: () => void;
}) {
  const { refresh, notify } = useApp();
  const [key, setKey] = useState(initialKey);
  const reserve = reserves.find((item) => item.key === key) ?? reserves[0];
  const limit = mode === "add" ? balances.available : reserve.allocated;
  const choices = STEPS.filter((step) => step <= limit);
  const [value, setValue] = useState(choices.includes(1000) ? 1000 : choices[0] ?? 0);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const commitments = useResource(() => api.commitments(key), [key]).data ?? [];

  const amount = choices.includes(value) ? value : choices[0] ?? 0;
  const sign = mode === "add" ? 1 : -1;
  const reserveAfter = reserve.allocated + sign * amount;
  const availableAfter = balances.available - sign * amount;
  const committed = commitments.reduce((sum, item) => sum + item.amount, 0);
  const shortAfter = Math.max(0, committed - reserveAfter);

  async function confirm() {
    setBusy(true);
    setFailure(null);
    try {
      await (mode === "add" ? api.allocate(key, amount) : api.release(key, amount));
      refresh();
      notify(`${reserve.name}: ${myr(reserveAfter)}. Available: ${myr(availableAfter)}. Cash unchanged.`, "success");
      onClose();
    } catch (error) {
      setFailure((error as Error).message);
      setBusy(false);
    }
  }

  return (
    <Dialog label={mode === "add" ? "Add to reserve" : "Release from reserve"} onClose={onClose} width={520}>
      <DialogTitle
        title={mode === "add" ? "Add to reserve" : `Release from ${reserve.name}`}
        subtitle="Reserves set money aside inside your cash balance."
        onClose={onClose}
      />

      <View style={{ marginTop: 22, gap: 8 }}>
        <T v="caption" c="secondary">{mode === "add" ? "Source" : "Return to"}</T>
        <View style={shared.field}>
          <T v="body">Available to spend · {myr(balances.available)}</T>
        </View>
      </View>

      <Row gap={12} style={{ marginTop: 16, zIndex: 10 }}>
        <View style={{ flex: 1, gap: 8 }}>
          <T v="caption" c="secondary">Reserve</T>
          <Select
            value={key}
            options={reserves.map((item) => ({ value: item.key, label: item.name }))}
            onChange={setKey}
            disabled={mode === "release"}
          />
        </View>
        <View style={{ flex: 1, gap: 8 }}>
          <T v="caption" c="secondary">Amount</T>
          {choices.length ? (
            <Select value={amount} options={choices.map((step) => ({ value: step, label: myr(step) }))} onChange={setValue} />
          ) : (
            <View style={shared.field}>
              <T v="body" c="secondary">Nothing to {mode === "add" ? "add" : "release"}</T>
            </View>
          )}
        </View>
      </Row>

      <View style={{ marginTop: 20, gap: 10 }}>
        <Row justify="space-between">
          <T v="body" c="secondary">Available after</T>
          <T v="body" w="semibold" num>{myr(availableAfter)}</T>
        </Row>
        <Row justify="space-between">
          <T v="body" c="secondary">{reserve.name} after</T>
          <T v="body" w="semibold" num>{myr(reserveAfter)}</T>
        </Row>
      </View>
      <T v="caption" c="secondary" style={{ marginTop: 10 }}>
        Cash balance remains {myr(balances.cash)}.
      </T>

      {mode === "release" && commitments.length > 0 && (
        <ReleaseImpact commitments={commitments} shortAfter={shortAfter} />
      )}

      {failure && (
        <T v="label" c="danger" style={{ marginTop: 12 }}>
          {failure}
        </T>
      )}

      <Divider style={{ marginTop: 20 }} />
      <Row justify="flex-end" gap={10} style={{ marginTop: 16 }}>
        <Button label="Cancel" variant="secondary" onPress={onClose} />
        <Button
          label={mode === "add" ? "Add to reserve" : "Confirm release"}
          disabled={busy || amount === 0}
          onPress={confirm}
        />
      </Row>
    </Dialog>
  );
}

function ReleaseImpact({ commitments, shortAfter }: { commitments: Commitment[]; shortAfter: number }) {
  return (
    <View
      style={{
        marginTop: 16,
        padding: 14,
        borderRadius: radius.field,
        backgroundColor: shortAfter ? colors.warningSurface : colors.limestone,
        gap: 4,
      }}
    >
      <T v="caption" c="secondary">
        Affected commitments: {commitments.map((item) => `${item.title} ${myr(item.amount)}`).join(" · ")}.
      </T>
      {shortAfter > 0 && (
        <Row gap={8}>
          <TriangleAlert size={15} color={colors.warning} />
          <T v="label" c="warning">Releasing funds would leave these goals {myr(shortAfter)} short.</T>
        </Row>
      )}
    </View>
  );
}
