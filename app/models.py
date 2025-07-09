from dataclasses import dataclass
from datetime import date
from typing import List, Optional


@dataclass
class CarrierRemittance:
    """Represents a payment record from insurance carriers"""
    policy_id: str
    agent_id: str
    carrier: str
    paid_date: date
    amount: float
    status: str


@dataclass
class CRMPolicy:
    """Represents a policy record from CRM system"""
    policy_id: str
    agent_id: str
    submit_date: date
    ltv_expected: float


@dataclass
class PolicyAnalysis:
    """Analysis results for a single policy"""
    policy_id: str
    agent_id: str
    earned_to_date: float
    remaining_expected: float
    is_eligible: bool
    submit_date: date
    latest_status: str


@dataclass
class AgentQuote:
    """Commission advance quote for an agent"""
    agent_id: str
    earned_to_date: float
    total_eligible_remaining: float
    safe_to_advance: float
    eligible_policies_count: int


@dataclass
class AdvanceQuoteResponse:
    """Response object for advance quote API"""
    generated_at: str
    quotes: List[AgentQuote]
    total_agents: int
    total_policies_analyzed: int 