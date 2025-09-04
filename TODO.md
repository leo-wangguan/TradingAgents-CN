Of course. Expanding the project to include cryptocurrencies is an excellent idea. The existing multi-agent architecture is very well-suited for this. The key is to adapt the data sources and the "fundamental analysis" part of the process, as crypto fundamentals are very different from stock fundamentals.

Here is a comprehensive, phased plan to extend `TradingAgents-CN` to support cryptocurrency analysis.

### 🎯 Overall Strategy

We will follow a phased approach, starting with foundational data integration and progressively adding more sophisticated, crypto-specific analysis capabilities. The goal is to reuse as much of the existing framework (the graph orchestrator, technical analysis, report generation) as possible while creating new, specialized components for crypto.

I will now create a detailed task list for this project.



[1 tool called]

Of course. Extending the project to support cryptocurrencies is an excellent idea. Given the project's modular architecture, this is very feasible. The key is to adapt the existing agent-based workflow for the unique characteristics of the crypto market.

Here is a comprehensive, phased plan to guide the development process. I have broken it down into actionable steps.

### High-Level Strategy

The core idea is to treat "Cryptocurrency" as a new `market_type`. We will then create crypto-specific data sources and analysis agents, and use the existing `TradingAgentsGraph` orchestrator to route tasks to these new components when a crypto analysis is requested. We will retain as much of the existing structure as possible, especially for technical analysis and workflow management.

### The Plan

#### **Phase 1: Foundation & Core Data Integration**

This phase is about getting the basic data plumbing in place.

*   [ ] **1.1: Implement Crypto Data Fetcher**: Create a new Python class/module in the `tradingagents/dataflows` directory to fetch data from a major cryptocurrency API.
    *   **Recommendation**: Use the **CoinGecko API**. It has a generous free tier and provides comprehensive data (price, volume, market cap, project info).
    *   **Action**: Create a `coingecko_data_fetcher.py`.
*   [ ] **1.2: Integrate into Data Abstraction Layer**: Modify the existing data source manager to recognize and use the new CoinGecko fetcher when the asset is a cryptocurrency.
*   [ ] **1.3: Update Configuration**: Add `'crypto'` as a supported `market_type` in the system's configuration files (e.g., `tradingagents/default_config.py`). This will be the key for conditional logic later.
*   [ ] **1.4: Adapt Caching**: Ensure the existing caching mechanisms in Redis and MongoDB can handle cryptocurrency data by using appropriate keys (e.g., `crypto:bitcoin`).

#### **Phase 2: Adapting the Multi-Agent System**

Now we adapt the AI agents. The `Fundamentals Analyst` for stocks is not applicable to crypto, so we will create a new, specialized agent.

*   [ ] **2.1: Adapt `Market Analyst`**: This agent's role (technical analysis) is largely the same for stocks and crypto. The main change is pointing it to the new crypto data source for price, volume, and indicator calculations.
*   [ ] **2.2: Create `CryptoProjectAnalyst` Agent**: This is the most critical step. This new agent will replace the `Fundamentals Analyst`. Its responsibilities will be to analyze:
    *   **Tokenomics**: Supply, distribution, inflation/deflation mechanics.
    *   **Whitepaper**: The project's goals, technology, and value proposition.
    *   **Team & Community**: The credibility of the development team and the strength of the community.
    *   **Roadmap & Utility**: The project's future plans and the token's actual use case.
*   [ ] **2.3: Develop Tools for `CryptoProjectAnalyst`**: This agent will need new tools to fetch the data for its analysis, likely from the CoinGecko API (which provides much of this info).
*   [ ] **2.4: Update News & Sentiment Analysts**: The existing `NewsAnalyst` and `SocialMediaAnalyst` need to be given new, crypto-specific data sources (e.g., APIs for CryptoPanic, Coindesk, and tools to scan specific subreddits or X (Twitter) accounts).
*   [ ] **2.5: Modify the `TradingAgentsGraph`**: Add conditional routing logic. When the `market_type` is `'crypto'`, the graph should invoke the `CryptoProjectAnalyst` instead of the `FundamentalsAnalyst`.

#### **Phase 3: Advanced On-Chain & DeFi Analysis (Optional but Recommended)**

To make the tool truly powerful, we should add agents that can analyze on-chain data.

*   [ ] **3.1: Integrate On-Chain Data Source**: Add a new data fetcher for on-chain metrics.
    *   **Recommendation**: Use the **Glassnode API** for comprehensive metrics, or a free alternative like the Dune Analytics API for specific queries.
*   [ ] **3.2: Create `OnChainAnalyst` Agent**: A new agent specialized in interpreting on-chain data.
*   [ ] **3.3: Develop On-Chain Tools**: Create tools for this agent to fetch key metrics like:
    *   Active wallet addresses
    *   Transaction volume and count
    *   Total Value Locked (TVL) for DeFi projects
    *   Staking data and network hash rates
*   [ ] **3.4: Incorporate into Graph**: Add the `OnChainAnalyst` to the parallel analysis phase, so its report is available to the researcher agents.

#### **Phase 4: UI/UX Integration**

This phase ensures the user can actually use the new functionality.

*   [ ] **4.1: Update Market Selection**: Add "Cryptocurrency" to the market selection dropdown in the Streamlit web interface.
*   [ ] **4.2: Update Ticker Input**: Modify the stock symbol input field to accept cryptocurrency tickers (e.g., `BTC-USD`, `ETH`) and provide examples to the user. Input validation should be updated.
*   [ ] **4.3: Update Report Template**: The final report view needs to be updated to show the new, crypto-specific analysis sections like "Tokenomics" and "On-Chain Analysis".

#### **Phase 5: Finalization & Documentation**

The final steps to make the feature complete and maintainable.

*   [ ] **5.1: Update Configuration Files**: Add any new API key requirements (e.g., `COINGECKO_API_KEY`) to the `.env.example` file.
*   [ ] **5.2: Create Documentation**: Write a new guide in the `docs/usage/` folder explaining how to use the cryptocurrency analysis feature, what data sources are used, and how to interpret the results.
*   [ ] **5.3: Update Dependencies**: Add any new Python libraries (e.g., `pycoingecko`) to the `requirements.txt` and `pyproject.toml` files.
*   [ ] **5.4: Testing**: Create a new set of integration tests to validate the entire crypto analysis workflow, from data fetching to report generation.

This plan provides a clear roadmap. I would recommend starting with Phase 1 and progressing sequentially. I'm ready to help you implement the first step whenever you are.