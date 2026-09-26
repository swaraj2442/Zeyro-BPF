# Zeyro Trade Sentinel

**Behavioral Risk Intelligence for Trade Finance**

Built for the **BITSoM Vertex Buildathon (BFSI AI Track)** by team Zeyro.

## Overview

Trade finance is inherently a network problem. An exposure involves an exporter, importer, bank, factor, invoice, shipment, insurer, and multiple payment counterparties. Traditional systems evaluate these individually (document-centric or transaction-centric). 

**Zeyro Trade Sentinel** is a relationship-centric behavioral graph intelligence layer. Instead of just looking at isolated transactions, it maps the entire trade ecosystem to detect anomalies such as **duplicate invoice financing**—where an exporter submits the same (or slightly altered) invoice to multiple financiers.

## Features

- **Behavioral Graph Engine**: Dynamically computes 8 behavioral features per node (e.g., fan-in/fan-out, pass-through ratio, velocity) and combines them into a risk score without hardcoded verdicts.
- **Duplicate Invoice Detection**: Specifically targeted at uncovering overlapping invoice submissions across multiple financiers (similar to real-world fraud cases like the PNB fraud or solutions like MonetaGo).
- **Explainable AI Investigation**: An integrated Agent (powered by Groq / `gpt-oss-120b`) reads the graph evidence and dynamically generates a markdown investigation note to explain *why* an entity was flagged.
- **Synthetic Data**: 100% dynamically generated synthetic trade data. No real confidential, financial, or PII data is used.
- **Interactive Graph UI**: A frontend that renders the transaction graph and provides a 4-point workflow view (Counterparty Intelligence, Transaction Intelligence, Early Warning, Investigation).

## Architecture

```
Trade Data → Behavioural Graph → Risk Intelligence → Decision

  EXPORTER → INVOICE → IMPORTER
                │           │
                ▼           ▼
            SHIPMENT      BANK
                │           │
                └─────┬─────┘
                      ▼
             TRANSACTION GRAPH
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
  Counterparty    Money Flow    Behaviour
  relationships    patterns    over time
        └─────────────┼─────────────┘
                      ▼
         ZEYRO BEHAVIOURAL INTELLIGENCE
```

## Quick Start

### 1. Backend Setup

The backend requires Python and uses FastAPI.

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies (using pip or uv)
pip install -r requirements.txt

# Start the API server
uvicorn api:app --reload --port 8000
```

### 2. Frontend Setup

The frontend is a Vite + React application.

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

The frontend will be available at `http://localhost:5173`. 

### 3. Environment Variables

Ensure you have a `.env` file in the root with any required API keys (e.g., `GROQ_API_KEY` for the AI agent capabilities).

## Demo Guide

For the buildathon pitch:
1. **The Problem**: Open with the PNB/Nirav Modi fraud as the real-world stakes—trade finance is a network problem, not a document problem.
2. **The Hard Case**: The frontend auto-loads a clean "hard case" (Seed 107, `FRAUD_0000` with high risk due to duplicate-invoice evidence). 
3. **Agent Note**: Click the flagged entity to see the agent's explanation generated dynamically from the graph evidence.
4. **Behavioral Flags**: Highlight relationship-based flags (e.g., dormant counterparty suddenly active, or a short cycle) to show capabilities beyond simple invoice-fingerprint matching.

## Acknowledgements & Precedents

- **IFSCA ITFS Framework (2021)**: GIFT IFSC's dedicated trade-finance platform regulation.
- **MonetaGo**: Production precedent in India for duplicate invoice detection across TReDS exchanges.
- **FlowScope**: Academic precedent (AAAI) for graph-based money laundering detection.
