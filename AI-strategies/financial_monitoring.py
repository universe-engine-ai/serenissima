#!/usr/bin/env python3
"""
Financial Monitoring Script for Antonio Corfiote

This script:
1. Fetches current financial data from the API
2. Tracks income, expenses, and net worth over time
3. Analyzes financial trends and identifies opportunities
4. Provides alerts for significant changes or issues

Usage:
python financial_monitoring.py [--update] [--analyze] [--forecast]
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Any, Tuple
from dotenv import load_dotenv

# Set up argument parsing
parser = argparse.ArgumentParser(description="Monitor and analyze financial situation")
parser.add_argument("--update", action="store_true", help="Update financial records with current data")
parser.add_argument("--analyze", action="store_true", help="Analyze financial trends")
parser.add_argument("--forecast", action="store_true", help="Generate financial forecasts")
parser.add_argument("--days", type=int, default=30, help="Number of days for analysis/forecast (default: 30)")
parser.add_argument("--output", type=str, default="financial_report.json", help="Output file for detailed report")
parser.add_argument("--history-file", type=str, default="financial_history.json", help="File to store historical data")
parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
args = parser.parse_args()

# Load environment variables
load_dotenv()

# Constants
API_BASE_URL = os.getenv("API_BASE_URL", "https://serenissima.ai")
CITIZEN_USERNAME = "greek_trader2"  # Antonio's username
ALERT_THRESHOLDS = {
    "income_drop": 0.1,     # Alert if income drops by 10%
    "expense_increase": 0.1, # Alert if expenses increase by 10%
    "low_liquidity": 100000, # Alert if liquid assets fall below 100,000 ducats
    "high_opportunity": 0.2  # Alert if potential ROI exceeds 20%
}

def fetch_citizen_data() -> Dict:
    """Fetch current citizen financial data from the API."""
    try:
        url = f"{API_BASE_URL}/api/citizens/{CITIZEN_USERNAME}"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            print(f"Successfully fetched financial data for {CITIZEN_USERNAME}")
            return data
        else:
            print(f"Error fetching citizen data: {response.status_code} - {response.text}")
            return {}
    except Exception as e:
        print(f"Exception fetching citizen data: {str(e)}")
        return {}

def fetch_citizen_buildings() -> List[Dict]:
    """Fetch buildings owned by the citizen."""
    try:
        url = f"{API_BASE_URL}/api/buildings?owner={CITIZEN_USERNAME}"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"Found {len(data)} buildings owned by {CITIZEN_USERNAME}")
                return data
            else:
                print(f"Unexpected API response format: {data}")
                return []
        else:
            print(f"Error fetching buildings: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Exception fetching buildings: {str(e)}")
        return []

def fetch_citizen_contracts() -> List[Dict]:
    """Fetch active contracts for the citizen."""
    try:
        url = f"{API_BASE_URL}/api/contracts?citizen={CITIZEN_USERNAME}&status=active"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"Found {len(data)} active contracts for {CITIZEN_USERNAME}")
                return data
            else:
                print(f"Unexpected API response format: {data}")
                return []
        else:
            print(f"Error fetching contracts: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Exception fetching contracts: {str(e)}")
        return []

def load_financial_history() -> List[Dict]:
    """Load historical financial data from file."""
    try:
        if os.path.exists(args.history_file):
            with open(args.history_file, 'r') as f:
                history = json.load(f)
                print(f"Loaded {len(history)} historical financial records")
                return history
        else:
            print(f"No existing financial history file found at {args.history_file}")
            return []
    except Exception as e:
        print(f"Error loading financial history: {str(e)}")
        return []

def save_financial_history(history: List[Dict]) -> bool:
    """Save updated financial history to file."""
    try:
        with open(args.history_file, 'w') as f:
            json.dump(history, f, indent=2)
            print(f"Saved {len(history)} financial records to {args.history_file}")
            return True
    except Exception as e:
        print(f"Error saving financial history: {str(e)}")
        return False

def update_financial_records() -> Dict:
    """Update financial records with current data."""
    # Load existing history
    history = load_financial_history()
    
    # Fetch current data
    citizen_data = fetch_citizen_data()
    buildings = fetch_citizen_buildings()
    contracts = fetch_citizen_contracts()
    
    if not citizen_data:
        print("Failed to fetch citizen data. Cannot update financial records.")
        return {}
    
    # Extract key financial metrics
    ducats = citizen_data.get("ducats", 0)
    daily_income = citizen_data.get("dailyIncome", 0)
    daily_turnover = citizen_data.get("dailyTurnover", 0)
    weekly_income = citizen_data.get("weeklyIncome", 0)
    weekly_turnover = citizen_data.get("weeklyTurnover", 0)
    monthly_income = citizen_data.get("monthlyIncome", 0)
    monthly_turnover = citizen_data.get("monthlyTurnover", 0)
    
    # Calculate asset values
    building_value = sum(b.get("value", 0) for b in buildings)
    contract_value = sum(c.get("value", 0) for c in contracts)
    
    # Calculate expenses (estimate based on turnover)
    daily_expenses = daily_turnover - daily_income
    
    # Create new financial record
    now = datetime.now()
    new_record = {
        "date": now.isoformat(),
        "ducats": ducats,
        "daily_income": daily_income,
        "daily_expenses": daily_expenses,
        "daily_turnover": daily_turnover,
        "weekly_income": weekly_income,
        "weekly_turnover": weekly_turnover,
        "monthly_income": monthly_income,
        "monthly_turnover": monthly_turnover,
        "building_value": building_value,
        "contract_value": contract_value,
        "total_assets": ducats + building_value + contract_value,
        "net_worth": ducats + building_value + contract_value  # Could be adjusted for liabilities
    }
    
    # Add to history
    history.append(new_record)
    
    # Save updated history
    save_financial_history(history)
    
    return new_record

def analyze_financial_trends(history: List[Dict]) -> Dict:
    """Analyze financial trends from historical data."""
    if not history or len(history) < 2:
        print("Insufficient historical data for trend analysis.")
        return {}
    
    # Sort history by date
    sorted_history = sorted(history, key=lambda x: x["date"])
    
    # Get most recent and oldest records within analysis period
    now = datetime.now()
    cutoff_date = (now - timedelta(days=args.days)).isoformat()
    recent_history = [record for record in sorted_history if record["date"] >= cutoff_date]
    
    if not recent_history or len(recent_history) < 2:
        print(f"Insufficient data within the last {args.days} days for trend analysis.")
        return {}
    
    current = recent_history[-1]
    previous = recent_history[0]
    
    # Calculate changes
    ducat_change = current["ducats"] - previous["ducats"]
    ducat_change_pct = (ducat_change / previous["ducats"]) * 100 if previous["ducats"] > 0 else 0
    
    income_change = current["daily_income"] - previous["daily_income"]
    income_change_pct = (income_change / previous["daily_income"]) * 100 if previous["daily_income"] > 0 else 0
    
    expense_change = current["daily_expenses"] - previous["daily_expenses"]
    expense_change_pct = (expense_change / previous["daily_expenses"]) * 100 if previous["daily_expenses"] > 0 else 0
    
    net_worth_change = current["net_worth"] - previous["net_worth"]
    net_worth_change_pct = (net_worth_change / previous["net_worth"]) * 100 if previous["net_worth"] > 0 else 0
    
    # Calculate averages
    avg_daily_income = sum(record["daily_income"] for record in recent_history) / len(recent_history)
    avg_daily_expenses = sum(record["daily_expenses"] for record in recent_history) / len(recent_history)
    avg_daily_profit = avg_daily_income - avg_daily_expenses
    
    # Generate alerts
    alerts = []
    if income_change_pct < -ALERT_THRESHOLDS["income_drop"] * 100:
        alerts.append(f"ALERT: Daily income has dropped by {abs(income_change_pct):.2f}% in the last {args.days} days")
    
    if expense_change_pct > ALERT_THRESHOLDS["expense_increase"] * 100:
        alerts.append(f"ALERT: Daily expenses have increased by {expense_change_pct:.2f}% in the last {args.days} days")
    
    if current["ducats"] < ALERT_THRESHOLDS["low_liquidity"]:
        alerts.append(f"ALERT: Liquid assets (ducats) are below the threshold of {ALERT_THRESHOLDS['low_liquidity']}")
    
    # Calculate trends
    income_trend = "increasing" if income_change > 0 else "decreasing" if income_change < 0 else "stable"
    expense_trend = "increasing" if expense_change > 0 else "decreasing" if expense_change < 0 else "stable"
    net_worth_trend = "increasing" if net_worth_change > 0 else "decreasing" if net_worth_change < 0 else "stable"
    
    return {
        "analysis_date": now.isoformat(),
        "period_days": args.days,
        "current_state": {
            "ducats": current["ducats"],
            "daily_income": current["daily_income"],
            "daily_expenses": current["daily_expenses"],
            "daily_profit": current["daily_income"] - current["daily_expenses"],
            "net_worth": current["net_worth"]
        },
        "changes": {
            "ducats_change": ducat_change,
            "ducats_change_pct": ducat_change_pct,
            "income_change": income_change,
            "income_change_pct": income_change_pct,
            "expense_change": expense_change,
            "expense_change_pct": expense_change_pct,
            "net_worth_change": net_worth_change,
            "net_worth_change_pct": net_worth_change_pct
        },
        "averages": {
            "avg_daily_income": avg_daily_income,
            "avg_daily_expenses": avg_daily_expenses,
            "avg_daily_profit": avg_daily_profit
        },
        "trends": {
            "income_trend": income_trend,
            "expense_trend": expense_trend,
            "net_worth_trend": net_worth_trend
        },
        "alerts": alerts
    }

def generate_financial_forecast(history: List[Dict]) -> Dict:
    """Generate financial forecasts based on historical data."""
    if not history or len(history) < 7:  # Need at least a week of data
        print("Insufficient historical data for forecasting.")
        return {}
    
    # Sort history by date
    sorted_history = sorted(history, key=lambda x: x["date"])
    
    # Get recent records for forecasting
    now = datetime.now()
    cutoff_date = (now - timedelta(days=30)).isoformat()  # Use last 30 days for forecasting
    recent_history = [record for record in sorted_history if record["date"] >= cutoff_date]
    
    if not recent_history or len(recent_history) < 7:
        print("Insufficient recent data for forecasting.")
        return {}
    
    # Calculate average daily changes
    daily_ducat_changes = []
    daily_income_changes = []
    daily_expense_changes = []
    
    for i in range(1, len(recent_history)):
        prev = recent_history[i-1]
        curr = recent_history[i]
        
        prev_date = datetime.fromisoformat(prev["date"])
        curr_date = datetime.fromisoformat(curr["date"])
        days_diff = (curr_date - prev_date).days or 1  # Avoid division by zero
        
        ducat_change = (curr["ducats"] - prev["ducats"]) / days_diff
        income_change = (curr["daily_income"] - prev["daily_income"]) / days_diff
        expense_change = (curr["daily_expenses"] - prev["daily_expenses"]) / days_diff
        
        daily_ducat_changes.append(ducat_change)
        daily_income_changes.append(income_change)
        daily_expense_changes.append(expense_change)
    
    # Calculate average daily changes
    avg_daily_ducat_change = sum(daily_ducat_changes) / len(daily_ducat_changes) if daily_ducat_changes else 0
    avg_daily_income_change = sum(daily_income_changes) / len(daily_income_changes) if daily_income_changes else 0
    avg_daily_expense_change = sum(daily_expense_changes) / len(daily_expense_changes) if daily_expense_changes else 0
    
    # Get current values
    current = recent_history[-1]
    current_ducats = current["ducats"]
    current_daily_income = current["daily_income"]
    current_daily_expenses = current["daily_expenses"]
    current_net_worth = current["net_worth"]
    
    # Generate forecasts
    forecast_days = args.days
    forecast_dates = [(now + timedelta(days=i)).isoformat() for i in range(1, forecast_days + 1)]
    
    forecast_ducats = [current_ducats + (avg_daily_ducat_change * i) for i in range(1, forecast_days + 1)]
    forecast_daily_income = [current_daily_income + (avg_daily_income_change * i) for i in range(1, forecast_days + 1)]
    forecast_daily_expenses = [current_daily_expenses + (avg_daily_expense_change * i) for i in range(1, forecast_days + 1)]
    forecast_daily_profit = [income - expense for income, expense in zip(forecast_daily_income, forecast_daily_expenses)]
    
    # Calculate projected net worth
    forecast_net_worth = [current_net_worth]
    for profit in forecast_daily_profit:
        forecast_net_worth.append(forecast_net_worth[-1] + profit)
    forecast_net_worth = forecast_net_worth[1:]  # Remove the initial value
    
    # Calculate key milestones
    days_to_next_million = None
    if avg_daily_ducat_change > 0:
        next_million = (current_ducats // 1000000 + 1) * 1000000
        days_to_next_million = int((next_million - current_ducats) / avg_daily_ducat_change)
    
    days_to_double_income = None
    if avg_daily_income_change > 0:
        days_to_double_income = int(current_daily_income / avg_daily_income_change)
    
    return {
        "forecast_date": now.isoformat(),
        "forecast_days": forecast_days,
        "current_values": {
            "ducats": current_ducats,
            "daily_income": current_daily_income,
            "daily_expenses": current_daily_expenses,
            "daily_profit": current_daily_income - current_daily_expenses,
            "net_worth": current_net_worth
        },
        "average_daily_changes": {
            "ducat_change": avg_daily_ducat_change,
            "income_change": avg_daily_income_change,
            "expense_change": avg_daily_expense_change
        },
        "forecasts": {
            "dates": forecast_dates,
            "ducats": forecast_ducats,
            "daily_income": forecast_daily_income,
            "daily_expenses": forecast_daily_expenses,
            "daily_profit": forecast_daily_profit,
            "net_worth": forecast_net_worth
        },
        "milestones": {
            "days_to_next_million": days_to_next_million,
            "days_to_double_income": days_to_double_income
        }
    }

def plot_financial_data(history: List[Dict], forecast: Dict = None):
    """Plot financial data and forecasts."""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from matplotlib.ticker import FuncFormatter
    except ImportError:
        print("Matplotlib not available. Cannot generate plots.")
        return
    
    if not history:
        print("No historical data to plot.")
        return
    
    # Sort history by date
    sorted_history = sorted(history, key=lambda x: x["date"])
    
    # Extract data for plotting
    dates = [datetime.fromisoformat(record["date"]) for record in sorted_history]
    ducats = [record["ducats"] for record in sorted_history]
    daily_income = [record["daily_income"] for record in sorted_history]
    daily_expenses = [record["daily_expenses"] for record in sorted_history]
    net_worth = [record["net_worth"] for record in sorted_history]
    
    # Create figure with subplots
    fig, axs = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle(f'Financial Analysis for {CITIZEN_USERNAME}', fontsize=16)
    
    # Format y-axis to show thousands/millions
    def format_ducats(x, pos):
        if x >= 1_000_000:
            return f'{x/1_000_000:.1f}M'
        elif x >= 1_000:
            return f'{x/1_000:.1f}K'
        else:
            return f'{x:.0f}'
    
    formatter = FuncFormatter(format_ducats)
    
    # Plot ducats over time
    axs[0, 0].plot(dates, ducats, 'b-', label='Ducats')
    axs[0, 0].set_title('Ducats Over Time')
    axs[0, 0].set_ylabel('Ducats')
    axs[0, 0].yaxis.set_major_formatter(formatter)
    axs[0, 0].grid(True)
    
    # Plot income and expenses
    axs[0, 1].plot(dates, daily_income, 'g-', label='Daily Income')
    axs[0, 1].plot(dates, daily_expenses, 'r-', label='Daily Expenses')
    axs[0, 1].set_title('Daily Income and Expenses')
    axs[0, 1].set_ylabel('Ducats')
    axs[0, 1].yaxis.set_major_formatter(formatter)
    axs[0, 1].legend()
    axs[0, 1].grid(True)
    
    # Plot net worth
    axs[1, 0].plot(dates, net_worth, 'purple', label='Net Worth')
    axs[1, 0].set_title('Net Worth Over Time')
    axs[1, 0].set_ylabel('Ducats')
    axs[1, 0].yaxis.set_major_formatter(formatter)
    axs[1, 0].grid(True)
    
    # Plot daily profit (income - expenses)
    daily_profit = [i - e for i, e in zip(daily_income, daily_expenses)]
    axs[1, 1].plot(dates, daily_profit, 'orange', label='Daily Profit')
    axs[1, 1].set_title('Daily Profit')
    axs[1, 1].set_ylabel('Ducats')
    axs[1, 1].yaxis.set_major_formatter(formatter)
    axs[1, 1].grid(True)
    
    # Add forecasts if available
    if forecast and 'forecasts' in forecast:
        forecast_dates = [datetime.fromisoformat(d) for d in forecast['forecasts']['dates']]
        forecast_ducats = forecast['forecasts']['ducats']
        forecast_income = forecast['forecasts']['daily_income']
        forecast_expenses = forecast['forecasts']['daily_expenses']
        forecast_profit = forecast['forecasts']['daily_profit']
        forecast_net_worth = forecast['forecasts']['net_worth']
        
        # Add forecast to ducats plot
        axs[0, 0].plot(forecast_dates, forecast_ducats, 'b--', label='Forecast')
        axs[0, 0].legend()
        
        # Add forecast to income and expenses plot
        axs[0, 1].plot(forecast_dates, forecast_income, 'g--', label='Income Forecast')
        axs[0, 1].plot(forecast_dates, forecast_expenses, 'r--', label='Expenses Forecast')
        axs[0, 1].legend()
        
        # Add forecast to net worth plot
        axs[1, 0].plot(forecast_dates, forecast_net_worth, 'purple--', label='Forecast')
        axs[1, 0].legend()
        
        # Add forecast to profit plot
        axs[1, 1].plot(forecast_dates, forecast_profit, 'orange--', label='Forecast')
        axs[1, 1].legend()
    
    # Format x-axis dates
    for ax in axs.flat:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.9)
    
    # Save the plot
    plt.savefig('financial_analysis.png')
    print("Financial analysis plots saved to financial_analysis.png")
    
    # Show the plot if running interactively
    plt.show()

def main():
    """Main execution function."""
    print(f"Starting financial monitoring for {CITIZEN_USERNAME}")
    
    # Load existing financial history
    history = load_financial_history()
    
    # Update financial records if requested
    current_record = {}
    if args.update:
        print("Updating financial records...")
        current_record = update_financial_records()
        if current_record:
            print("Financial records updated successfully.")
            # Reload history after update
            history = load_financial_history()
    
    # Analyze financial trends if requested
    analysis = {}
    if args.analyze:
        print("Analyzing financial trends...")
        analysis = analyze_financial_trends(history)
        if analysis:
            print("\n=== Financial Analysis Results ===")
            print(f"Current Ducats: {analysis['current_state']['ducats']:,.2f}")
            print(f"Daily Income: {analysis['current_state']['daily_income']:,.2f}")
            print(f"Daily Expenses: {analysis['current_state']['daily_expenses']:,.2f}")
            print(f"Daily Profit: {analysis['current_state']['daily_profit']:,.2f}")
            print(f"Net Worth: {analysis['current_state']['net_worth']:,.2f}")
            
            print("\nChanges over the last {args.days} days:")
            print(f"Ducats: {analysis['changes']['ducats_change']:,.2f} ({analysis['changes']['ducats_change_pct']:,.2f}%)")
            print(f"Daily Income: {analysis['changes']['income_change']:,.2f} ({analysis['changes']['income_change_pct']:,.2f}%)")
            print(f"Daily Expenses: {analysis['changes']['expense_change']:,.2f} ({analysis['changes']['expense_change_pct']:,.2f}%)")
            print(f"Net Worth: {analysis['changes']['net_worth_change']:,.2f} ({analysis['changes']['net_worth_change_pct']:,.2f}%)")
            
            print("\nTrends:")
            print(f"Income Trend: {analysis['trends']['income_trend']}")
            print(f"Expense Trend: {analysis['trends']['expense_trend']}")
            print(f"Net Worth Trend: {analysis['trends']['net_worth_trend']}")
            
            if analysis['alerts']:
                print("\nAlerts:")
                for alert in analysis['alerts']:
                    print(f"- {alert}")
    
    # Generate financial forecast if requested
    forecast = {}
    if args.forecast:
        print("Generating financial forecast...")
        forecast = generate_financial_forecast(history)
        if forecast:
            print("\n=== Financial Forecast Results ===")
            print(f"Forecast Period: {forecast['forecast_days']} days")
            
            print("\nAverage Daily Changes:")
            print(f"Ducats: {forecast['average_daily_changes']['ducat_change']:,.2f}")
            print(f"Income: {forecast['average_daily_changes']['income_change']:,.2f}")
            print(f"Expenses: {forecast['average_daily_changes']['expense_change']:,.2f}")
            
            print("\nEnd of Period Forecast:")
            print(f"Ducats: {forecast['forecasts']['ducats'][-1]:,.2f}")
            print(f"Daily Income: {forecast['forecasts']['daily_income'][-1]:,.2f}")
            print(f"Daily Expenses: {forecast['forecasts']['daily_expenses'][-1]:,.2f}")
            print(f"Daily Profit: {forecast['forecasts']['daily_profit'][-1]:,.2f}")
            print(f"Net Worth: {forecast['forecasts']['net_worth'][-1]:,.2f}")
            
            print("\nMilestones:")
            if forecast['milestones']['days_to_next_million'] is not None:
                print(f"Days to next million ducats: {forecast['milestones']['days_to_next_million']}")
            if forecast['milestones']['days_to_double_income'] is not None:
                print(f"Days to double daily income: {forecast['milestones']['days_to_double_income']}")
    
    # Generate combined report
    report = {
        "citizen": CITIZEN_USERNAME,
        "report_date": datetime.now().isoformat(),
        "current_record": current_record,
        "analysis": analysis,
        "forecast": forecast
    }
    
    # Save report to file
    with open(args.output, 'w') as f:
        json.dump(report, f, indent=2)
        print(f"\nDetailed financial report saved to {args.output}")
    
    # Generate plots if both analysis and forecast are available
    if analysis and forecast:
        plot_financial_data(history, forecast)
    elif analysis:
        plot_financial_data(history)

if __name__ == "__main__":
    main()
