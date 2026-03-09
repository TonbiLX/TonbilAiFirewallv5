// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// API model TypeScript arayuzleri

export interface Profile {
  id: number;
  name: string;
  profile_type: "child" | "adult" | "guest";
  allowed_hours: { start: string; end: string } | null;
  content_filters: string[] | null;
  bandwidth_limit_mbps: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface Device {
  id: number;
  mac_address: string;
  ip_address: string | null;
  hostname: string | null;
  manufacturer: string | null;
  profile_id: number | null;
  is_blocked: boolean;
  is_online: boolean;
  first_seen: string | null;
  last_seen: string | null;
  total_online_seconds: number;
  last_online_start: string | null;
  // DNS Fingerprinting
  detected_os: string | null;
  device_type: string | null;
  // Bant genişliği siniri
  bandwidth_limit_mbps: number | null;
  // IPTV cihaz modu
  is_iptv: boolean;
  // Risk Degerlendirme
  risk_score: number;
  risk_level: "safe" | "suspicious" | "dangerous";
  last_risk_assessment: string | null;
}

export interface TrafficLog {
  id: number;
  timestamp: string | null;
  device_id: number;
  hostname: string | null;
  ip_address: string | null;
  mac_address: string | null;
  destination_domain: string | null;
  category: string | null;
  bytes_sent: number;
  bytes_received: number;
  protocol: string | null;
}

export interface AiInsight {
  id: number;
  timestamp: string | null;
  severity: "info" | "warning" | "critical";
  message: string;
  suggested_action: string | null;
  related_device_id: number | null;
  category: string | null;
  is_dismissed: boolean;
}

export interface ThreatStats {
  blocked_ip_count: number;
  total_external_blocked: number;
  total_auto_blocks: number;
  total_suspicious: number;
  last_threat_time: string | null;
}

export interface BlockedIp {
  ip: string;
  reason: string;
  remaining_seconds: number;
}

export interface DashboardSummary {
  devices: {
    total: number;
    online: number;
    blocked: number;
  };
  dns: {
    total_queries_24h: number;
    blocked_queries_24h: number;
    block_percentage: number;
    active_blocklists: number;
    total_blocked_domains: number;
  };
  vpn?: {
    enabled: boolean;
    total_peers: number;
    connected_peers: number;
    total_rx: number;
    total_tx: number;
  };
  top_clients: Array<{ client_ip: string; query_count: number }>;
  top_queried_domains: Array<{ domain: string; count: number }>;
  top_blocked_domains: Array<{ domain: string; count: number }>;
}

// --- Faz 2: DNS Engelleme ---

export interface Blocklist {
  id: number;
  name: string;
  url: string;
  description: string | null;
  format: "hosts" | "domain_list" | "adblock";
  enabled: boolean;
  domain_count: number;
  last_updated: string | null;
  last_error: string | null;
  content_hash: string | null;
  update_frequency_hours: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface BlocklistRefreshResult {
  blocklist_id: number;
  name: string;
  previous_domain_count: number;
  new_domain_count: number;
  added_count: number;
  removed_count: number;
  status: "updated" | "unchanged" | "error";
  error_message: string | null;
}

export interface BulkRefreshResult {
  total_blocklists: number;
  updated_count: number;
  unchanged_count: number;
  failed_count: number;
  total_domains_before: number;
  total_domains_after: number;
  new_domains_added: number;
  results: BlocklistRefreshResult[];
}

export interface DnsRule {
  id: number;
  domain: string;
  rule_type: "block" | "allow";
  reason: string | null;
  profile_id: number | null;
  added_by: string;
  created_at: string | null;
}

export interface DnsQueryLog {
  id: number;
  timestamp: string | null;
  device_id: number | null;
  client_ip: string | null;
  domain: string;
  query_type: string;
  blocked: boolean;
  block_reason: string | null;
  upstream_response_ms: number | null;
  answer_ip: string | null;
  source_type: string | null;  // INTERNAL | EXTERNAL | DOT
}

export interface DnsStats {
  total_queries_24h: number;
  blocked_queries_24h: number;
  block_percentage: number;
  total_blocklist_domains: number;
  active_blocklists: number;
  top_blocked_domains: Array<{ domain: string; count: number }>;
  top_queried_domains: Array<{ domain: string; count: number }>;
  top_clients: Array<{ device_id: number; client_ip: string; query_count: number }>;
  external_queries_24h: number;
}

export interface DomainLookup {
  domain: string;
  is_blocked: boolean;
  custom_rule: { type: string; reason: string } | null;
  recent_query_count: number;
}

// --- Cihaz Özel DNS Kuralları ---

export interface DeviceCustomRule {
  id: number;
  device_id: number;
  device_hostname: string | null;
  device_ip: string | null;
  domain: string;
  rule_type: "block" | "allow";
  reason: string | null;
  added_by: string;
  created_at: string | null;
}

// --- Servis Engelleme (AdGuard Home tarzi) ---

export interface BlockedService {
  id: number;
  service_id: string;
  name: string;
  group_name: string;
  icon_svg: string | null;
  rules: string[];
  domain_count: number;
  enabled: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface DeviceBlockedService {
  service_id: string;
  name: string;
  group_name: string;
  icon_svg: string | null;
  blocked: boolean;
  schedule: Record<string, { start: string; end: string }> | null;
}

export interface ServiceGroup {
  group: string;
  count: number;
}

// --- Faz 2: DHCP Sunucu ---

export interface DhcpPool {
  id: number;
  name: string;
  subnet: string;
  netmask: string;
  range_start: string;
  range_end: string;
  gateway: string;
  dns_servers: string[];
  lease_time_seconds: number;
  enabled: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface DhcpLease {
  id: number;
  mac_address: string;
  ip_address: string;
  hostname: string | null;
  lease_start: string | null;
  lease_end: string | null;
  is_static: boolean;
  device_id: number | null;
  pool_id: number | null;
}

export interface DhcpStats {
  total_pools: number;
  active_pools: number;
  total_ips: number;
  assigned_ips: number;
  available_ips: number;
  static_leases: number;
  dynamic_leases: number;
}

// --- Faz 2: Firewall (Güvenlik Duvarı) ---

export interface FirewallRule {
  id: number;
  name: string;
  description?: string;
  direction: 'inbound' | 'outbound' | 'forward';
  protocol: 'tcp' | 'udp' | 'both' | 'icmp' | 'all';
  port?: number;
  port_end?: number;
  source_ip?: string;
  dest_ip?: string;
  action: 'accept' | 'drop' | 'reject';
  enabled: boolean;
  priority: number;
  log_packets: boolean;
  hit_count: number;
  created_at?: string;
  updated_at?: string;
}

export interface FirewallStats {
  total_rules: number;
  active_rules: number;
  inbound_rules: number;
  outbound_rules: number;
  blocked_packets_24h: number;
  open_ports: number[];
  rule_hit_counts?: Record<number, { packets: number; bytes: number }>;
  active_connections?: number;
  max_connections?: number;
}

// --- Trafik & Bandwidth ---

export interface DeviceTrafficSummary {
  device_id: number;
  hostname: string | null;
  mac_address: string | null;
  ip_address: string | null;
  is_online: boolean;
  upload_bytes: number;
  download_bytes: number;
  connection_count: number;
  upload_bps: number;
  download_bps: number;
}

export interface ActiveConnection {
  protocol: string;
  src_ip: string;
  src_port: number;
  dst_ip: string;
  dst_port: number;
  dst_domain: string | null;
  bytes_sent: number;
  bytes_received: number;
  state: string;
}

export interface DeviceTrafficHistory {
  timestamp: string;
  upload_bps: number;
  download_bps: number;
  upload_bytes?: number;
  download_bytes?: number;
  source?: string;
}

export interface TopDestination {
  domain: string;
  category: string | null;
  bytes_sent: number;
  bytes_received: number;
  total_bytes: number;
  connection_count: number;
}

export interface DeviceBandwidth {
  upload_bps: number;
  download_bps: number;
  upload_total: number;
  download_total: number;
}

export interface BandwidthData {
  total_upload_bps: number;
  total_download_bps: number;
  devices: Record<string, DeviceBandwidth>;
}

export interface RealtimeWsData {
  type: string;
  device_count: number;
  devices: Array<{
    id: number;
    mac: string;
    ip: string;
    hostname: string;
    manufacturer: string;
    is_online: boolean;
  }>;
  dns: {
    total_queries_24h: number;
    blocked_queries_24h: number;
    block_percentage: number;
    queries_per_min: number;
  };
  bandwidth: BandwidthData;
  vpn?: {
    enabled: boolean;
    connected_peers: number;
    total_peers: number;
  };
}

export interface PortScanResult {
  port: number;
  protocol: string;
  state: 'open' | 'closed' | 'filtered';
  service?: string;
}

// --- Faz 2: VPN (WireGuard) ---

export interface VpnPeer {
  name: string;
  public_key?: string;
  allowed_ips: string;
  endpoint?: string;
  dns_servers?: string;
  enabled: boolean;
  has_qr: boolean;
  is_connected: boolean;
  last_handshake?: string;
  transfer_rx: number;
  transfer_tx: number;
}

export interface VpnConfig {
  interface_name: string;
  listen_port: number;
  server_public_key?: string;
  server_address: string;
  dns_server: string;
  mtu: number;
  enabled: boolean;
}

export interface VpnStats {
  server_enabled: boolean;
  server_public_key?: string;
  listen_port: number;
  total_peers: number;
  connected_peers: number;
  total_transfer_rx: number;
  total_transfer_tx: number;
}

export interface VpnPeerConfig {
  peer_name: string;
  config_text: string;
  qr_data?: string;
}

// --- Sistem Logları ---

export interface SystemLogEntry {
  id: number;
  timestamp: string | null;
  client_ip: string | null;
  dest_ip: string | null;
  mac_address: string | null;
  hostname: string | null;
  domain: string;
  query_type: string;
  action: string; // query / block / allow
  category: string; // dns / ai / security
  severity: string; // info / warning / critical
  answer_ip: string | null;
  block_reason: string | null;
  upstream_response_ms: number | null;
  bytes_total: number | null;
  source_type: string;
}

export interface SystemLogListResponse {
  items: SystemLogEntry[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface SystemLogSummary {
  total_logs_30d: number;
  dns_queries_30d: number;
  blocked_30d: number;
  ai_insights_30d: number;
  critical_30d: number;
  traffic_logs_30d: number;
}

// --- Saat & Tarih ---

export interface SystemTimeStatus {
  current_time: string;
  timezone: string;
  ntp_enabled: boolean;
  ntp_server: string | null;
  ntp_synced: boolean;
  utc_offset: string | null;
}

// --- Telegram Bot ---

export interface TelegramConfig {
  id: number;
  bot_token_masked: string | null;
  chat_ids: string | null;
  enabled: boolean;
  notify_new_device: boolean;
  notify_blocked_ip: boolean;
  notify_trusted_ip_threat: boolean;
  notify_ai_insight: boolean;
  created_at: string | null;
  updated_at: string | null;
}

// --- Cihaz Bağlantı Geçmişi ---

export interface DeviceConnectionLog {
  id: number;
  device_id: number;
  event_type: "connect" | "disconnect";
  ip_address: string | null;
  session_duration_seconds: number | null;
  timestamp: string | null;
}

// --- IP Yönetimi ---

export interface TrustedIp {
  id: number;
  ip_address: string;
  description: string | null;
  created_at: string | null;
}

export interface ManagedBlockedIp {
  id: number | null;
  ip_address: string;
  reason: string | null;
  blocked_at: string | null;
  expires_at: string | null;
  is_manual: boolean;
  source: string;
  remaining_seconds: number | null;
}

export interface IpManagementStats {
  trusted_ip_count: number;
  blocked_ip_count: number;
  manual_block_count: number;
  auto_block_count: number;
}

// --- Sistem Monitörü ---

export interface SystemHardwareInfo {
  model: string;
  cpu_model: string;
  cpu_cores: number;
  cpu_max_freq_mhz: number;
  ram_total_mb: number;
  disk_total_gb: number;
  os_info: string;
}

export interface CpuMetrics {
  usage_percent: number;
  temperature_c: number;
  frequency_mhz: number;
}

export interface MemoryMetrics {
  used_mb: number;
  total_mb: number;
  available_mb: number;
  usage_percent: number;
}

export interface DiskMetrics {
  used_gb: number;
  total_gb: number;
  free_gb: number;
  usage_percent: number;
}

export interface NetworkInterfaceMetrics {
  interface: string;
  rx_bytes: number;
  tx_bytes: number;
  rx_rate_kbps: number;
  tx_rate_kbps: number;
}

export interface FanMetrics {
  rpm: number;
  pwm: number;
  pwm_percent: number;
}

export interface SystemMetricsSnapshot {
  timestamp: string;
  cpu: CpuMetrics;
  memory: MemoryMetrics;
  disk: DiskMetrics;
  fan: FanMetrics;
  network: NetworkInterfaceMetrics[];
  uptime_seconds: number;
}

export interface SystemMetricsHistoryPoint {
  timestamp: string;
  cpu_usage: number;
  cpu_temp: number;
  ram_usage: number;
  net_rx_kbps: number;
  net_tx_kbps: number;
  fan_rpm: number;
}

export interface SystemMetricsResponse {
  current: SystemMetricsSnapshot;
  history: SystemMetricsHistoryPoint[];
}

export interface FanConfig {
  mode: "auto" | "manual";
  manual_pwm: number;
  auto_temp_low: number;
  auto_temp_mid: number;
  auto_temp_high: number;
}

export interface FanConfigUpdate {
  mode?: "auto" | "manual";
  manual_pwm?: number;
  auto_temp_low?: number;
  auto_temp_mid?: number;
  auto_temp_high?: number;
}

// --- Yapay Zeka Ayarları ---

export interface AiConfig {
  id: number;
  provider: string;
  api_key_masked: string | null;
  base_url: string | null;
  model: string | null;
  chat_mode: "tfidf" | "llm" | "hybrid";
  temperature: number;
  max_tokens: number;
  log_analysis_enabled: boolean;
  log_analysis_interval_minutes: number;
  log_analysis_max_logs: number;
  daily_request_limit: number;
  daily_request_count: number;
  custom_system_prompt: string | null;
  enabled: boolean;
  last_test_result: string | null;
  last_test_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface AiProviderInfo {
  id: string;
  name: string;
  description: string;
  requires_api_key: boolean;
  default_base_url: string | null;
  models: AiModelInfo[];
}

export interface AiModelInfo {
  id: string;
  name: string;
  context: number | null;
}

export interface AiTestResponse {
  success: boolean;
  response: string | null;
  latency_ms: number;
  model_used: string | null;
  error: string | null;
}

export interface AiStats {
  daily_request_count: number;
  daily_request_limit: number;
  remaining_today: number;
  provider: string;
  model: string | null;
  chat_mode: string;
  enabled: boolean;
  last_test_at: string | null;
}

// --- DDoS Koruma ---

export interface DdosConfig {
  syn_flood_enabled: boolean;
  syn_flood_rate: number;
  syn_flood_burst: number;
  udp_flood_enabled: boolean;
  udp_flood_rate: number;
  udp_flood_burst: number;
  icmp_flood_enabled: boolean;
  icmp_flood_rate: number;
  icmp_flood_burst: number;
  conn_limit_enabled: boolean;
  conn_limit_per_ip: number;
  invalid_packet_enabled: boolean;
  http_flood_enabled: boolean;
  http_flood_rate: string;
  http_flood_burst: number;
  kernel_hardening_enabled: boolean;
  tcp_max_syn_backlog: number;
  tcp_synack_retries: number;
  netfilter_conntrack_max: number;
  uvicorn_workers_enabled: boolean;
  uvicorn_workers: number;
}

export interface DdosProtectionStatus {
  name: string;
  enabled: boolean;
  active: boolean;
  description: string;
}

// ============================================================================
// Sistem Yönetimi
// ============================================================================

export interface ServiceStatus {
  name: string;
  label: string;
  active_state: string;
  sub_state: string;
  pid: number | null;
  memory_mb: number | null;
  uptime_seconds: number | null;
  critical: boolean;
  restart_count: number | null;
}

export interface SystemOverview {
  uptime_seconds: number;
  boot_time: string;
  boot_count: number;
  safe_mode: boolean;
  watchdog_active: boolean;
  hostname: string;
}

export interface BootInfo {
  boot_count: number;
  safe_mode: boolean;
  max_boots_threshold: number;
  watchdog_active: boolean;
  recent_boots: string[];
}

// --- Connection Flow (Per-flow Baglanti Takibi) ---

export interface LiveFlow {
  flow_id: string;
  device_id: number | null;
  device_hostname: string;
  device_ip: string;
  src_ip: string;
  src_port: number;
  dst_ip: string;
  dst_port: number;
  dst_domain: string;
  protocol: string;
  state: string;
  direction: string | null;
  service_name: string | null;
  app_name: string | null;
  bytes_sent: number;
  bytes_received: number;
  bytes_total: number;
  packets_sent: number;
  packets_received: number;
  bps_in: number;
  bps_out: number;
  first_seen: string | null;
  last_seen: string | null;
  ended_at: string | null;
  category: string | null;
  dst_device_id: number | null;
  dst_device_hostname: string | null;
}

export interface FlowHistoryResponse {
  items: LiveFlow[];
  total: number;
  limit: number;
  offset: number;
}

export interface FlowStats {
  total_active_flows: number;
  total_bytes_in: number;
  total_bytes_out: number;
  total_devices_with_flows: number;
  large_transfer_count: number;
  total_internal_flows: number;
  last_update: string | null;
}

export interface DeviceFlowSummary {
  device_id: number;
  device_hostname: string | null;
  active_flows: number;
  total_flows_period: number;
  total_bytes_sent: number;
  total_bytes_received: number;
  top_domains: Array<{ domain: string; count: number; bytes: number }>;
  top_ports: Array<{ port: number; count: number; bytes: number }>;
}

// --- WiFi AP ---

export interface WifiStatus {
  enabled: boolean;
  ssid: string | null;
  channel: number | null;
  band: string | null;
  tx_power: number | null;
  clients_count: number;
  interface: string;
}

export interface WifiConfig {
  ssid: string;
  password: string | null;
  channel: number;
  band: string;
  tx_power: number;
  hidden_ssid: boolean;
  enabled: boolean;
  guest_enabled: boolean;
  guest_ssid: string | null;
  guest_password: string | null;
  mac_filter_mode: string;
  mac_filter_list: string[];
  schedule_enabled: boolean;
  schedule_start: string | null;
  schedule_stop: string | null;
}

export interface WifiClient {
  mac_address: string;
  ip_address: string | null;
  signal_dbm: number;
  tx_bitrate_mbps: number;
  rx_bitrate_mbps: number;
  connected_seconds: number;
  hostname: string | null;
}

// --- Güvenlik Ayarları ---

export interface SecurityConfig {
  id: number;
  external_rate_threshold: number;
  local_rate_threshold: number;
  block_duration_sec: number;
  dga_detection_enabled: boolean;
  dga_entropy_threshold: number;
  insight_cooldown_sec: number;
  subnet_flood_enabled: boolean;
  subnet_flood_threshold: number;
  subnet_window_sec: number;
  subnet_block_duration_sec: number;
  scan_pattern_enabled: boolean;
  scan_pattern_threshold: number;
  scan_pattern_window_sec: number;
  threat_score_auto_block: number;
  threat_score_ttl: number;
  aggregated_cooldown_sec: number;
  dns_rate_limit_per_sec: number;
  dns_blocked_qtypes: number[];
  sinkhole_ipv4: string;
  sinkhole_ipv6: string;
  ddos_alert_syn_flood: number;
  ddos_alert_udp_flood: number;
  ddos_alert_icmp_flood: number;
  ddos_alert_conn_limit: number;
  ddos_alert_invalid_packet: number;
  ddos_alert_cooldown_sec: number;
  fingerprint_ttl: number;
  fingerprint_min_matches: number;
  fingerprint_update_cooldown: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface SecurityStats {
  blocked_ip_count: number;
  total_auto_blocks: number;
  total_external_blocked: number;
  total_suspicious: number;
  dga_detections: number;
  blocked_subnet_count: number;
  last_threat_time: string | null;
}
