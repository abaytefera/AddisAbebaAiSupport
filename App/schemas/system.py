from pydantic import BaseModel
from typing import List, Dict

class MetricStats(BaseModel):
    companies: int
    admins: int
    servers: int

class ChartData(BaseModel):
    name: str
    traffic: int

class StatusData(BaseModel):
    name: str
    value: int

class SystemStatsResponse(BaseModel):
    metrics: MetricStats
    traffic: List[ChartData]
    status: List[StatusData]
    uptime: List[Dict]