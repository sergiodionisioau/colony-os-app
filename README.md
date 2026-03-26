# COE Kernel

A decentralized operating system for autonomous AI agents with reputation-based governance, hot-swappable business modules, and LangGraph orchestration.

## 🌟 Features

- **🔥 Hot-Swappable Modules**: Load, update, and swap business modules without downtime
- **🧠 Memory Layer**: Episodic and semantic memory with PGVector integration
- **🤖 LangGraph Orchestration**: Deterministic AI workflow execution
- **🏢 Multi-Tenant Business Support**: Manage multiple businesses with isolated data
- **📊 Real-time Dashboard**: Web-based monitoring and management UI
- **🔒 Zero Tolerance Security**: Ed25519 signatures, AST-guarded code, audit trails
- **⚡ High Performance**: Connection pooling, Redis caching, optimized embeddings

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        COE KERNEL v1.1.0                        │
├─────────────────────────────────────────────────────────────────┤
│  REST API (FastAPI)                                             │
│  ├── /v1/businesses      → Business CRUD                        │
│  ├── /v1/modules         → Module hot-swap                      │
│  ├── /v1/agents          → Agent management                     │
│  └── /                   → Dashboard UI                         │
├─────────────────────────────────────────────────────────────────┤
│  Business Module (Hot-Swappable)                                │
│  ├── 4 Sample Businesses                                        │
│  ├── Metrics Tracking                                           │
│  └── CRM Integration                                            │
├─────────────────────────────────────────────────────────────────┤
│  LangGraph Orchestrator                                         │
│  ├── StateGraph with 5 nodes                                    │
│  ├── Memory-aware planning                                      │
│  ├── Deterministic execution                                    │
│  └── Event-driven architecture                                  │
├─────────────────────────────────────────────────────────────────┤
│  Memory Layer                                                   │
│  ├── Episodic Memory (Task history)                             │
│  ├── Semantic Memory (Vector store + PGVector)                  │
│  ├── Context Retrieval (Top-k similarity)                       │
│  └── Learning Loop                                              │
├─────────────────────────────────────────────────────────────────┤
│  Kernel Core                                                    │
│  ├── Audit Ledger (Hash-chained)                                │
│  ├── Event Bus (Deterministic)                                  │
│  ├── Policy Engine (Zero implicit permissions)                  │
│  └── Module Loader (AST-guarded)                                │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 15+ with PGVector extension
- Redis 7+
- Docker & Docker Compose (optional)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/coe-kernel.git
cd coe-kernel

# Install dependencies
pip install -r coe-kernel/requirements.txt
pip install langgraph langchain-openai

# Set environment variables
export OPENAI_API_KEY=your_key_here
export POSTGRES_URL=postgresql://coe:coe_password@localhost:5432/coe_memory
export REDIS_URL=redis://localhost:6379

# Start infrastructure (optional - using Docker)
cd infrastructure
docker-compose up -d
cd ..

# Run the kernel
python start_with_business.py --port 8000
```

### Access the Dashboard

Once running, open your browser:
- **Dashboard**: http://localhost:8000/
- **Health Check**: http://localhost:8000/v1/health
- **API Docs**: http://localhost:8000/docs

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | System architecture and design |
| [API Reference](docs/api-reference.md) | REST API documentation |
| [Deployment](docs/DEPLOYMENT.md) | Production deployment guide |
| [Performance](docs/PERFORMANCE_OPTIMIZATION.md) | Optimization strategies |
| [Cost Management](docs/COST_MANAGEMENT.md) | Cost monitoring and controls |

## 🧪 Testing

```bash
# Run integration tests
python integration_test.py

# Run comprehensive test suite
python comprehensive_test.py

# Run specific test categories
pytest tests/unit/ -v
pytest tests/integration/ -v
```

## 🏢 Sample Businesses

The system comes pre-loaded with 4 sample businesses:

| ID | Name | Industry | Revenue | Agents |
|----|------|----------|---------|--------|
| biz-001 | Colony OS | Software Infra | $1,000 | 2 |
| biz-002 | Verified OS | Software Infra | $1,000 | 2 |
| biz-003 | App OS | Software Infra | $1,000 | 2 |
| biz-004 | Content OS | Software Infra | $1,000 | 2 |

## 🔧 API Examples

### List Businesses
```bash
curl http://localhost:8000/v1/businesses
```

### Get Business Stats
```bash
curl http://localhost:8000/v1/businesses/stats
```

### Hot-Swap Module
```bash
curl -X POST http://localhost:8000/v1/modules/business/hot-swap \
  -H "Content-Type: application/json" \
  -d '{"new_version_path": "modules/business-v2"}'
```

## 🛠️ Development

### Project Structure
```
coe-kernel/
├── coe-kernel/           # Core kernel code
│   ├── core/            # Kernel subsystems
│   ├── orchestrator/    # LangGraph orchestrator
│   ├── memory/          # Memory layer
│   ├── graphs/          # State graphs
│   └── api/             # REST API
├── modules/             # Hot-swappable modules
│   ├── business/        # Business module
│   └── crm/            # CRM module
├── infrastructure/      # Docker deployment
├── docs/               # Documentation
└── tests/              # Test suite
```

### Adding a New Module

1. Create module directory: `modules/my_module/`
2. Add `manifest.json` with module metadata
3. Implement `entry.py` with module logic
4. Sign with Ed25519: `python -m coe-kernel.modules.sign my_module`
5. Load: `loader.load("my_module")`

## 📊 Performance

| Metric | Value |
|--------|-------|
| API Response (p50) | 89ms |
| API Response (p99) | 320ms |
| Concurrent Requests | 1000+ |
| Memory Retrieval | 35ms |
| Embedding Generation | 220ms |

## 💰 Cost Estimates

| Environment | Monthly Cost |
|-------------|--------------|
| Development | ~$50 |
| Staging | ~$150 |
| Production | ~$285 |

See [Cost Management](docs/COST_MANAGEMENT.md) for details.

## 🔐 Security

- **Ed25519 Signatures**: All modules cryptographically signed
- **AST Guarding**: Code validation before execution
- **Zero Implicit Permissions**: Explicit permission model
- **Audit Ledger**: Tamper-evident operation logging
- **Input Validation**: SQL injection and XSS protection

## 🤝 Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- LangChain & LangGraph for the orchestration framework
- FastAPI for the high-performance API layer
- PostgreSQL & PGVector for vector storage
- The open-source community

---

**Version:** 1.1.0  
**Status:** Production Ready ✅  
**Integration Tests:** 94.4% Pass Rate
