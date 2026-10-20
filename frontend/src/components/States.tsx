import { View } from "react-native";

import { colors } from "../theme";
import { Card, LinkButton, T } from "./ui";

/** Loading and error states from the Foundations "Data and queues" panel. */
export function LoadState({ error, onRetry }: { error: string | null; onRetry: () => void }) {
  if (error) {
    return (
      <Card style={{ backgroundColor: colors.warningSurface, borderColor: colors.warningSurface }}>
        <T v="caption" w="semibold" c="warning">
          Can't reach AmanahPay
        </T>
        <T v="body" c="warning" style={{ marginTop: 4, marginBottom: 10 }}>
          {error}. Check that the API is running, then try again.
        </T>
        <LinkButton label="Refresh" onPress={onRetry} />
      </Card>
    );
  }
  return (
    <Card>
      <T v="caption" w="semibold" c="secondary">
        Loading
      </T>
      <T v="body" style={{ marginTop: 4 }}>
        Updating your cash position…
      </T>
      <View style={{ flexDirection: "row", gap: 8, marginTop: 14 }}>
        <View style={{ width: 120, height: 12, borderRadius: 6, backgroundColor: colors.muted }} />
        <View style={{ width: 80, height: 12, borderRadius: 6, backgroundColor: colors.muted }} />
      </View>
    </Card>
  );
}
