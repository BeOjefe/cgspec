# 04-ARCHITECTURE: Physical System Architecture, Ports & Adapters & Governance

> **Stage 3 (Architecture): Modular Topology, Interface Decoupling, Physical DDL & MCP Bridge**

---

## 1. Modular Boundaries & Ports & Adapters (Hexagonal Architecture)

CGSpec enforces strict separation between domain logic and external infrastructure across all projects:

```mermaid
flowchart TB
    subgraph DrivingAdapters["Driving Adapters (Inbound)"]
        CLI["CLI Commands / TUI"]
        HTTP["HTTP API / Fastify / Express"]
        MCP["Model Context Protocol (MCP) Server"]
    end

    subgraph CoreDomain["Core Domain (Pure Logic)"]
        PORTS["Inbound & Outbound Ports (Interfaces)"]
        USECASES["Application Use Cases & Workflows"]
        ENTITIES["Domain Entities & Mental Model"]
    end

    subgraph DrivenAdapters["Driven Adapters (Outbound)"]
        DB["PostgreSQL / SQLite Storage Adapter"]
        CRYPTO["Local AES-256-GCM / Vault Adapter"]
        GIT["Serialized Git Queue Adapter"]
    end

    CLI & HTTP & MCP --> PORTS
    PORTS --> USECASES
    USECASES --> ENTITIES
    USECASES --> DrivenAdapters
```

- **Hexagonal Isolation:** The core domain logic has zero dependencies on databases, ORMs, or third-party web frameworks.
- **Interchangeable Adapters:** Infrastructure can be swapped (e.g. SQLite to PostgreSQL, or Local FS to S3) via Tier 1 module swaps without altering domain models or UI screens.

---

## 2. Multi-Agent Governance & Supervised Peer Council Architecture

To eliminate single-model sycophancy and architectural blind spots, major technical choices are evaluated by a Supervised 3-Agent Peer Debate Council:

```mermaid
sequenceDiagram
    autonumber
    actor User as Human Architect
    participant Main as Main Agent (Primary Chat Session)
    participant Sup as Council Supervisor & Inspector (Background Pane)
    participant D1 as Debater 1 (Systems & Modularity)
    participant D2 as Debater 2 (Adversarial Security)
    participant D3 as Debater 3 (Pragmatic DX & Ship Speed)

    User->>Main: Locks architectural debate topic
    Main->>User: Displays High-Information Briefing (Question, Tension, Target ADR)
    Main->>Sup: Spawns ONLY Supervisor via invoke_subagent
    Sup->>D1: Spawns Debaters in background workspace
    Sup->>D2: (debater turn completions stay 100% inside background pane)
    Sup->>D3: 

    loop For Each Round k = 1 to N
        Sup->>D1: Open Round k prompt
        D1->>D2: Direct peer argument
        D2->>D3: Direct peer counter-attack
        D3->>D1: Direct peer synthesis
        D1 & D2 & D3->>Sup: Submit Round k position to disk
        Sup->>Sup: Synthesizes round-0k.md
        Sup-->>Main: LIVE INSPECTOR REPORT: 3-bullet summary of clash & shifts
        Main-->>User: Displays clean 3-line round progress
    end

    Sup->>Sup: Terminate debaters, write summary.md, draft docs/adr/ADR-NNN.md
    Sup-->>Main: Final verdict + path to ADR-NNN.md
    Main-->>User: Presents consolidated ADR proposal for explicit human approval
```

- **Main Chat Insulation:** The Main Agent spawns **only** the `Council Supervisor & Inspector`. Zero debater turn completions touch the user's primary chat.
- **Atomic ADR Gate (Law 7):** The debate produces a draft ADR with `Status: Proposed`. It only transitions to `Status: Accepted` upon explicit human sign-off.

---

## 3. Dual Storage & MCP Integration

CGSpec supports two operational modes without vendor lock-in:

1. **Local Mode (Offline Git Repository):**
   - Decisions logged to `docs/.memlog.md`.
   - Spines derived into `docs/00..05-*.md`.
   - Integrates with any AI coding agent via standard Markdown.

2. **Connected Team Mode (CortexGate MCP):**
   - Synchronizes specs and decisions across multiple agents and squad members.
   - Enforces **Resource Ownership (`Owner`)** and **Granular Permissions (`read | invoke | propose_edit | write | share | admin`)**.
