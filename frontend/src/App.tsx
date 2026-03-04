// --- Ajan: MUHAFIZ (THE GUARDIAN) ---
// Uygulama koku: React Router ile sayfa yonlendirme
// Login sayfası koruma disinda, diger tum sayfalar AuthGuard ile korunur

import { Routes, Route } from "react-router-dom";
import { MainLayout } from "./components/layout/MainLayout";
import { AuthGuard } from "./components/auth/AuthGuard";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DevicesPage } from "./pages/DevicesPage";
import { ProfilesPage } from "./pages/ProfilesPage";
import { TrafficPage } from "./pages/TrafficPage";
import { InsightsPage } from "./pages/InsightsPage";
import { DnsBlockingPage } from "./pages/DnsBlockingPage";
import { DhcpPage } from "./pages/DhcpPage";
import { FirewallPage } from "./pages/FirewallPage";
import { VpnPage } from "./pages/VpnPage";
import { ChatPage } from "./pages/ChatPage";
import { VpnClientPage } from "./pages/VpnClientPage";
import { TlsPage } from "./pages/TlsPage";
import { ContentCategoriesPage } from "./pages/ContentCategoriesPage";
import DeviceServicesPage from "./pages/DeviceServicesPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SystemLogsPage } from "./pages/SystemLogsPage";
import { SystemTimePage } from "./pages/SystemTimePage";
import { TelegramPage } from "./pages/TelegramPage";
import { IpManagementPage } from "./pages/IpManagementPage";
import { SystemMonitorPage } from "./pages/SystemMonitorPage";
import { AiSettingsPage } from "./pages/AiSettingsPage";
import { DeviceDetailPage } from "./pages/DeviceDetailPage";
import { SystemManagementPage } from "./pages/SystemManagementPage";
import { DdosMapPage } from "./pages/DdosMapPage";
import { WifiPage } from "./pages/WifiPage";

export default function App() {
  return (
    <Routes>
      {/* Login sayfası - koruma disinda (tam ekran) */}
      <Route path="/login" element={<LoginPage />} />

      {/* Korunmus sayfalar - AuthGuard + MainLayout içinde */}
      <Route
        path="/*"
        element={
          <AuthGuard>
            <MainLayout>
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/system-monitor" element={<SystemMonitorPage />} />
                <Route path="/devices" element={<DevicesPage />} />
                <Route path="/devices/:id" element={<DeviceDetailPage />} />
                <Route path="/devices/:deviceId/services" element={<DeviceServicesPage />} />
                <Route path="/profiles" element={<ProfilesPage />} />
                <Route path="/content-categories" element={<ContentCategoriesPage />} />
                <Route path="/dns" element={<DnsBlockingPage />} />
                <Route path="/dhcp" element={<DhcpPage />} />
                <Route path="/wifi" element={<WifiPage />} />
                <Route path="/firewall" element={<FirewallPage />} />
                <Route path="/ddos-map" element={<DdosMapPage />} />
                <Route path="/ip-management" element={<IpManagementPage />} />
                <Route path="/vpn" element={<VpnPage />} />
                <Route path="/vpn-client" element={<VpnClientPage />} />
                <Route path="/tls" element={<TlsPage />} />
                <Route path="/chat" element={<ChatPage />} />
                <Route path="/traffic" element={<TrafficPage />} />
                <Route path="/insights" element={<InsightsPage />} />
                <Route path="/system-logs" element={<SystemLogsPage />} />
                <Route path="/system-time" element={<SystemTimePage />} />
                <Route path="/telegram" element={<TelegramPage />} />
                <Route path="/ai-settings" element={<AiSettingsPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="/system-management" element={<SystemManagementPage />} />
              </Routes>
            </MainLayout>
          </AuthGuard>
        }
      />
    </Routes>
  );
}
