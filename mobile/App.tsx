import { useState } from "react";
import { SafeAreaView, Text, TextInput, Pressable, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { supabase } from "./src/supabase";

function normalizePhone(value: string) {
  const digits = value.replace(/\D/g, "");
  if (digits.startsWith("234") && digits.length === 13) return "+" + digits;
  if (digits.startsWith("0") && digits.length === 11) return "+234" + digits.slice(1);
  if (digits.length === 10) return "+234" + digits;
  throw new Error("Enter a valid Nigerian phone number");
}

export default function App() {
  const [phone, setPhone] = useState("");
  const [token, setToken] = useState("");
  const [stage, setStage] = useState<"phone" | "otp">("phone");
  const [message, setMessage] = useState("");

  async function sendOtp() {
    try {
      const normalized = normalizePhone(phone);
      const { error } = await supabase.auth.signInWithOtp({ phone: normalized });
      if (error) throw error;
      setPhone(normalized);
      setStage("otp");
      setMessage("OTP sent.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not send OTP");
    }
  }

  async function verifyOtp() {
    const { data, error } = await supabase.auth.verifyOtp({ phone, token, type: "sms" });
    if (error || !data.session) {
      setMessage("Invalid or expired OTP.");
      return;
    }
    await AsyncStorage.setItem("medinaija:last-auth", new Date().toISOString());
    setMessage("Signed in. The next screen will reuse the web onboarding API and cache the last 30 days locally.");
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#FDF6EC", padding: 24 }}>
      <StatusBar style="dark" />
      <Text style={{ fontSize: 30, fontWeight: "700", color: "#043B2B", marginTop: 40 }}>MediNaija</Text>
      <Text style={{ marginTop: 8, color: "#496158" }}>Your chronic care companion.</Text>

      <View style={{ marginTop: 36, gap: 12 }}>
        <TextInput
          value={stage === "phone" ? phone : token}
          onChangeText={stage === "phone" ? setPhone : setToken}
          placeholder={stage === "phone" ? "0803 123 4567" : "6-digit OTP"}
          keyboardType="phone-pad"
          style={{ height: 52, backgroundColor: "white", borderRadius: 14, paddingHorizontal: 16 }}
        />
        <Pressable
          onPress={stage === "phone" ? sendOtp : verifyOtp}
          style={{ minHeight: 52, borderRadius: 14, backgroundColor: "#0B6E4F", alignItems: "center", justifyContent: "center" }}
        >
          <Text style={{ color: "white", fontWeight: "700" }}>{stage === "phone" ? "Send OTP" : "Verify OTP"}</Text>
        </Pressable>
      </View>

      {message ? <Text style={{ marginTop: 16, color: "#043B2B" }}>{message}</Text> : null}
    </SafeAreaView>
  );
}
