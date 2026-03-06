# Feature Research

**Domain:** Android Router Management / Network Security Monitoring App
**Researched:** 2026-03-06
**Confidence:** HIGH (well-established domain with mature competitors: UniFi, Nighthawk, Firewalla, TP-Link Tether, ASUS Router)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist in any router management mobile app. Missing these = app feels like a broken web wrapper.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Dashboard / Overview Screen | Every competitor has a single-glance network status screen. Users open the app wanting to see "is everything OK?" in 2 seconds. | MEDIUM | Show: connection status, bandwidth gauge, active device count, DNS block count, threat count. Map 1:1 from web dashboard widgets but optimize for vertical scroll. |
| Device List + Detail | Core function. Users want to see who's on their network, what they're doing, and block/manage them. | MEDIUM | List: device name, IP, MAC, status indicator, current bandwidth. Detail: traffic history, DNS queries, profile assignment, block toggle. |
| Push Notifications (FCM) | Mobile's #1 advantage over web. Users expect alerts without opening the app: new device joined, DDoS detected, device blocked, VPN status change. | HIGH | Requires backend FCM integration (new endpoint for token registration, notification dispatch service). This is the primary reason to have a native app. |
| Biometric Authentication | Standard security practice for admin/management apps. No one wants to type JWT credentials on a phone. | LOW | Android BiometricPrompt API. Store JWT in EncryptedSharedPreferences, unlock with fingerprint/face. |
| Pull-to-Refresh | Mobile UI convention. Users expect to swipe down to refresh data on every screen. | LOW | Standard Compose pattern with SwipeRefresh. |
| Real-time Data Updates | Web uses WebSocket for live bandwidth/DNS data. Mobile must match this — stale data on a monitoring app is unacceptable. | MEDIUM | Use OkHttp WebSocket client or SSE. Same ws:// endpoint as web frontend. |
| DNS Blocking Toggle (Quick On/Off) | Users frequently need to temporarily disable filtering (e.g., a blocked site they actually need). Must be one tap. | LOW | Single API call to toggle. Can also be a Quick Settings Tile (see Differentiators). |
| Device Blocking (Pause Internet) | Nighthawk, UniFi, Firewalla all have "pause device" as a primary action. Parents use this constantly. | LOW | Already in backend API. One-tap block/unblock per device. |
| Profile Management (View + Assign) | Content filtering profiles are a core TonbilAiOS feature. Users need to assign profiles to devices from mobile. | LOW | List profiles, assign to device. Backend API exists. |
| Remote Access (WAN) | Managing router only from local network defeats the purpose of a mobile app. Must work via wall.tonbilx.com. | LOW | Already available via HTTPS. App needs base URL configuration: auto-detect local (192.168.1.2) vs remote (wall.tonbilx.com). |
| Dark Theme | The web UI is cyberpunk dark theme. A light-themed Android app would feel disconnected. Also, AMOLED screens benefit from dark UI. | LOW | Jetpack Compose theming. Define color palette matching web neon-cyan/magenta/green scheme. |
| Connection Status Indicator | Users need to see at a glance: is the router reachable? Is internet working? Is VPN active? | LOW | Persistent header or status bar. Ping /api/v1/dashboard/summary on interval. |
| Settings Screen (Server URL, Auth) | Users need to configure server address, manage login, clear cache, etc. | LOW | Standard settings pattern. |

### Differentiators (Competitive Advantage)

Features that set TonbilAiOS apart from generic router apps. Most competitors are vendor-locked (Nighthawk = NETGEAR only, Tether = TP-Link only). TonbilAiOS is a custom AI-powered system.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Home Screen Widget (Glance) | See bandwidth, device count, threat status WITHOUT opening the app. None of the major router apps do this well. OpManager recently added it as a premium feature. | MEDIUM | Jetpack Glance (Compose-based widget API). Show: up/down bandwidth, active devices, last alert. Update every 30-60 seconds via WorkManager. |
| Quick Settings Tile | Toggle DNS filtering or pause all internet from the Android notification shade. Extremely fast access. | LOW | Android TileService API (API 24+). Two tiles: "DNS Filtering" toggle and "Block All Devices" toggle. |
| AI Chat (Mobile) | No competitor has an AI assistant for network management on mobile. Users can ask "why is my internet slow?" or "block YouTube for kids" in natural language. | MEDIUM | Reuse existing /api/v1/chat endpoint. Standard chat UI with Compose. Telegram intents already handle 16 commands — same backend. |
| Per-Device Traffic Visualization | Firewalla excels here. Show per-device bandwidth usage over time with charts, top domains visited, app detection. Most router apps show basic lists only. | MEDIUM | Use existing /flows/ endpoints. Recharts equivalent: Vico or MPAndroidChart for Compose. |
| Notification Categories + Channels | Android notification channels let users fine-tune which alerts they get: security (high priority), new device (medium), bandwidth (low). | LOW | Define channels: Security Alerts, Device Events, Traffic Alerts, System Status. FCM topics per category. |
| Live Traffic Monitor (Floating) | Picture-in-Picture or floating overlay showing real-time bandwidth. Unique to this app. | HIGH | Android PiP mode or SYSTEM_ALERT_WINDOW permission. Niche but impressive for power users. Defer to v2. |
| Threat Map (Mobile) | DDoS attack world map on mobile. Visually striking, reinforces the "security" value prop. | MEDIUM | Simplified SVG or Canvas-based map. Existing web component can guide design, but must be touch-optimized. |
| Auto-Discovery (Local/Remote) | App automatically detects if on local network (use 192.168.1.2) or remote (use wall.tonbilx.com). No manual URL switching. | LOW | Check if 192.168.1.2 responds on port 8000 with timeout. Fallback to wall.tonbilx.com. Cache result with TTL. |
| Shortcut Actions (App Shortcuts) | Long-press app icon to see: "Block a Device", "Check Status", "Open Chat". Android static shortcuts. | LOW | AndroidManifest shortcut definitions. 3-4 shortcuts max. |
| WiFi AP Management | Control the Pi's WiFi access point (hostapd) from mobile. Change SSID, password, channel, enable/disable. | LOW | Backend API exists. Standard form UI. |
| Haptic Feedback on Critical Alerts | Phone vibrates with distinct pattern for security alerts vs info. Subtle but professional. | LOW | Android VibrationEffect API. Different patterns for threat vs info. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Offline Mode / Local Cache | "I want to see data when router is down" | If router is down, cached data is stale and misleading. Router management is inherently online. Caching state creates sync conflicts when reconnecting. | Show clear "Router Unreachable" screen with last-known status timestamp. No fake data. |
| Full Config Backup/Restore from Mobile | "I want to backup my entire router config from my phone" | Config includes nftables rules, sysctl, dnsmasq, hostapd — touching these from mobile is dangerous. One wrong restore bricks the network. | View-only config summary on mobile. Full backup/restore stays in web UI or SSH. |
| Direct SSH Terminal in App | "I want a terminal to my Pi from the app" | Security nightmare. SSH credentials in a mobile app, fat-finger risk on a phone keyboard for root commands. Scope creep into general server management. | AI Chat handles common commands via structured intents. For SSH, use dedicated apps (JuiceSSH, Termius). |
| Multi-Router Management | "I have multiple routers/sites" | Adds massive complexity: site switching, per-site auth, per-site notifications. TonbilAiOS is a single-Pi deployment. | Single router. If multi-site needed in future, it's a separate milestone. |
| Bandwidth Speed Test from App | "Test my internet speed from the app" | The app tests phone-to-router speed, NOT internet speed. Misleading results. Also, running iperf from mobile drains battery. | Show bandwidth data from the router's perspective (already collected by bandwidth_monitor). Link to Speedtest app for phone-side testing. |
| Custom Theme Editor | "I want to pick my own colors" | Massive UI effort for minimal value. Cyberpunk theme IS the brand. Custom themes create untested color combinations and visual bugs. | Single cyberpunk dark theme. Maybe offer "dim" variant for AMOLED. |
| Tablet-Optimized Layout | "I want a tablet version" | Target device is Samsung S24 Ultra. Tablet layout doubles UI work for near-zero user base. | Responsive Compose layouts that look acceptable on tablets but optimize for phone. |
| Real-time Video/Camera Feed | "Show me a camera feed of my router room" | Completely out of scope. This is network management, not home security. | Not applicable. |

---

## Feature Dependencies

```
[Biometric Auth]
    └──requires──> [JWT Auth + EncryptedSharedPreferences]
                       └──requires──> [API Client (Retrofit/Ktor)]

[Push Notifications (FCM)]
    └──requires──> [Backend FCM Token Endpoint (NEW)]
    └──requires──> [Backend Notification Dispatch Service (NEW)]
    └──requires──> [Android Notification Channels]

[Home Screen Widget]
    └──requires──> [API Client]
    └──requires──> [WorkManager (background refresh)]
    └──enhances──> [Dashboard Screen]

[Quick Settings Tile]
    └──requires──> [API Client]
    └──requires──> [Biometric Auth] (should verify before toggling security features)

[Live Traffic Monitor]
    └──requires──> [WebSocket Client]
    └──requires──> [Dashboard Screen]

[AI Chat (Mobile)]
    └──requires──> [API Client]
    └──independent of──> most other features

[Device Blocking]
    └──requires──> [Device List Screen]
    └──requires──> [API Client]

[Profile Assignment]
    └──requires──> [Device Detail Screen]
    └──requires──> [Profile List (API)]

[Auto-Discovery]
    └──enhances──> [API Client]
    └──should exist before──> [All screens]

[Notification Categories]
    └──requires──> [Push Notifications (FCM)]
    └──enhances──> [All alert-generating features]

[Per-Device Traffic Viz]
    └──requires──> [Device Detail Screen]
    └──requires──> [Charting Library]
```

### Dependency Notes

- **FCM requires backend changes:** Two new endpoints needed: POST /api/v1/notifications/register-device (stores FCM token) and internal dispatch service that sends FCM messages when events occur (new device, DDoS alert, etc.). This is the highest-effort backend change.
- **Biometric Auth requires EncryptedSharedPreferences:** JWT token must be stored encrypted. BiometricPrompt gates access to the decryption key. Standard Android security pattern.
- **Widget requires WorkManager:** Widgets cannot maintain persistent connections. Must use periodic WorkManager tasks to fetch data and update widget. Battery optimization may throttle updates.
- **Quick Settings Tile should require biometric:** Toggling DNS filtering from the notification shade is powerful but dangerous. Should prompt biometric before executing security-sensitive actions.

---

## MVP Definition

### Launch With (v1)

Minimum viable product — core monitoring and management from Android.

- [ ] **API Client + Auth (JWT)** — Foundation for everything
- [ ] **Biometric Authentication** — Security requirement for admin app
- [ ] **Auto-Discovery (local/remote)** — Seamless connection to router
- [ ] **Dashboard Screen** — Single-glance network status
- [ ] **Device List + Detail** — See and manage connected devices
- [ ] **Device Blocking (pause internet)** — #1 action users take
- [ ] **DNS Blocking Overview** — See what's being filtered
- [ ] **Profile View + Assignment** — Assign content profiles to devices
- [ ] **Push Notifications (FCM) — basic** — New device, security alert, router offline
- [ ] **Pull-to-Refresh** — Mobile UX essential
- [ ] **Cyberpunk Dark Theme** — Brand consistency
- [ ] **Settings Screen** — Server URL, logout, about

### Add After Validation (v1.x)

Features to add once core is stable.

- [ ] **Real-time WebSocket data** — Live bandwidth updates on dashboard
- [ ] **Home Screen Widget** — Glance at status without opening app
- [ ] **Quick Settings Tile** — Toggle DNS from notification shade
- [ ] **AI Chat** — Natural language network management
- [ ] **Traffic Monitoring (live flows, history)** — Deep traffic visibility
- [ ] **VPN Management** — View/manage WireGuard peers
- [ ] **Firewall Rules** — View/manage firewall rules
- [ ] **WiFi AP Management** — Control hostapd settings
- [ ] **Notification Channels (categorized)** — Fine-grained alert control
- [ ] **App Shortcuts** — Long-press quick actions

### Future Consideration (v2+)

- [ ] **Threat Map (DDoS visualization)** — Visually impressive but not critical
- [ ] **Live Traffic Floating Overlay** — Power user feature, PiP mode
- [ ] **Security Settings Management** — Complex config screens, lower priority
- [ ] **Telegram Integration Settings** — Manage from mobile
- [ ] **Haptic Feedback Patterns** — Polish feature

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| API Client + JWT Auth | HIGH | MEDIUM | P1 |
| Biometric Auth | HIGH | LOW | P1 |
| Auto-Discovery | HIGH | LOW | P1 |
| Dashboard Screen | HIGH | MEDIUM | P1 |
| Device List + Detail | HIGH | MEDIUM | P1 |
| Device Blocking | HIGH | LOW | P1 |
| Push Notifications (FCM) | HIGH | HIGH | P1 |
| DNS Blocking Overview | MEDIUM | LOW | P1 |
| Profile View + Assignment | MEDIUM | LOW | P1 |
| Cyberpunk Theme | MEDIUM | LOW | P1 |
| Pull-to-Refresh | MEDIUM | LOW | P1 |
| Settings Screen | MEDIUM | LOW | P1 |
| WebSocket Live Data | HIGH | MEDIUM | P2 |
| Home Screen Widget | HIGH | MEDIUM | P2 |
| Quick Settings Tile | MEDIUM | LOW | P2 |
| AI Chat Mobile | MEDIUM | MEDIUM | P2 |
| Traffic Monitoring | MEDIUM | MEDIUM | P2 |
| VPN Management | MEDIUM | LOW | P2 |
| Firewall Rules | LOW | MEDIUM | P2 |
| WiFi AP Management | LOW | LOW | P2 |
| Notification Channels | LOW | LOW | P2 |
| App Shortcuts | LOW | LOW | P2 |
| Threat Map | LOW | HIGH | P3 |
| Floating Traffic Overlay | LOW | HIGH | P3 |
| Security Settings | LOW | MEDIUM | P3 |
| Telegram Settings | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add in subsequent releases
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | UniFi | Nighthawk (NETGEAR) | Firewalla | TP-Link Tether | TonbilAiOS (Our Plan) |
|---------|-------|---------------------|-----------|----------------|----------------------|
| Dashboard overview | Full network topology + health score | Simple status + speed | Device-centric with threat score | Basic router status | Cyberpunk-themed glance dashboard with bandwidth gauge |
| Device management | List + block + group | List + pause + parental | Deep per-device analytics + block | List + block | List + block + profile assign + traffic detail |
| Push notifications | Device offline, firmware update, client events | Security alerts, new device | Threat alerts, new device, abnormal activity | Basic alerts | FCM: security, device, traffic, system categories |
| DNS filtering | Basic content filtering (paid add-on) | Smart Parental Controls (paid) | Family Protect + Safe Search + Ad Block | Basic parental | Profile-based category filtering (built-in, free) |
| AI assistant | None | None | None | None | AI Chat with 16+ intents (UNIQUE differentiator) |
| Home widget | None | None | None | None | Bandwidth + device count + last alert |
| Quick Settings | None | None | None | None | DNS toggle + block-all tile |
| VPN management | Single-tap VPN | None | Built-in VPN server/client | None | WireGuard peer management |
| Traffic analysis | Basic client stats | Traffic meter | Deep flow analysis + app detection | Basic | Per-flow tracking with app/service detection |
| Remote access | UniFi Cloud (account required) | Anywhere Access (account) | Remote management | TP-Link Cloud (account) | wall.tonbilx.com (self-hosted, no account) |
| DDoS/Threat monitoring | Basic IDS alerts | Armor (paid subscription) | IDS/IPS built-in | None | DDoS map + threat analysis + DNS fingerprinting |
| Biometric auth | No | No | Yes | No | Yes (fingerprint/face) |
| Vendor lock-in | Ubiquiti hardware only | NETGEAR hardware only | Firewalla hardware only | TP-Link hardware only | Raspberry Pi (open hardware) |

**Key competitive advantages:**
1. **AI Chat** — No competitor has conversational network management
2. **No vendor lock-in** — Runs on standard Raspberry Pi
3. **Self-hosted remote access** — No cloud account, no subscription
4. **Built-in DNS filtering** — No paid add-on (unlike Nighthawk Armor or UniFi)
5. **Home widget + Quick Settings** — Mobile-native features competitors lack

---

## Sources

- [NETGEAR Nighthawk App features](https://www.netgear.com/home/services/nighthawk-app/) (MEDIUM confidence)
- [UniFi App on Google Play](https://play.google.com/store/apps/details?id=com.ubnt.easyunifi) (MEDIUM confidence)
- [Firewalla App features](https://firewalla.com/) (MEDIUM confidence)
- [TP-Link Tether features](https://techdator.net/best-apps-help-control-your-router/) (LOW confidence — third-party review)
- [Android Quick Settings Tile API](https://developer.android.com/develop/ui/views/quicksettings-tiles) (HIGH confidence — official docs)
- [Android BiometricPrompt API](https://developer.android.com/training/sign-in/biometric-auth) (HIGH confidence — official docs, training data)
- [WiFi Widget (Jetpack Glance example)](https://github.com/w2sv/WiFi-Widget) (MEDIUM confidence)
- [OpManager mobile widgets for network monitoring](https://blogs.manageengine.com/itom/opmanager/opmanagers-new-mobile-widgets-redefine-network-monitoring-onthego.html) (MEDIUM confidence)
- [Router alert types for push notifications](https://askanydifference.com/setting-up-email-or-push-alerts-for-router-events/) (LOW confidence)
- [Firebase Cloud Messaging docs](https://firebase.google.com/docs/cloud-messaging/) (HIGH confidence — official docs)
- TonbilAiOS v5 codebase and PROJECT.md (HIGH confidence — direct source)

---

*Feature research for: TonbilAiOS Android App (v2.0 Milestone)*
*Researched: 2026-03-06*
