# --- Ajan: MIMAR (THE ARCHITECT) ---
# Dashboard agrege response semalari.

from pydantic import BaseModel
from typing import Optional


class DeviceSummary(BaseModel):
    total: int = 0
    online: int = 0
    blocked: int = 0


class BandwidthSummary(BaseModel):
    wan_download_mbps: float = 0.0
    wan_upload_mbps: float = 0.0
    lan_throughput_mbps: float = 0.0
    timestamp: Optional[str] = None


class AlertSummary(BaseModel):
    critical: int = 0


class DashboardSummaryResponse(BaseModel):
    devices: DeviceSummary
    bandwidth: BandwidthSummary
    alerts: AlertSummary
