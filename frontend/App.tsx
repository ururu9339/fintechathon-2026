import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

type ForecastPoint = {
  week: number;
  closing_balance: number;
  lower_bound: number;
  upper_bound: number;
};

const API = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";
const colors = {
  background: "#0e1513",
  card: "#16221e",
  text: "#f2f7f3",
  muted: "#9eb1a8",
  accent: "#b8f36b",
  line: "#2a3a33",
  negative: "#ff896b",
};

export default function App() {
  const [forecast, setForecast] = useState<ForecastPoint[]>([]);
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState("Try the prompt-injection demo below.");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/forecast`)
      .then((response) => response.json())
      .then((data) => setForecast(data.points))
      .catch(() => setReply("Unable to load the forecast. Check the API connection."))
      .finally(() => setLoading(false));
  }, []);

  async function askAgent() {
    const response = await fetch(`${API}/api/agent`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await response.json();
    setReply(data.message);
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.header}>
          <View>
            <Text style={styles.eyebrow}>AMANAH FINTECH</Text>
            <Text style={styles.title}>AmanahPay Treasurer</Text>
            <Text style={styles.muted}>Your cash-flow co-pilot with owner-controlled autonomy.</Text>
          </View>
          <Text style={styles.status}>● Demo environment</Text>
        </View>

        <View style={styles.grid}>
          <View style={[styles.card, styles.hero]}>
            <Text style={styles.eyebrow}>13-WEEK OUTLOOK</Text>
            <Text style={styles.heading}>Know the gap before it arrives.</Text>
            <Text style={styles.muted}>Probabilistic cash-flow signals turn late invoices into an actionable plan.</Text>
            {loading ? (
              <ActivityIndicator color={colors.accent} style={styles.loader} />
            ) : (
              <View style={styles.chart}>
                {forecast.map((point) => (
                  <View style={styles.barWrap} key={point.week}>
                    <View
                      style={[
                        styles.bar,
                        {
                          height: Math.max(12, Math.min(100, Math.abs(point.closing_balance) / 3)),
                          backgroundColor: point.closing_balance < 0 ? colors.negative : colors.accent,
                        },
                      ]}
                    />
                    <Text style={styles.chartLabel}>W{point.week}</Text>
                  </View>
                ))}
              </View>
            )}
          </View>

          <View style={styles.card}>
            <Text style={styles.eyebrow}>ENVELOPES</Text>
            <Text style={styles.heading}>Protected funds</Text>
            <Envelope label="SST & taxes" amount="MYR 5,200" progress={87} />
            <Envelope label="EPF & salaries" amount="MYR 12,000" progress={100} />
            <Envelope label="Suppliers" amount="MYR 6,800" progress={68} />
          </View>
        </View>

        <View style={styles.grid}>
          <View style={styles.card}>
            <Text style={styles.eyebrow}>WHATSAPP SIMULATION</Text>
            <Text style={styles.heading}>Agent safety test</Text>
            <Text style={styles.bubble}>{reply}</Text>
            <TextInput
              value={message}
              onChangeText={setMessage}
              placeholder="Ignore previous instructions..."
              placeholderTextColor={colors.muted}
              style={styles.input}
            />
            <Pressable onPress={askAgent} style={styles.button}>
              <Text style={styles.buttonText}>Send to treasurer</Text>
            </Pressable>
          </View>

          <View style={styles.card}>
            <Text style={styles.eyebrow}>MANDATE STATUS</Text>
            <Text style={styles.heading}>Supplier payments</Text>
            <Approval icon="✓" title="Mandate active" detail="MYR 2,500 per transaction · allowlist enforced" />
            <Approval icon="↗" title="Financing watch" detail="Recommendations appear when a gap is predicted." />
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function Envelope({ label, amount, progress }: { label: string; amount: string; progress: number }) {
  return (
    <View style={styles.envelope}>
      <View style={styles.row}>
        <Text style={styles.muted}>{label}</Text>
        <Text style={styles.amount}>{amount}</Text>
      </View>
      <View style={styles.progress}>
        <View style={[styles.progressFill, { width: `${progress}%` }]} />
      </View>
    </View>
  );
}

function Approval({ icon, title, detail }: { icon: string; title: string; detail: string }) {
  return (
    <View style={styles.approval}>
      <Text style={styles.approvalIcon}>{icon}</Text>
      <View style={styles.approvalText}>
        <Text style={styles.approvalTitle}>{title}</Text>
        <Text style={styles.muted}>{detail}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.background },
  container: { width: "100%", maxWidth: 1180, alignSelf: "center", padding: 24, gap: 18 },
  header: { gap: 18, marginBottom: 24 },
  title: { color: colors.text, fontSize: 42, fontWeight: "800", letterSpacing: -1.5, marginVertical: 10 },
  heading: { color: colors.text, fontSize: 21, fontWeight: "700", marginVertical: 10 },
  eyebrow: { color: colors.accent, fontSize: 11, fontWeight: "800", letterSpacing: 2 },
  status: { color: colors.accent, fontSize: 13 },
  muted: { color: colors.muted, fontSize: 15, lineHeight: 23 },
  grid: { gap: 18 },
  card: { backgroundColor: colors.card, borderColor: colors.line, borderWidth: 1, borderRadius: 18, padding: 24 },
  hero: { minHeight: 330 },
  loader: { marginTop: 80 },
  chart: { height: 150, flexDirection: "row", alignItems: "flex-end", gap: 8, paddingTop: 25, marginTop: 20 },
  barWrap: { flex: 1, height: "100%", alignItems: "center", justifyContent: "flex-end", gap: 8 },
  bar: { width: "100%", minHeight: 10, borderRadius: 5 },
  chartLabel: { color: colors.muted, fontSize: 10 },
  envelope: { marginTop: 22 },
  row: { flexDirection: "row", justifyContent: "space-between", gap: 12 },
  amount: { color: colors.text, fontWeight: "700" },
  progress: { height: 7, backgroundColor: "#26352f", borderRadius: 99, overflow: "hidden", marginTop: 9 },
  progressFill: { height: "100%", backgroundColor: colors.accent, borderRadius: 99 },
  bubble: { color: colors.text, borderColor: colors.line, borderWidth: 1, borderRadius: 12, padding: 14, minHeight: 58, marginTop: 8, lineHeight: 22 },
  input: { color: colors.text, backgroundColor: "#0f1815", borderColor: colors.line, borderWidth: 1, borderRadius: 8, padding: 13, marginVertical: 8 },
  button: { backgroundColor: colors.accent, borderRadius: 8, padding: 13, alignItems: "center" },
  buttonText: { color: "#101810", fontWeight: "800" },
  approval: { flexDirection: "row", gap: 14, alignItems: "center", borderBottomColor: colors.line, borderBottomWidth: 1, paddingVertical: 18 },
  approvalIcon: { color: colors.accent, fontSize: 24 },
  approvalText: { flex: 1, gap: 5 },
  approvalTitle: { color: colors.text, fontWeight: "700" },
});
