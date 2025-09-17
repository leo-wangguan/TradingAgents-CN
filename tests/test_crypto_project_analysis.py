import asyncio
import os
import sys
import time

sys.path.append('.')

from dotenv import load_dotenv
load_dotenv()

from tradingagents.agents.utils.agent_utils import Toolkit
from tradingagents.agents.analysts.crypto_project_analyst import create_crypto_project_analyst
from tradingagents.llm_adapters.deepseek_adapter import ChatDeepSeek
from tradingagents.default_config import DEFAULT_CONFIG

# Add project root to sys.path to allow imports
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# --- Configuration ---
TICKER = "ENA"
TRADE_DATE = "2025-09-16"
LLM_PROVIDER = "deepseek" 
REPORT_DIR = "results/tmp"

def get_llm(provider="openai"):
    """Initializes and returns the specified LLM."""
    if provider == "deepseek":
        print("🤖 Using DeepSeek LLM...")
        return ChatDeepSeek(
            model='deepseek-coder',
            temperature=0.1,
        )
    print("🤖 Using OpenAI LLM...")
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(temperature=0.1, model="gpt-4-turbo")


def main():
    """Main function to run the crypto project analysis."""
    # 1. Initialize Toolkit and LLM
    print("🛠️  Initializing toolkit and LLM...")
    toolkit = Toolkit()
    llm = get_llm(LLM_PROVIDER)

    # 2. Create the analyst node
    print("👨‍💻 Creating crypto project analyst node...")
    crypto_analyst = create_crypto_project_analyst(llm=llm, toolkit=toolkit)

    # 3. Set up the initial state
    initial_state = {
        "company_of_interest": TICKER,
        "trade_date": TRADE_DATE,
        "messages": [],
    }

    # 4. Run the analyst node
    print(f"🚀 Starting analysis for {TICKER}...")
    start_time = time.time()
    final_state = crypto_analyst(initial_state)
    end_time = time.time()
    print(f"⏳ Analysis completed in {end_time - start_time:.2f} seconds.")

    # 5. Print and save the report
    report = final_state.get("fundamentals_report", "No report generated.")
    
    print("\n\n" + "="*80)
    print("📊 CRYPTO PROJECT ANALYSIS REPORT (Preview)")
    print("="*80)
    print(report[:1500] + "\n..." if len(report) > 1500 else report)
    print("="*80)

    # Save the report to a file
    # Ensure the report directory is relative to the project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    report_path = os.path.join(project_root, REPORT_DIR)
    os.makedirs(report_path, exist_ok=True)
    
    file_path = os.path.join(report_path, f"{TICKER.lower()}_project_analysis_report_{time.strftime('%Y%m%d_%H%M%S')}.md")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# {TICKER} Project Analysis Report\n\n")
            f.write(f"**Generated on:** {TRADE_DATE}\n\n")
            f.write(report)
        print(f"✅ Report for {TICKER} saved to: {os.path.abspath(file_path)}")
    except Exception as e:
        print(f"❌ Failed to save report: {e}")

if __name__ == "__main__":
    main()
