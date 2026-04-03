"""
Token usage tracker for OpenAI API calls.
Tracks tokens used and calculates costs in INR.
"""
import json
from pathlib import Path
from datetime import datetime

# OpenAI GPT-4 Pricing (as of 2024)
# Input: $0.03 per 1K tokens
# Output: $0.06 per 1K tokens
# 1 USD = ~83 INR (approximate)

PRICING = {
    "gpt-4": {
        "input": 0.03 / 1000,   # per token
        "output": 0.06 / 1000,  # per token
    },
    "gpt-3.5-turbo": {
        "input": 0.0015 / 1000,
        "output": 0.002 / 1000,
    }
}

USD_TO_INR = 83.0

TRACKER_FILE = Path(__file__).parent.parent / "reports" / "token_usage.json"


class TokenTracker:
    def __init__(self):
        self.session_usage = {
            "start_time": datetime.now().isoformat(),
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0.0,
            "total_cost_inr": 0.0,
            "api_calls": []
        }
        self.load_history()
    
    def load_history(self):
        """Load historical usage data."""
        if TRACKER_FILE.exists():
            try:
                self.history = json.loads(TRACKER_FILE.read_text())
            except:
                self.history = {"sessions": []}
        else:
            self.history = {"sessions": []}
    
    def track_call(self, model, input_tokens, output_tokens, feature="unknown"):
        """Track a single API call."""
        pricing = PRICING.get(model, PRICING["gpt-4"])
        
        input_cost = input_tokens * pricing["input"]
        output_cost = output_tokens * pricing["output"]
        total_cost_usd = input_cost + output_cost
        total_cost_inr = total_cost_usd * USD_TO_INR
        
        call_data = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "feature": feature,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(total_cost_usd, 4),
            "cost_inr": round(total_cost_inr, 2)
        }
        
        self.session_usage["api_calls"].append(call_data)
        self.session_usage["total_input_tokens"] += input_tokens
        self.session_usage["total_output_tokens"] += output_tokens
        self.session_usage["total_cost_usd"] += total_cost_usd
        self.session_usage["total_cost_inr"] += total_cost_inr
        
        # Log to console
        print(f"      💰 API Call: {input_tokens} in + {output_tokens} out = ₹{total_cost_inr:.2f}")
        
        return call_data
    
    def get_session_summary(self):
        """Get current session summary."""
        return {
            "total_calls": len(self.session_usage["api_calls"]),
            "total_input_tokens": self.session_usage["total_input_tokens"],
            "total_output_tokens": self.session_usage["total_output_tokens"],
            "total_tokens": self.session_usage["total_input_tokens"] + self.session_usage["total_output_tokens"],
            "total_cost_usd": round(self.session_usage["total_cost_usd"], 4),
            "total_cost_inr": round(self.session_usage["total_cost_inr"], 2)
        }
    
    def save_session(self):
        """Save session data to history."""
        self.session_usage["end_time"] = datetime.now().isoformat()
        summary = self.get_session_summary()
        self.session_usage["summary"] = summary
        
        self.history["sessions"].append(self.session_usage)
        
        # Calculate all-time totals
        all_time = {
            "total_sessions": len(self.history["sessions"]),
            "total_calls": sum(s["summary"]["total_calls"] for s in self.history["sessions"]),
            "total_tokens": sum(s["summary"]["total_tokens"] for s in self.history["sessions"]),
            "total_cost_usd": round(sum(s["summary"]["total_cost_usd"] for s in self.history["sessions"]), 4),
            "total_cost_inr": round(sum(s["summary"]["total_cost_inr"] for s in self.history["sessions"]), 2)
        }
        self.history["all_time"] = all_time
        
        # Save to file
        TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
        TRACKER_FILE.write_text(json.dumps(self.history, indent=2))
        
        return summary
    
    def print_summary(self):
        """Print session summary to console."""
        summary = self.get_session_summary()
        
        print("\n" + "="*70)
        print("💰 OpenAI API Usage Summary")
        print("="*70)
        print(f"  Total API Calls:     {summary['total_calls']}")
        print(f"  Input Tokens:        {summary['total_input_tokens']:,}")
        print(f"  Output Tokens:       {summary['total_output_tokens']:,}")
        print(f"  Total Tokens:        {summary['total_tokens']:,}")
        print(f"  Cost (USD):          ${summary['total_cost_usd']:.4f}")
        print(f"  Cost (INR):          ₹{summary['total_cost_inr']:.2f}")
        print("="*70)
        
        # Show all-time stats if available
        if "all_time" in self.history:
            at = self.history["all_time"]
            print("\n📊 All-Time Statistics")
            print("-"*70)
            print(f"  Total Sessions:      {at['total_sessions']}")
            print(f"  Total API Calls:     {at['total_calls']}")
            print(f"  Total Tokens:        {at['total_tokens']:,}")
            print(f"  Total Cost (USD):    ${at['total_cost_usd']:.4f}")
            print(f"  Total Cost (INR):    ₹{at['total_cost_inr']:.2f}")
            print("-"*70)


# Global tracker instance
_tracker = None

def get_tracker():
    """Get or create global tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = TokenTracker()
    return _tracker

def track_api_call(model, input_tokens, output_tokens, feature="unknown"):
    """Track an API call."""
    tracker = get_tracker()
    return tracker.track_call(model, input_tokens, output_tokens, feature)

def print_summary():
    """Print usage summary."""
    tracker = get_tracker()
    tracker.print_summary()

def save_session():
    """Save session data."""
    tracker = get_tracker()
    return tracker.save_session()
