import pandas as pd
from datetime import date, timedelta
from typing import Dict, List, Tuple, Optional
import logging
from collections import defaultdict

from .models import AgentQuote, PolicyAnalysis
from .config import config

logger = logging.getLogger(__name__)


def get_today() -> date:
    """Get current date for business logic (configurable for testing)"""
    return date(2025, 7, 6)  # Frozen for reproducibility


def deduplicate_payments(carrier_df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate payments based on policy_id, paid_date, and amount.
    
    As per FAQ #7: collapse identical (policy_id, paid_date, amount) rows into one logical payment.
    """
    logger.info(f"Processing {len(carrier_df)} payment records for deduplication")
    
    # Group by key fields and keep only one record per group
    # For status, we take the latest alphabetically (active comes before cancelled)
    deduplicated = (carrier_df
                   .sort_values(['policy_id', 'paid_date', 'amount', 'status'])
                   .drop_duplicates(subset=['policy_id', 'paid_date', 'amount'], keep='last'))
    
    removed_count = len(carrier_df) - len(deduplicated)
    if removed_count > 0:
        logger.info(f"Removed {removed_count} duplicate payment records")
    
    return deduplicated


def calculate_earned_per_policy(carrier_df: pd.DataFrame) -> Dict[Tuple[str, str], float]:
    """
    Calculate total earned amount per policy (policy_id, agent_id).
    
    Handles claw-backs (negative payments) as per business rules.
    """
    # First deduplicate payments
    carrier_clean = deduplicate_payments(carrier_df)
    
    # Group by policy and agent, sum all payments (including negative ones for claw-backs)
    earned_by_policy = (carrier_clean
                       .groupby(['policy_id', 'agent_id'])['amount']
                       .sum()
                       .to_dict())
    
    logger.info(f"Calculated earnings for {len(earned_by_policy)} unique policies")
    return earned_by_policy


def get_latest_policy_status(carrier_df: pd.DataFrame) -> Dict[Tuple[str, str], str]:
    """
    Get the latest status for each policy based on the most recent payment date.
    
    As per FAQ #6: sort by paid_date to find last-known status.
    """
    # Create a copy to avoid modifying the original
    carrier_copy = carrier_df.copy()
    
    # Convert paid_date to datetime if it's a string
    if carrier_copy['paid_date'].dtype == 'object':
        carrier_copy['paid_date'] = pd.to_datetime(carrier_copy['paid_date'])
    
    # Sort by paid_date to get the latest status for each policy
    latest_status = (carrier_copy
                    .sort_values('paid_date')
                    .groupby(['policy_id', 'agent_id'])['status']
                    .last()
                    .to_dict())
    
    return latest_status


def determine_eligibility(submit_date: date, latest_status: str, today: Optional[date] = None) -> bool:
    """
    Determine if a policy is eligible for advance.
    
    Rules:
    - status must be 'active'
    - submit_date must be <= today - 7 days
    """
    if today is None:
        today = get_today()
    
    return (latest_status == 'active' and 
            submit_date <= today - timedelta(days=config.ELIGIBILITY_DAYS))


def analyze_policies(carrier_df: pd.DataFrame, crm_df: pd.DataFrame) -> List[PolicyAnalysis]:
    """
    Analyze all policies to determine eligibility and calculate remaining expected amounts.
    """
    today = get_today()
    
    # Calculate earned amounts per policy
    earned_by_policy = calculate_earned_per_policy(carrier_df)
    
    # Get latest status per policy
    latest_status_by_policy = get_latest_policy_status(carrier_df)
    
    policy_analyses = []
    
    for _, crm_row in crm_df.iterrows():
        policy_key = (crm_row['policy_id'], crm_row['agent_id'])
        
        # Get earned amount (default to 0 if no payments yet)
        earned_to_date = earned_by_policy.get(policy_key, 0.0)
        
        # Get latest status (default to 'active' if no payments yet)
        latest_status = latest_status_by_policy.get(policy_key, 'active')
        
        # Calculate remaining expected (can't be negative)
        remaining_expected = max(crm_row['ltv_expected'] - earned_to_date, 0.0)
        
        # Convert submit_date to date object if it's a string
        submit_date = crm_row['submit_date']
        if isinstance(submit_date, str):
            from datetime import datetime
            submit_date = datetime.strptime(submit_date, '%Y-%m-%d').date()
        
        # Determine eligibility
        is_eligible = determine_eligibility(submit_date, latest_status, today)
        
        analysis = PolicyAnalysis(
            policy_id=crm_row['policy_id'],
            agent_id=crm_row['agent_id'],
            earned_to_date=earned_to_date,
            remaining_expected=remaining_expected,
            is_eligible=is_eligible,
            submit_date=submit_date,
            latest_status=latest_status
        )
        
        policy_analyses.append(analysis)
    
    logger.info(f"Analyzed {len(policy_analyses)} policies")
    return policy_analyses


def calculate_agent_quotes(policy_analyses: List[PolicyAnalysis]) -> List[AgentQuote]:
    """
    Calculate safe-to-advance amounts per agent with proper cap handling.
    
    Rules:
    - Safe-to-advance = min(0.80 × Σ remaining_expected (eligible), $2,000 cap)
    - Only eligible policies count toward advance calculation
    """
    # Group analyses by agent
    agent_data = defaultdict(lambda: {
        'total_earned': 0.0,
        'total_eligible_remaining': 0.0,
        'eligible_policies_count': 0
    })
    
    for analysis in policy_analyses:
        agent_id = analysis.agent_id
        agent_data[agent_id]['total_earned'] += analysis.earned_to_date
        
        if analysis.is_eligible:
            agent_data[agent_id]['total_eligible_remaining'] += analysis.remaining_expected
            agent_data[agent_id]['eligible_policies_count'] = int(agent_data[agent_id]['eligible_policies_count']) + 1
    
    # Calculate quotes for each agent
    agent_quotes = []
    
    for agent_id, data in agent_data.items():
        # Apply advance percentage
        calculated_advance = data['total_eligible_remaining'] * config.ADVANCE_PERCENTAGE
        
        # Apply cap
        safe_to_advance = min(calculated_advance, config.MAX_ADVANCE_AMOUNT)
        
        quote = AgentQuote(
            agent_id=agent_id,
            earned_to_date=data['total_earned'],
            total_eligible_remaining=data['total_eligible_remaining'],
            safe_to_advance=safe_to_advance,
            eligible_policies_count=int(data['eligible_policies_count'])
        )
        
        agent_quotes.append(quote)
    
    # Sort by agent_id for consistent output
    agent_quotes.sort(key=lambda x: x.agent_id)
    
    logger.info(f"Generated quotes for {len(agent_quotes)} agents")
    return agent_quotes


def compute_quotes(carrier_df: pd.DataFrame, crm_df: pd.DataFrame) -> List[Dict]:
    """
    Main business logic function to compute commission advance quotes.
    
    Handles all edge cases:
    - Duplicate payments
    - Claw-backs (negative payments)
    - Retro policy status changes
    - $2,000 cap per agent
    """
    logger.info("Starting quote computation")
    
    try:
        # Analyze all policies
        policy_analyses = analyze_policies(carrier_df, crm_df)
        
        # Calculate agent quotes
        agent_quotes = calculate_agent_quotes(policy_analyses)
        
        # Convert to dict format for API response (maintaining backward compatibility)
        result = []
        for quote in agent_quotes:
            result.append({
                'agent_id': quote.agent_id,
                'earned_to_date': quote.earned_to_date,
                'total_eligible_remaining': quote.total_eligible_remaining,
                'safe_to_advance': quote.safe_to_advance,
                'eligible_policies_count': quote.eligible_policies_count
            })
        
        logger.info(f"Successfully computed quotes for {len(result)} agents")
        return result
        
    except Exception as e:
        logger.error(f"Error computing quotes: {str(e)}")
        raise


def get_detailed_agent_quotes(carrier_df: pd.DataFrame, crm_df: pd.DataFrame) -> List[AgentQuote]:
    """
    Get detailed agent quotes with additional metrics for internal use.
    """
    policy_analyses = analyze_policies(carrier_df, crm_df)
    return calculate_agent_quotes(policy_analyses) 