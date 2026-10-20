import { ReactNode, useState } from "react";
import {
  Pressable,
  StyleProp,
  StyleSheet,
  Text,
  TextProps,
  TextStyle,
  View,
  ViewStyle,
} from "react-native";
import { ArrowUpRight, ChevronDown, LucideIcon } from "lucide-react-native";

import { cardShadow, colors, fonts, radius, themed, type } from "../theme";

type Weight = keyof typeof fonts;
type Tone =
  | "ink"
  | "secondary"
  | "emerald"
  | "warning"
  | "danger"
  | "porcelain"
  | "onAccent"
  | "selectedText"
  | "heroText"
  | "heroLabel";

const toneColor = themed(
  (): Record<Tone, string> => ({
    ink: colors.ink,
    secondary: colors.secondary,
    emerald: colors.emerald,
    warning: colors.warning,
    danger: colors.danger,
    porcelain: colors.porcelain,
    onAccent: colors.onAccent,
    selectedText: colors.selectedText,
    heroText: colors.heroText,
    heroLabel: colors.heroLabel,
  }),
);

export function T({
  v = "body",
  w,
  c = "ink",
  align,
  num,
  style,
  ...props
}: TextProps & {
  v?: keyof typeof type;
  w?: Weight;
  c?: Tone;
  align?: TextStyle["textAlign"];
  num?: boolean;
}) {
  return (
    <Text
      {...props}
      style={[
        type[v],
        w && { fontFamily: fonts[w] },
        { color: toneColor[c] },
        align && { textAlign: align },
        num && { fontVariant: ["tabular-nums"] },
        style,
      ]}
    />
  );
}

export function Card({
  children,
  style,
  padding = 24,
}: {
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
  padding?: number;
}) {
  return <View style={[styles.card, { padding }, style]}>{children}</View>;
}

export function Row({
  children,
  gap = 0,
  align = "center",
  justify,
  style,
}: {
  children: ReactNode;
  gap?: number;
  align?: ViewStyle["alignItems"];
  justify?: ViewStyle["justifyContent"];
  style?: StyleProp<ViewStyle>;
}) {
  return (
    <View style={[{ flexDirection: "row", alignItems: align, justifyContent: justify, gap }, style]}>
      {children}
    </View>
  );
}

export function Divider({ style }: { style?: StyleProp<ViewStyle> }) {
  return <View style={[{ height: 1, backgroundColor: colors.edge }, style]} />;
}

type PillTone = "jade" | "muted" | "warning" | "outline";

const pillStyles = themed(
  (): Record<PillTone, { bg: string; fg: Tone; border?: string }> => ({
    jade: { bg: colors.jade, fg: "emerald" },
    muted: { bg: colors.muted, fg: "secondary" },
    warning: { bg: colors.warningSurface, fg: "warning" },
    outline: { bg: colors.porcelain, fg: "secondary", border: colors.edge },
  }),
);

export function Pill({ label, tone = "muted", size = "md" }: { label: string; tone?: PillTone; size?: "sm" | "md" }) {
  const look = pillStyles[tone];
  return (
    <View
      style={[
        styles.pill,
        size === "sm" && { paddingVertical: 3, paddingHorizontal: 8 },
        { backgroundColor: look.bg, borderColor: look.border ?? look.bg },
      ]}
    >
      <T v="caption" w="medium" c={look.fg}>
        {label}
      </T>
    </View>
  );
}

export function Button({
  label,
  onPress,
  variant = "primary",
  disabled,
  icon: Icon,
}: {
  label: string;
  onPress?: () => void;
  variant?: "primary" | "secondary";
  disabled?: boolean;
  icon?: LucideIcon;
}) {
  const primary = variant === "primary";
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={(state) => [
        styles.button,
        primary ? styles.buttonPrimary : styles.buttonSecondary,
        (state as { hovered?: boolean }).hovered && !disabled && { opacity: 0.9 },
        disabled && { backgroundColor: colors.muted, borderColor: colors.muted },
      ]}
    >
      {Icon && <Icon size={16} color={primary ? colors.onAccent : colors.emerald} />}
      <T v="body" w="semibold" c={disabled ? "secondary" : primary ? "onAccent" : "emerald"}>
        {label}
      </T>
    </Pressable>
  );
}

export function LinkButton({
  label,
  onPress,
  arrow,
  tone = "emerald",
  v = "body",
}: {
  label: string;
  onPress?: () => void;
  arrow?: boolean;
  tone?: Tone;
  v?: keyof typeof type;
}) {
  return (
    <Pressable onPress={onPress} hitSlop={6}>
      {(state) => (
        <Row gap={6}>
          <T
            v={v}
            w="semibold"
            c={tone}
            style={(state as { hovered?: boolean }).hovered && { textDecorationLine: "underline" }}
          >
            {label}
          </T>
          {arrow && <ArrowUpRight size={15} color={toneColor[tone]} strokeWidth={2.2} />}
        </Row>
      )}
    </Pressable>
  );
}

export function IconBadge({ icon: Icon, size = 48 }: { icon: LucideIcon; size?: number }) {
  return (
    <View style={[styles.iconBadge, { width: size, height: size, borderRadius: size / 3.2 }]}>
      <Icon size={size * 0.46} color={colors.emerald} />
    </View>
  );
}

export type Option<V> = { value: V; label: string };

/** Dropdown styled like the Figma field; the list opens below and overlays the content. */
export function Select<V extends string | number>({
  value,
  options,
  onChange,
  disabled,
  style,
}: {
  value: V;
  options: Option<V>[];
  onChange: (value: V) => void;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  const [open, setOpen] = useState(false);
  const current = options.find((option) => option.value === value);
  return (
    <View style={[{ zIndex: open ? 50 : 1 }, style]}>
      <Pressable
        disabled={disabled}
        onPress={() => setOpen(!open)}
        style={[styles.field, disabled && { backgroundColor: colors.porcelain }]}
      >
        <T v="body" style={{ flex: 1 }} numberOfLines={1}>
          {current?.label ?? ""}
        </T>
        {!disabled && <ChevronDown size={16} color={colors.secondary} />}
      </Pressable>
      {open && (
        <View style={styles.menu}>
          {options.map((option) => (
            <Pressable
              key={String(option.value)}
              onPress={() => {
                onChange(option.value);
                setOpen(false);
              }}
              style={(state) => [
                styles.menuItem,
                ((state as { hovered?: boolean }).hovered || option.value === value) && {
                  backgroundColor: colors.limestone,
                },
              ]}
            >
              <T v="body" w={option.value === value ? "semibold" : undefined}>
                {option.label}
              </T>
            </Pressable>
          ))}
        </View>
      )}
    </View>
  );
}

const styles = themed(() =>
  StyleSheet.create({
    card: {
      backgroundColor: colors.porcelain,
      borderRadius: radius.card,
      borderWidth: 1,
      borderColor: colors.edge,
      ...cardShadow,
    },
    pill: {
      alignSelf: "flex-start",
      borderRadius: radius.pill,
      borderWidth: 1,
      paddingVertical: 4,
      paddingHorizontal: 9,
    },
    button: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "center",
      gap: 8,
      height: 44,
      paddingHorizontal: 14,
      borderRadius: radius.field,
      borderWidth: 1,
    },
    buttonPrimary: { backgroundColor: colors.emerald, borderColor: colors.primaryEdge },
    buttonSecondary: { backgroundColor: colors.raised, borderColor: colors.controlEdge },
    iconBadge: { backgroundColor: colors.jade, alignItems: "center", justifyContent: "center" },
    field: {
      flexDirection: "row",
      alignItems: "center",
      gap: 10,
      height: 44,
      paddingHorizontal: 14,
      borderRadius: radius.field,
      borderWidth: 1,
      borderColor: colors.controlEdge,
      backgroundColor: colors.raised,
    },
    menu: {
      position: "absolute",
      top: 48,
      left: 0,
      right: 0,
      padding: 6,
      borderRadius: radius.field,
      borderWidth: 1,
      borderColor: colors.edge,
      backgroundColor: colors.raised,
      shadowColor: colors.shadow,
      shadowOffset: { width: 0, height: 10 },
      shadowOpacity: 0.1,
      shadowRadius: 24,
    },
    menuItem: { paddingVertical: 9, paddingHorizontal: 10, borderRadius: 8 },
  }),
);

/** Styles other components reuse, e.g. `shared.field` for a field that isn't a Select. */
export const shared = themed(() => ({ field: styles.field }));
