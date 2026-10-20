import { ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ScrollView, StyleSheet, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import { Inter_400Regular, Inter_500Medium, Inter_600SemiBold, useFonts } from "@expo-google-fonts/inter";
import { CircleCheck, Info } from "lucide-react-native";

import { api, ApiError, onSessionEnded, Session, setRefreshToken, setToken } from "./src/api";
import { AppActions, AppContext, NavParams, Notice, parseTarget } from "./src/AppContext";
import { ReviewPaymentDialog } from "./src/components/ReviewPaymentDialog";
import { Screen, Sidebar, TopBar } from "./src/components/Shell";
import { Row, T } from "./src/components/ui";
import { AskAmanah, Exchange } from "./src/screens/AskAmanah";
import { CashFlow } from "./src/screens/CashFlow";
import { Financing } from "./src/screens/Financing";
import { Login } from "./src/screens/Login";
import { Overview } from "./src/screens/Overview";
import { PaymentRules } from "./src/screens/PaymentRules";
import { Payments } from "./src/screens/Payments";
import { Reserves } from "./src/screens/Reserves";
import { storage } from "./src/storage";
import { applyTheme, colors, isDark, ThemeName, themed } from "./src/theme";
import { useResource } from "./src/useResource";

const THEME_KEY = "amanahpay.theme";
const SESSION_KEY = "amanahpay.session";

/** The saved choice, otherwise the system setting. */
function initialTheme(): ThemeName {
  const saved = storage.get(THEME_KEY);
  if (saved === "light" || saved === "dark") return saved;
  const prefersDark = typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  return prefersDark ? "dark" : "light";
}

function savedSession(): Session | null {
  try {
    const session = JSON.parse(storage.get(SESSION_KEY) ?? "null") as Session | null;
    return session && new Date(session.expires_at) > new Date() ? session : null;
  } catch {
    return null;
  }
}

export default function App() {
  const [fontsLoaded] = useFonts({ Inter_400Regular, Inter_500Medium, Inter_600SemiBold });
  const [theme, setTheme] = useState<ThemeName>(() => {
    const name = initialTheme();
    applyTheme(name);
    return name;
  });
  const [session, setSession] = useState<Session | null>(null);
  const [restoring, setRestoring] = useState(true);
  const [signInNotice, setSignInNotice] = useState<string | null>(null);

  // The palette is swapped in place, then this state change re-renders everything with it.
  const toggleTheme = useCallback(() => {
    const next: ThemeName = isDark() ? "light" : "dark";
    applyTheme(next);
    storage.set(THEME_KEY, next);
    setTheme(next);
  }, []);

  const endSession = useCallback((message: string | null) => {
    setToken(null);
    setRefreshToken(null);
    storage.remove(SESSION_KEY);
    setSession(null);
    setSignInNotice(message);
  }, []);

  const signIn = useCallback((next: Session) => {
    setToken(next.token);
    setRefreshToken(next.refresh_token);
    storage.set(SESSION_KEY, JSON.stringify(next));
    setSignInNotice(null);
    setSession(next);
  }, []);

  const signOut = useCallback(() => {
    api
      .logout()
      .catch(() => undefined)
      .finally(() => endSession(null));
  }, [endSession]);

  // Reopen a saved session if the API still accepts it. A rejected token ends the session
  // (via onSessionEnded); if the API is just unreachable, keep it and let the screens retry.
  useEffect(() => {
    onSessionEnded(() => endSession("Your session ended. Sign in again."));
    const saved = savedSession();
    if (!saved) {
      storage.remove(SESSION_KEY);
      setRestoring(false);
      return;
    }
    setToken(saved.token);
    setRefreshToken(saved.refresh_token ?? null);
    api
      .me()
      .then(() => setSession(saved))
      .catch((error) => {
        if (!(error instanceof ApiError && error.status === 401)) setSession(saved);
      })
      .finally(() => setRestoring(false));
    return () => onSessionEnded(null);
  }, [endSession]);

  const statusBar = <StatusBar style={theme === "dark" ? "light" : "dark"} />;
  if (!fontsLoaded || restoring) return <View style={styles.root} />;
  if (!session) {
    return (
      <>
        {statusBar}
        <Login notice={signInNotice} onSignedIn={signIn} onToggleTheme={toggleTheme} />
      </>
    );
  }
  return (
    <>
      {statusBar}
      <Workspace onSignOut={signOut} onToggleTheme={toggleTheme} />
    </>
  );
}

/** The signed-in app: navigation, screens, dialogs and toasts. */
function Workspace({ onSignOut, onToggleTheme }: { onSignOut: () => void; onToggleTheme: () => void }) {
  const [screen, setScreen] = useState<Screen>("overview");
  const [params, setParams] = useState<NavParams>({});
  const [reviewId, setReviewId] = useState<string | null>(null);
  const [overlay, setOverlay] = useState<ReactNode>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [conversation, setConversation] = useState<Exchange[]>([]);
  const noticeTimer = useRef<ReturnType<typeof setTimeout>>();
  const scroll = useRef<ScrollView>(null);

  const workspace = useResource(api.workspace, []).data;
  const pending = useResource(api.payments, [refreshKey]).data?.summary.needs_approval ?? 0;

  const notify = useCallback((message: string, tone: Notice["tone"] = "info") => {
    clearTimeout(noticeTimer.current);
    setNotice({ message, tone });
    noticeTimer.current = setTimeout(() => setNotice(null), 4500);
  }, []);

  const navigate = useCallback((next: Screen, nextParams: NavParams = {}) => {
    setReviewId(null);
    setOverlay(null);
    setScreen(next);
    setParams(nextParams);
    scroll.current?.scrollTo({ y: 0, animated: false });
  }, []);

  const ask = useCallback((question: string) => {
    const id = Date.now();
    setConversation((items) => [...items, { id, question, answer: null, error: null }]);
    const settle = (patch: Partial<Exchange>) =>
      setConversation((items) => items.map((item) => (item.id === id ? { ...item, ...patch } : item)));
    api
      .ask(question)
      .then((answer) => settle({ answer }))
      .catch((error: Error) => settle({ error: error.message }));
  }, []);

  const actions = useMemo<AppActions>(
    () => ({
      workspace,
      refreshKey,
      refresh: () => setRefreshKey((key) => key + 1),
      params,
      navigate,
      open: (target) => {
        if (target.startsWith("payments/")) return setReviewId(target.slice("payments/".length));
        const { screen: next, params: nextParams } = parseTarget(target);
        navigate(next, nextParams);
      },
      openPayment: setReviewId,
      present: setOverlay,
      askAbout: (question) => {
        navigate("ask");
        ask(question);
      },
      notify,
    }),
    [workspace, refreshKey, params, navigate, ask, notify],
  );

  useEffect(() => () => clearTimeout(noticeTimer.current), []);

  return (
    <AppContext.Provider value={actions}>
      <View style={styles.root}>
        <Sidebar
          screen={screen}
          onNavigate={navigate}
          pendingApprovals={pending}
          workspace={workspace}
          onSignOut={onSignOut}
        />
        <ScrollView ref={scroll} style={styles.workspace} contentContainerStyle={styles.workspaceContent}>
          <View style={styles.page}>
            <TopBar workspace={workspace} onToggleTheme={onToggleTheme} />
            {screen === "overview" && <Overview />}
            {screen === "payments" && <Payments />}
            {screen === "rules" && <PaymentRules />}
            {screen === "ask" && <AskAmanah conversation={conversation} onAsk={ask} />}
            {screen === "cashflow" && <CashFlow />}
            {screen === "reserves" && <Reserves />}
            {screen === "financing" && <Financing />}
          </View>
        </ScrollView>

        {overlay}
        {reviewId && <ReviewPaymentDialog paymentId={reviewId} onClose={() => setReviewId(null)} />}

        {notice && (
          <View style={styles.toastWrap} pointerEvents="none">
            <Row gap={10} style={[styles.toast, notice.tone === "success" ? styles.toastSuccess : styles.toastInfo]}>
              {notice.tone === "success" ? (
                <CircleCheck size={17} color={colors.emerald} />
              ) : (
                <Info size={17} color={colors.secondary} />
              )}
              <T v="body" w="medium">
                {notice.message}
              </T>
            </Row>
          </View>
        )}
      </View>
    </AppContext.Provider>
  );
}

const styles = themed(() =>
  StyleSheet.create({
    root: { flex: 1, flexDirection: "row", backgroundColor: colors.limestone },
    workspace: { flex: 1 },
    workspaceContent: { padding: 32 },
    page: { width: "100%", maxWidth: 1280, alignSelf: "center" },
    toastWrap: { position: "absolute", left: 224, right: 0, bottom: 28, alignItems: "center", zIndex: 200 },
    toast: {
      paddingVertical: 12,
      paddingHorizontal: 18,
      borderRadius: 14,
      borderWidth: 1,
      shadowColor: colors.shadow,
      shadowOffset: { width: 0, height: 10 },
      shadowOpacity: 0.12,
      shadowRadius: 28,
    },
    toastSuccess: { backgroundColor: colors.jade, borderColor: colors.jade },
    toastInfo: { backgroundColor: colors.raised, borderColor: colors.edge },
  }),
);
