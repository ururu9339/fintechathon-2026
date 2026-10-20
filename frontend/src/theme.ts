import { TextStyle } from "react-native";

export type ThemeName = "light" | "dark";

// Tokens from the Figma "AmanahPay · Foundations" sheet (light) and its "02 Dark theme" page.
// Names describe the role in the light design; the dark palette fills the same roles.
const light = {
  limestone: "#F5F3EE", // page background
  porcelain: "#FFFEFB", // cards
  raised: "#FFFEFB", // dialogs, fields, menus, secondary buttons
  sidebar: "#FFFEFB",
  emerald: "#123E35", // accent: links, primary buttons, chart line
  emeraldLight: "#50886F",
  ink: "#172925",
  secondary: "#5D6E67",
  jade: "#E4ECE5", // positive surfaces: pills, avatar, question bubble
  selected: "#E4ECE5", // selected nav item, tab or row
  selectedText: "#123E35",
  edge: "#E2E5DE",
  controlEdge: "#E2E5DE", // border of fields and secondary buttons
  muted: "#EFF0EB",
  warning: "#8B5B1E",
  warningSurface: "#FBF2E3",
  danger: "#9A3F2C",
  sage: "#7FA08E",
  sageLight: "#B5C9BC",
  reserveSecondary: "#5E8C78",
  reserveTertiary: "#9DBAA9",
  dimmer: "rgba(23, 41, 37, 0.42)",
  dialogEdge: "transparent",
  onAccent: "#FFFEFB", // text on emerald
  primaryEdge: "#123E35",
  axis: "rgba(93, 110, 103, 0.55)", // zero line on charts
  shadow: "#172925",
  heroStart: "#123E35", // "Available to spend" card background (a gradient in the dark theme)
  heroMid: "#123E35",
  heroEnd: "#123E35",
  heroText: "#FFFEFB",
  heroLabel: "#FFFEFB",
  heroEdge: "transparent",
  logoTile: "transparent",
};

export type Palette = typeof light;

const dark: Palette = {
  limestone: "#111111",
  porcelain: "#1C1C1C",
  raised: "#252525",
  sidebar: "#151515",
  emerald: "#75B899",
  emeraldLight: "#75B899",
  ink: "#F2F2F2",
  secondary: "#ACACAC",
  jade: "#18382B",
  selected: "#2C2C2C",
  selectedText: "#B4DCC6",
  edge: "#363636",
  controlEdge: "#707070",
  muted: "#252525",
  warning: "#CBB27E",
  warningSurface: "#302A1E",
  danger: "#D79C93",
  sage: "#92AB9B",
  sageLight: "#92AB9B",
  reserveSecondary: "#92AB9B",
  reserveTertiary: "#B9A881",
  dimmer: "rgba(0, 0, 0, 0.45)",
  dialogEdge: "#363636",
  onAccent: "#0E2219",
  primaryEdge: "#0E2219",
  axis: "#707070",
  shadow: "#000000",
  heroStart: "#143C30",
  heroMid: "#184735",
  heroEnd: "#1A503D",
  heroText: "#F2F2F2",
  heroLabel: "#B4DCC6",
  heroEdge: "#B9A881",
  logoTile: "#F5F3EE",
};

/** The logo mark keeps its brand colour in both themes (dark mode puts it on an ivory tile). */
export const BRAND = "#123E35";

/**
 * The active palette. It is updated in place by `applyTheme`, so code that reads
 * `colors.x` while rendering always gets the current theme.
 */
export const colors: Palette = { ...light };

let current: ThemeName = "light";
let version = 0;

export function applyTheme(name: ThemeName) {
  if (name !== current) {
    current = name;
    version += 1;
    Object.assign(colors, name === "dark" ? dark : light);
  }
  // Web: native scrollbars and form controls follow the theme, and overscroll shows the page colour.
  if (typeof document !== "undefined") {
    document.documentElement.style.colorScheme = name;
    document.body.style.backgroundColor = colors.limestone;
  }
}

export const isDark = () => current === "dark";

/**
 * Builds a style sheet (or any colour-dependent object) lazily and rebuilds it after the
 * theme changes. Use it instead of a module-level `StyleSheet.create` whenever the styles
 * read `colors`, which would otherwise keep the colours from when the file loaded.
 */
export function themed<T extends object>(build: () => T): T {
  let cache: T | null = null;
  let builtFor = -1;
  const latest = (): T => {
    if (!cache || builtFor !== version) {
      cache = build();
      builtFor = version;
    }
    return cache;
  };
  return new Proxy({} as T, {
    get: (_target, key) => Reflect.get(latest(), key),
    has: (_target, key) => Reflect.has(latest(), key),
    ownKeys: () => Reflect.ownKeys(latest()),
    getOwnPropertyDescriptor: (_target, key) => {
      const descriptor = Reflect.getOwnPropertyDescriptor(latest(), key);
      return descriptor && { ...descriptor, configurable: true };
    },
  });
}

export const radius = { field: 12, card: 28, dialog: 30, pill: 8, nav: 14 };

export const fonts = {
  regular: "Inter_400Regular",
  medium: "Inter_500Medium",
  semibold: "Inter_600SemiBold",
};

export const type = {
  mainAmount: { fontFamily: fonts.semibold, fontSize: 44, lineHeight: 53 },
  screenHeading: { fontFamily: fonts.semibold, fontSize: 32, lineHeight: 38 },
  metric: { fontFamily: fonts.semibold, fontSize: 32, lineHeight: 40 },
  amount: { fontFamily: fonts.semibold, fontSize: 28, lineHeight: 36 },
  panelHeading: { fontFamily: fonts.semibold, fontSize: 19, lineHeight: 26 },
  title: { fontFamily: fonts.semibold, fontSize: 18, lineHeight: 25 },
  lead: { fontFamily: fonts.regular, fontSize: 15, lineHeight: 23 },
  body: { fontFamily: fonts.regular, fontSize: 14, lineHeight: 21 },
  label: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19 },
  caption: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 18 },
  small: { fontFamily: fonts.regular, fontSize: 11, lineHeight: 16 },
} satisfies Record<string, TextStyle>;

// Web-only: text inputs sit inside a styled field, so drop the browser's own focus ring.
export const noFocusRing = { outlineStyle: "none" } as unknown as TextStyle;

export const cardShadow = themed(() =>
  isDark()
    ? { shadowColor: colors.shadow, shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.18, shadowRadius: 14 }
    : { shadowColor: colors.shadow, shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.024, shadowRadius: 28 },
);
