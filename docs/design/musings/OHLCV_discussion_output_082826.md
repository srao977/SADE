# Trading System Architecture Specification

This document defines the full system architecture for a multi‑feed, risk‑aware trading platform.  
It includes the complete component descriptions and a Mermaid diagram compatible with GitHub’s Markdown renderer.

---

## 1. System Overview

The trading system is structured into four vertically stacked layers:

1. **Data Ingestion Layer**  
2. **Analytics & Model Layer**  
3. **Risk & OMS Guardrails**  
4. **Execution & Harness Layer**

Data flows top‑down: market data enters through multiple feeds, is normalized and aggregated, drives models, passes through risk controls, and finally routes into paper or live execution.

---

## 2. Data Ingestion Layer

### 2.1 Primary Feed: Alpaca SIP
- **Type:** WebSocket real‑time market data  
- **Cost:** $99/mo  
- **Purpose:** Main low‑latency feed for OHLCV bar construction  
- **Responsibilities:**  
  - Stream trades/quotes  
  - Maintain connection health  
  - Reconnect on failure  
  - Provide high‑frequency tick data

### 2.2 Secondary / Backup Feed: Databento
- **Type:** WebSocket + REST (Pay‑As‑You‑Go)  
- **Purpose:** Redundant feed for failover and data quality checks  
- **Responsibilities:**  
  - Provide alternative real‑time data  
  - Supply historical data for gap filling  
  - Cost‑aware usage (only when needed)

### 2.3 Circuit Breaker & Failover Router
- **Purpose:** Protect downstream systems from bad or missing data  
- **Responsibilities:**  
  - Monitor latency, error rate, and completeness  
  - Trigger circuit breaks when thresholds are violated  
  - Switch routing between Alpaca SIP and Databento  
  - Emit unified normalized tick stream

### 2.4 OHLCV Bar Aggregator & REST Gap‑Filler
- **Purpose:** Convert tick streams into time‑bucketed OHLCV bars  
- **Responsibilities:**  
  - Aggregate ticks into bars (1s, 5s, 1m, etc.)  
  - Maintain rolling windows for indicators  
  - Detect missing or partial bars  
  - Use REST calls to backfill gaps  
  - Output clean continuous OHLCV series

---

## 3. Analytics & Model Layer

### Adaptive Model Engine
- **Purpose:** Generate trading signals and decision vectors  
- **Inputs:**  
  - OHLCV bars  
  - Derived features (volatility, spreads, microstructure metrics)  
- **Outputs:**  
  - Signals (long/short/flat + confidence)  
  - Decision vector (target size, entry/exit conditions)  
- **Responsibilities:**  
  - Feature engineering  
  - Model execution (rule‑based, statistical, ML)  
  - Regime adaptation  
  - Diagnostics (signal quality, hit rate)

---

## 4. Risk & OMS Guardrails

### OMS / Risk Guardrails
- **Purpose:** Enforce portfolio‑level and order‑level constraints  
- **Inputs:**  
  - Decision vector  
  - Current positions, PnL, risk metrics  
- **Constraints:**  
  - Max position & order size  
  - Leverage & drawdown limits  
  - Latency & slippage tolerance  
- **Outputs:**  
  - Sanitized, risk‑compliant order instructions  
  - Optional feedback to model layer

---

## 5. Execution & Harness Layer

### 5.1 Execution Router & Benchmarking Engine
- **Purpose:** Route validated orders to paper or live execution  
- **Responsibilities:**  
  - Decide routing mode  
  - Benchmark execution quality  
  - Log all decisions for audit and research

### 5.2 Paper Execution Benchmarking Engine
- **Purpose:** Simulate fills and PnL  
- **Responsibilities:**  
  - Model fills using market data  
  - Record simulated trades and PnL  
  - Provide safe environment for testing

### 5.3 Live Broker API (Alpaca / IBKR)
- **Purpose:** Execute real trades  
- **Responsibilities:**  
  - Translate internal orders to broker API  
  - Handle authentication and rate limits  
  - Confirm order status  
  - Stream live positions and PnL

---

## 6. Cross‑Cutting Concerns

### Logging & Observability
- Structured logs for feed health, model decisions, risk rejections, execution quality  
- Metrics for latency, slippage, error rates, circuit breaker triggers  

### Configuration & Environment
- Feed thresholds  
- Bar intervals  
- Risk limits  
- Routing mode (paper vs live)  
- Environments: dev, staging, production  

---

## 7. Mermaid Architecture Diagram

```mermaid
flowchart TD

    %% LAYER 1: DATA INGESTION
    subgraph L1[DATA INGESTION LAYER]
        A1[Primary Feed: Alpaca SIP\n(WebSocket / $99/mo)]
        A2[Secondary / Backup Feed:\nDatabento (Pay-As-You-Go)]

        CB[Circuit Breaker\n& Failover Router]

        AGG[OHLCV Bar Aggregator\n+ REST Gap-Filler]

        A1 --> CB
        A2 --> CB
        CB --> AGG
    end

    %% LAYER 2: ANALYTICS & MODEL
    subgraph L2[ANALYTICS & MODEL LAYER]
        M1[Adaptive Model Engine\n(Signals & Decision Vector)]
    end

    %% LAYER 3: RISK & OMS GUARDRAILS
    subgraph L3[RISK & OMS GUARDRAILS]
        R1[OMS / Risk Guardrails\n- Max Position & Order Size\n- Leverage & Drawdown Limits\n- Latency & Slippage Tolerance]
    end

    %% LAYER 4: EXECUTION & HARNESS
    subgraph L4[EXECUTION & HARNESS LAYER]
        ER[Execution Router &\nBenchmarking Engine]

        PE[Paper Execution\nBenchmarking Engine]
        LB[Live Broker API\n(Alpaca / IBKR)]

        ER --> PE
        ER --> LB
    end

    %% TOP-DOWN FLOW
    AGG --> M1
    M1 --> R1
    R1 --> ER
