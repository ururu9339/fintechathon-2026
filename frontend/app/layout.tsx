import "./styles.css";

export const metadata = {
  title: "AmanahPay Treasurer",
  description: "A mandate-controlled AI treasurer for SMEs"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
