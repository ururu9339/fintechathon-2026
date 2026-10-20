import { createContext, ReactNode, useContext } from "react";

import type { Scenario, Workspace } from "./api";
import type { Screen } from "./components/Shell";

export type Notice = { message: string; tone: "success" | "info" };

/** Optional deep-link state, e.g. opening Cash flow on a given week and scenario. */
export type NavParams = { scenario?: Scenario; week?: string };

export type AppActions = {
  workspace: Workspace | null;
  /** Bumped after any change so every screen refetches. */
  refreshKey: number;
  refresh: () => void;
  params: NavParams;
  navigate: (screen: Screen, params?: NavParams) => void;
  /** Opens a backend link target: "payments/BP-0084" or "cashflow?scenario=…&week=…". */
  open: (target: string) => void;
  openPayment: (paymentId: string) => void;
  /** Shows a dialog over the whole window (pass null to close). */
  present: (dialog: ReactNode | null) => void;
  /** Switches to Ask Amanah and sends the question. */
  askAbout: (question: string) => void;
  notify: (message: string, tone?: Notice["tone"]) => void;
};

export const AppContext = createContext<AppActions | null>(null);

export function useApp(): AppActions {
  const value = useContext(AppContext);
  if (!value) throw new Error("useApp must be used inside AppContext");
  return value;
}

export function parseTarget(target: string): { screen: Screen; params: NavParams } {
  const [path, query = ""] = target.split("?");
  const params: NavParams = {};
  for (const pair of query.split("&").filter(Boolean)) {
    const [key, value] = pair.split("=");
    if (key === "scenario") params.scenario = value as Scenario;
    if (key === "week") params.week = value;
  }
  return { screen: path as Screen, params };
}

/** Toast for buttons whose flow isn't built yet, so nothing silently does nothing. */
export const NOT_IN_BUILD = "Not in this build yet. It's planned for the next pass.";
