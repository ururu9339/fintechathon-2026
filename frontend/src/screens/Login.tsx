import { ReactNode, useState } from "react";
import { Pressable, StyleSheet, TextInput, View } from "react-native";
import { Eye, EyeOff, Info, LockKeyhole } from "lucide-react-native";

import { api, Session } from "../api";
import { LogoMark, ThemeToggle } from "../components/Shell";
import { Button, Card, Divider, Row, shared, T } from "../components/ui";
import { colors, fonts, noFocusRing, themed } from "../theme";

// The local demo account created by scripts/seed_demo_business.py.
const DEMO_EMAIL = "demo.owner@example.com";
const DEMO_PASSWORD = "DemoPassword123!";

/** Owner sign-in. There is no Figma frame for it, so it reuses the workspace's tokens and controls. */
export function Login({
  notice,
  onSignedIn,
  onToggleTheme,
}: {
  notice: string | null;
  onSignedIn: (session: Session) => void;
  onToggleTheme: () => void;
}) {
  const [email, setEmail] = useState(DEMO_EMAIL);
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  async function submit() {
    if (busy) return;
    if (!email.trim() || !password) return setFailure("Enter your email and password.");
    setBusy(true);
    setFailure(null);
    try {
      onSignedIn(await api.login(email.trim(), password));
    } catch (error) {
      setFailure((error as Error).message);
      setBusy(false);
    }
  }

  return (
    <View style={styles.page}>
      <View style={styles.toggle}>
        <ThemeToggle onToggle={onToggleTheme} />
      </View>

      <Card style={styles.card} padding={32}>
        <Row gap={10}>
          <LogoMark />
          <View>
            <T v="title">AmanahPay</T>
            <T v="small" c="secondary">
              Treasurer
            </T>
          </View>
        </Row>

        <T style={styles.heading}>Sign in</T>
        <T v="body" c="secondary">
          Owner access to the Bayu Studio treasury workspace.
        </T>

        {notice && (
          <Row gap={10} style={styles.notice}>
            <Info size={16} color={colors.warning} />
            <T v="label" c="warning" style={{ flex: 1 }}>
              {notice}
            </T>
          </Row>
        )}

        <Field label="Email">
          <TextInput
            value={email}
            onChangeText={setEmail}
            onSubmitEditing={submit}
            autoCapitalize="none"
            autoComplete="email"
            keyboardType="email-address"
            placeholder="you@company.com"
            placeholderTextColor={colors.secondary}
            style={styles.input}
          />
        </Field>
        <Field label="Password">
          <TextInput
            value={password}
            onChangeText={setPassword}
            onSubmitEditing={submit}
            secureTextEntry={!showPassword}
            autoCapitalize="none"
            autoComplete="current-password"
            placeholder="Password"
            placeholderTextColor={colors.secondary}
            style={styles.input}
          />
          <Pressable
            onPress={() => setShowPassword(!showPassword)}
            hitSlop={8}
            accessibilityLabel={showPassword ? "Hide password" : "Show password"}
          >
            {showPassword ? (
              <EyeOff size={17} color={colors.secondary} />
            ) : (
              <Eye size={17} color={colors.secondary} />
            )}
          </Pressable>
        </Field>

        {failure && (
          <T v="label" c="danger" style={{ marginTop: 14 }}>
            {failure}
          </T>
        )}

        <View style={{ marginTop: 22 }}>
          <Button label={busy ? "Signing in…" : "Sign in"} icon={LockKeyhole} disabled={busy} onPress={submit} />
        </View>

        <Divider style={{ marginTop: 24 }} />
        <Row gap={8} align="flex-start" style={{ marginTop: 16 }}>
          <Info size={15} color={colors.secondary} style={{ marginTop: 1 }} />
          <View style={{ flex: 1 }}>
            <T v="caption" w="medium" c="secondary">
              Demo account
            </T>
            <T v="caption" c="secondary">
              {DEMO_EMAIL} · password {DEMO_PASSWORD}
            </T>
          </View>
        </Row>
      </Card>

      <T v="caption" c="secondary" style={{ marginTop: 18 }}>
        Demo data · Nothing here moves real money.
      </T>
    </View>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <View style={{ marginTop: 18, gap: 8 }}>
      <T v="caption" c="secondary">
        {label}
      </T>
      <View style={shared.field}>{children}</View>
    </View>
  );
}

const styles = themed(() =>
  StyleSheet.create({
    page: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24, backgroundColor: colors.limestone },
    toggle: { position: "absolute", top: 24, right: 32 },
    card: { width: "100%", maxWidth: 440 },
    heading: { fontFamily: fonts.semibold, fontSize: 26, lineHeight: 32, color: colors.ink, marginTop: 28 },
    notice: {
      marginTop: 16,
      paddingVertical: 12,
      paddingHorizontal: 14,
      borderRadius: 14,
      backgroundColor: colors.warningSurface,
    },
    input: { flex: 1, height: "100%", fontFamily: fonts.regular, fontSize: 14, color: colors.ink, ...noFocusRing },
  }),
);
