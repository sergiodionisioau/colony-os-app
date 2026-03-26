# Cost Management Configuration

## 1. AWS Cost Alerts

### Budget Configuration
```json
{
  "budgets": [
    {
      "name": "COE-Kernel-Monthly",
      "amount": 500,
      "currency": "USD",
      "time_unit": "MONTHLY",
      "thresholds": [
        {"percentage": 50, "action": "email"},
        {"percentage": 80, "action": "email_sns"},
        {"percentage": 100, "action": "email_sns_stop"}
      ]
    },
    {
      "name": "COE-Kernel-Daily",
      "amount": 20,
      "currency": "USD",
      "time_unit": "DAILY",
      "thresholds": [
        {"percentage": 100, "action": "email"}
      ]
    }
  ]
}
```

### Cost Allocation Tags
- `Project`: coe-kernel
- `Environment`: production|staging|development
- `Component`: api|database|cache|orchestrator
- `Business`: biz-001|biz-002|biz-003|biz-004

## 2. Resource Limits

### Container Resource Limits
```yaml
# Docker Compose resource limits
services:
  appserver1:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
  
  postgres:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
  
  redis-node1:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
```

### Kubernetes Resource Limits (Future)
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: coe-kernel-quota
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "20"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: coe-kernel-limits
spec:
  limits:
  - default:
      cpu: "1"
      memory: 1Gi
    defaultRequest:
      cpu: "100m"
      memory: 256Mi
    type: Container
```

## 3. Auto-Shutdown for Non-Prod

### Development Environment Schedule
```bash
#!/bin/bash
# /scripts/auto-shutdown.sh

ENVIRONMENT=${ENVIRONMENT:-development}
CURRENT_HOUR=$(date +%H)
DAY_OF_WEEK=$(date +%u)  # 1-5 = Mon-Fri

# Shutdown dev/staging outside business hours
if [[ "$ENVIRONMENT" != "production" ]]; then
    # Shutdown after 8 PM and before 7 AM
    if [[ $CURRENT_HOUR -ge 20 ]] || [[ $CURRENT_HOUR -lt 7 ]]; then
        echo "[$ENVIRONMENT] Auto-shutdown triggered"
        docker-compose down
        exit 0
    fi
    
    # Shutdown on weekends
    if [[ $DAY_OF_WEEK -ge 6 ]]; then
        echo "[$ENVIRONMENT] Weekend shutdown triggered"
        docker-compose down
        exit 0
    fi
fi

echo "[$ENVIRONMENT] Keeping services running"
```

### Cron Schedule
```cron
# Auto-shutdown non-prod environments
0 20 * * 1-5 /home/coe/.openclaw/workspace/infrastructure/scripts/auto-shutdown.sh
0 7 * * 1-5 /home/coe/.openclaw/workspace/infrastructure/scripts/auto-startup.sh
```

## 4. Instance Right-Sizing

### Current vs Optimized

| Component | Current | Optimized | Savings |
|-----------|---------|-----------|---------|
| App Server | t3.large (2 vCPU, 8GB) | t3.medium (2 vCPU, 4GB) | 50% |
| PostgreSQL | db.r5.large | db.t3.medium | 60% |
| Redis | cache.r5.large | cache.t3.micro | 75% |
| **Total Monthly** | **~$450** | **~$180** | **60%** |

### Reserved Instance Strategy
```yaml
# 1-year reserved instances (baseline capacity)
reserved_instances:
  - type: t3.medium
    count: 2
    term: 1_year
    payment: partial_upfront
    savings: 40%
  
  - type: db.t3.medium
    count: 1
    term: 1_year
    payment: all_upfront
    savings: 45%

# On-demand for burst capacity
on_demand:
  max_instances: 5
  auto_scaling: true
```

## 5. OpenAI API Cost Monitoring

### Token Usage Tracking
```python
# /coe-kernel/monitoring/openai_costs.py

import os
from typing import Dict
from dataclasses import dataclass

@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float

# Pricing (as of 2026-03-26)
PRICING = {
    "gpt-4.1-mini": {
        "input": 0.00000015,   # $0.15 per 1M tokens
        "output": 0.0000006,   # $0.60 per 1M tokens
    },
    "text-embedding-3-small": {
        "input": 0.00000002,   # $0.02 per 1M tokens
    }
}

class OpenAICostTracker:
    def __init__(self):
        self.usage: Dict[str, TokenUsage] = {}
        self.daily_budget = float(os.getenv("OPENAI_DAILY_BUDGET", "10.0"))
    
    def track_usage(self, model: str, prompt_tokens: int, completion_tokens: int = 0):
        """Track API usage and calculate costs."""
        if model not in PRICING:
            return
        
        pricing = PRICING[model]
        input_cost = prompt_tokens * pricing.get("input", 0)
        output_cost = completion_tokens * pricing.get("output", 0)
        total_cost = input_cost + output_cost
        
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=total_cost
        )
        
        self.usage[model] = usage
        
        # Alert if approaching budget
        total_daily = sum(u.cost_usd for u in self.usage.values())
        if total_daily > self.daily_budget * 0.8:
            self._send_alert(f"OpenAI API at 80% of daily budget: ${total_daily:.2f}")
    
    def get_cost_report(self) -> Dict:
        """Generate cost report."""
        total_cost = sum(u.cost_usd for u in self.usage.values())
        total_tokens = sum(u.total_tokens for u in self.usage.values())
        
        return {
            "total_cost_usd": round(total_cost, 4),
            "total_tokens": total_tokens,
            "daily_budget": self.daily_budget,
            "budget_used_percent": round((total_cost / self.daily_budget) * 100, 2),
            "by_model": {
                model: {
                    "tokens": u.total_tokens,
                    "cost_usd": round(u.cost_usd, 6)
                }
                for model, u in self.usage.items()
            }
        }
```

### Cost Optimization Strategies
1. **Embedding Caching:** Cache embeddings to reduce API calls by ~70%
2. **Batch Processing:** Batch embedding requests (32 per batch)
3. **Model Selection:** Use gpt-4.1-mini for most tasks
4. **Token Optimization:** Truncate long inputs, use efficient prompts

## 6. Cost Dashboard

### Metrics to Track
```yaml
dashboard_metrics:
  - name: daily_compute_cost
    source: aws_cloudwatch
    aggregation: sum
    period: 1d
  
  - name: openai_api_cost
    source: custom_tracker
    aggregation: sum
    period: 1d
  
  - name: database_storage
    source: aws_rds
    aggregation: average
    period: 1h
  
  - name: cache_hit_rate
    source: redis
    aggregation: average
    period: 5m
  
  - name: requests_per_dollar
    source: calculated
    formula: total_requests / total_cost
    period: 1h
```

### Estimated Monthly Costs

| Service | Baseline | Optimized | Notes |
|---------|----------|-----------|-------|
| EC2 (App Servers) | $140 | $70 | 2x t3.medium reserved |
| RDS (PostgreSQL) | $200 | $80 | db.t3.medium reserved |
| ElastiCache (Redis) | $100 | $25 | cache.t3.micro |
| OpenAI API | $150 | $50 | With caching & batching |
| Data Transfer | $30 | $20 | Optimized routing |
| Storage (EBS/S3) | $50 | $40 | Lifecycle policies |
| **Total** | **$670** | **$285** | **57% savings** |

---
*Report generated: 2026-03-26*
*Currency: USD*
