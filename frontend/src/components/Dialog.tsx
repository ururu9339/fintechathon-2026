import { ReactNode } from "react";
import { Pressable, ScrollView, StyleSheet, View } from "react-native";
import { X } from "lucide-react-native";

import { colors, fonts, radius, themed } from "../theme";
import { Row, T } from "./ui";

/** Modal frame from the Figma "Review payment" screen: dimmed backdrop, 30px-radius sheet. */
export function Dialog({
  label,
  onClose,
  width = 680,
  children,
}: {
  label: string;
  onClose: () => void;
  width?: number;
  children: ReactNode;
}) {
  return (
    <View style={styles.overlay}>
      <Pressable style={StyleSheet.absoluteFill} onPress={onClose} accessibilityLabel="Close dialog" />
      <View style={[styles.dialog, { width }]} role="dialog" aria-modal aria-label={label}>
        <ScrollView contentContainerStyle={{ padding: 28 }}>{children}</ScrollView>
      </View>
    </View>
  );
}

export function DialogTitle({ title, subtitle, onClose }: { title: string; subtitle?: string; onClose: () => void }) {
  return (
    <Row justify="space-between" align="flex-start">
      <View>
        <T style={styles.title}>{title}</T>
        {subtitle ? (
          <T v="body" c="secondary">
            {subtitle}
          </T>
        ) : null}
      </View>
      <Pressable onPress={onClose} hitSlop={10} accessibilityLabel="Close">
        <X size={22} color={colors.ink} />
      </Pressable>
    </Row>
  );
}

const styles = themed(() =>
  StyleSheet.create({
    overlay: {
      ...StyleSheet.absoluteFillObject,
      backgroundColor: colors.dimmer,
      alignItems: "center",
      paddingTop: 40,
      paddingBottom: 40,
      zIndex: 100,
    },
    dialog: {
      maxHeight: "100%",
      backgroundColor: colors.raised,
      borderRadius: radius.dialog,
      borderWidth: 1,
      borderColor: colors.dialogEdge,
      shadowColor: colors.shadow,
      shadowOffset: { width: 0, height: 24 },
      shadowOpacity: 0.18,
      shadowRadius: 60,
    },
    title: { fontFamily: fonts.semibold, fontSize: 26, lineHeight: 32, color: colors.ink },
  }),
);
