import { ReactNode } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import Svg, { Path } from "react-native-svg";
import {
  Building2,
  CalendarDays,
  ChartNoAxesCombined,
  ChevronDown,
  CreditCard,
  Landmark,
  LayoutDashboard,
  LogOut,
  LucideIcon,
  MessageCircle,
  Moon,
  ShieldCheck,
  SlidersHorizontal,
  Sun,
} from "lucide-react-native";

import type { Workspace } from "../api";
import { longDate } from "../format";
import { BRAND, colors, isDark, radius, themed } from "../theme";
import { Divider, Pill, Row, T } from "./ui";

export type Screen = "overview" | "cashflow" | "payments" | "reserves" | "financing" | "rules" | "ask";

const MAIN_NAV: { screen: Screen; label: string; icon: LucideIcon }[] = [
  { screen: "overview", label: "Overview", icon: LayoutDashboard },
  { screen: "cashflow", label: "Cash flow", icon: ChartNoAxesCombined },
  { screen: "payments", label: "Payments", icon: CreditCard },
  { screen: "reserves", label: "Reserves", icon: ShieldCheck },
  { screen: "financing", label: "Financing", icon: Landmark },
];

const SUPPORT_NAV: { screen: Screen; label: string; icon: LucideIcon }[] = [
  { screen: "rules", label: "Payment rules", icon: SlidersHorizontal },
  { screen: "ask", label: "Ask Amanah", icon: MessageCircle },
];

export function LogoMark({ size = 32 }: { size?: number }) {
  // The dark theme sets the mark on an ivory tile (4px larger than `size`), inset so it
  // doesn't touch the tile's edges.
  const dark = isDark();
  const inset = dark ? Math.round(size * 0.14) : 0;
  const markSize = dark ? size + 4 - inset * 2 : size;
  // One continuous line draws the frame, loops into the ring and hooks back into the
  // bottom edge; the pen crosses it from the ring's centre to the nib at the corner.
  const mark = (
    <Svg width={markSize} height={markSize} viewBox="0 0 230 230">
      <Path
        d="M180 217.5 L40 217.5 A26.5 26.5 0 0 1 13.5 191 L13.5 10.5 L197.5 10.5 A20 20 0 0 1 217.5 30.5 L217.5 156 A15.5 15.5 0 0 1 186.5 156 C186.5 142 175 128 175 113 A61 61 0 1 0 114 174 C140 172 163 186 180 217.5"
        fill="none"
        stroke={BRAND}
        strokeWidth={20.5}
        strokeLinejoin="miter"
        strokeLinecap="round"
      />
      <Path d="M124.5 108 L211.5 195 L226 225 L194.5 208 L109.5 123 Z" fill={BRAND} />
    </Svg>
  );
  if (!dark) return mark;
  return (
    <View style={{ padding: inset, borderRadius: size * 0.3, backgroundColor: colors.logoTile }}>{mark}</View>
  );
}

/** Sun / moon button that switches between the light and dark themes. */
export function ThemeToggle({ onToggle }: { onToggle: () => void }) {
  const dark = isDark();
  const Icon = dark ? Sun : Moon;
  return (
    <Pressable
      onPress={onToggle}
      hitSlop={8}
      accessibilityRole="button"
      accessibilityLabel={dark ? "Switch to light theme" : "Switch to dark theme"}
      style={(state) => [styles.iconButton, (state as { hovered?: boolean }).hovered && { backgroundColor: colors.selected }]}
    >
      <Icon size={17} color={colors.secondary} />
    </Pressable>
  );
}

export function Sidebar({
  screen,
  onNavigate,
  pendingApprovals,
  workspace,
  onSignOut,
}: {
  screen: Screen;
  onNavigate: (screen: Screen) => void;
  pendingApprovals: number;
  workspace: Workspace | null;
  onSignOut: () => void;
}) {
  const initials = (workspace?.owner ?? "")
    .split(" ")
    .map((part) => part[0])
    .join("");
  return (
    <View style={styles.sidebar}>
      <Row gap={10} style={{ paddingHorizontal: 8, marginTop: 30 }}>
        <LogoMark />
        <View>
          <T v="title">AmanahPay</T>
          <T v="small" c="secondary">
            Treasurer
          </T>
        </View>
      </Row>

      <View style={{ marginTop: 32, gap: 6 }}>
        {MAIN_NAV.map((item) => (
          <NavItem
            key={item.screen}
            {...item}
            active={screen === item.screen}
            onPress={() => onNavigate(item.screen)}
            badge={item.screen === "payments" ? pendingApprovals : 0}
          />
        ))}
      </View>

      <View style={{ flex: 1 }} />

      <View style={{ gap: 6, marginBottom: 32 }}>
        {SUPPORT_NAV.map((item) => (
          <NavItem key={item.screen} {...item} active={screen === item.screen} onPress={() => onNavigate(item.screen)} />
        ))}
      </View>
      <Divider />
      <Row gap={10} style={{ paddingHorizontal: 8, paddingVertical: 24 }}>
        <View style={styles.avatar}>
          <T v="caption" w="semibold">
            {initials}
          </T>
        </View>
        <View style={{ flex: 1 }}>
          <T v="body" w="semibold">
            {workspace?.owner}
          </T>
          <T v="caption" c="secondary">
            {workspace?.owner_role}
          </T>
        </View>
        <Pressable
          onPress={onSignOut}
          hitSlop={8}
          accessibilityRole="button"
          accessibilityLabel="Sign out"
          style={(state) => [styles.iconButton, (state as { hovered?: boolean }).hovered && { backgroundColor: colors.selected }]}
        >
          <LogOut size={17} color={colors.secondary} />
        </Pressable>
      </Row>
    </View>
  );
}

function NavItem({
  label,
  icon: Icon,
  active,
  onPress,
  badge = 0,
}: {
  label: string;
  icon: LucideIcon;
  active: boolean;
  onPress: () => void;
  badge?: number;
}) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="link"
      accessibilityState={{ selected: active }}
      style={(state) => [
        styles.navItem,
        active && { backgroundColor: colors.selected },
        !active && (state as { hovered?: boolean }).hovered && { backgroundColor: colors.limestone },
      ]}
    >
      <Icon size={19} color={active ? colors.selectedText : colors.secondary} strokeWidth={1.8} />
      <T v="body" w={active ? "semibold" : "medium"} c={active ? "selectedText" : "secondary"} style={{ flex: 1 }}>
        {label}
      </T>
      {badge > 0 && (
        <View style={styles.badge}>
          <T v="small" w="semibold" c="warning">
            {badge}
          </T>
        </View>
      )}
    </Pressable>
  );
}

export function TopBar({ workspace, onToggleTheme }: { workspace: Workspace | null; onToggleTheme: () => void }) {
  return (
    <Row justify="space-between" style={{ height: 40 }}>
      <Row gap={9}>
        <Building2 size={18} color={colors.ink} />
        <T v="body" w="semibold">
          {workspace?.company}
        </T>
        <ChevronDown size={14} color={colors.ink} />
      </Row>
      {workspace && (
        <Row gap={20}>
          <Row gap={20}>
            <CalendarDays size={16} color={colors.secondary} />
            <T v="label" c="secondary">
              {longDate(workspace.demo_date)}
            </T>
          </Row>
          {workspace.demo_data && <Pill label="Demo data" />}
          <T v="label" c="secondary">
            {workspace.owner} · {workspace.owner_role}
          </T>
          <ThemeToggle onToggle={onToggleTheme} />
        </Row>
      )}
    </Row>
  );
}

export function PageHeader({ title, subtitle, right }: { title: string; subtitle: string; right?: ReactNode }) {
  return (
    <Row justify="space-between" align="center" style={{ marginTop: 24, marginBottom: 24, minHeight: 72 }}>
      <View style={{ gap: 3 }}>
        <T v="screenHeading">{title}</T>
        <T v="body" c="secondary">
          {subtitle}
        </T>
      </View>
      {right}
    </Row>
  );
}

const styles = themed(() =>
  StyleSheet.create({
    sidebar: {
      width: 224,
      paddingHorizontal: 16,
      backgroundColor: colors.sidebar,
      borderRightWidth: 1,
      borderRightColor: colors.edge,
    },
    iconButton: {
      width: 32,
      height: 32,
      borderRadius: radius.field,
      alignItems: "center",
      justifyContent: "center",
    },
    navItem: {
      flexDirection: "row",
      alignItems: "center",
      gap: 12,
      height: 48,
      paddingHorizontal: 14,
      borderRadius: radius.nav,
    },
    badge: {
      width: 21,
      height: 21,
      borderRadius: 11,
      backgroundColor: colors.warningSurface,
      alignItems: "center",
      justifyContent: "center",
    },
    avatar: {
      width: 34,
      height: 34,
      borderRadius: 17,
      backgroundColor: colors.jade,
      alignItems: "center",
      justifyContent: "center",
    },
  }),
);
