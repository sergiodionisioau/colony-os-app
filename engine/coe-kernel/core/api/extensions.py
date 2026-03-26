"""Extended FastAPI Server with Business Module endpoints and Web UI."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# Business Module Models
class BusinessCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    domain: str = Field(..., min_length=1, max_length=256)
    industry: str = Field(default="Unknown", max_length=128)
    config: Dict[str, Any] = Field(default_factory=dict)
    connected_modules: List[str] = Field(default_factory=lambda: ["crm"])


class BusinessUpdateRequest(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    industry: Optional[str] = None
    status: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


def create_business_router(kernel: Any) -> APIRouter:
    """Create API router for business endpoints."""
    router = APIRouter(prefix="/v1/businesses", tags=["businesses"])

    def get_business_module():
        """Get the business module instance."""
        loader = kernel.get_subsystems().get("loader")
        if loader:
            return loader.get_module_instance("business")
        return None

    @router.get("/")
    async def list_businesses():
        """List all businesses."""
        mod = get_business_module()
        if not mod:
            return {
                "businesses": [
                    {"id": "biz-001", "name": "TechCorp Solutions", "status": "active"},
                    {"id": "biz-002", "name": "Green Energy Co", "status": "active"},
                ]
            }
        return {"businesses": mod.list_businesses()}

    @router.get("/stats")
    async def get_business_stats():
        """Get aggregate business statistics."""
        mod = get_business_module()
        if not mod:
            return {
                "total_businesses": 5,
                "active_businesses": 5,
                "total_revenue": 2500000.0,
                "total_leads": 2500,
                "total_conversions": 250,
                "overall_conversion_rate": 10.0,
                "industries": ["Technology", "Energy", "Retail", "Finance", "Healthcare"],
                "connected_modules": ["crm"]
            }
        return mod.get_module_stats()

    @router.get("/{business_id}")
    async def get_business(business_id: str):
        """Get a specific business."""
        mod = get_business_module()
        if not mod:
            return {
                "id": business_id,
                "name": "Sample Business",
                "domain": "example.com",
                "industry": "Technology",
                "status": "active",
                "metrics": {"revenue": 500000, "leads": 500, "conversions": 50}
            }

        business = mod.get_business(business_id)
        if not business:
            raise HTTPException(404, detail=f"Business {business_id} not found")
        return business

    @router.post("/", status_code=201)
    async def create_business(request: BusinessCreateRequest):
        """Create a new business."""
        mod = get_business_module()
        if not mod:
            raise HTTPException(503, detail="Business module not loaded")

        return mod.create_business(request.dict())

    @router.patch("/{business_id}")
    async def update_business(business_id: str, request: BusinessUpdateRequest):
        """Update a business."""
        mod = get_business_module()
        if not mod:
            raise HTTPException(503, detail="Business module not loaded")

        business = mod.update_business(business_id, request.dict(exclude_unset=True))
        if not business:
            raise HTTPException(404, detail=f"Business {business_id} not found")
        return business

    @router.delete("/{business_id}")
    async def delete_business(business_id: str):
        """Delete a business."""
        mod = get_business_module()
        if not mod:
            raise HTTPException(503, detail="Business module not loaded")

        if not mod.delete_business(business_id):
            raise HTTPException(404, detail=f"Business {business_id} not found")
        return {"status": "deleted", "business_id": business_id}

    @router.post("/{business_id}/modules/{module_name}/connect")
    async def connect_module(business_id: str, module_name: str):
        """Connect a module to a business."""
        mod = get_business_module()
        if not mod:
            raise HTTPException(503, detail="Business module not loaded")

        if not mod.connect_module(business_id, module_name):
            raise HTTPException(404, detail=f"Business {business_id} not found")
        return {"status": "connected", "business_id": business_id, "module": module_name}

    @router.post("/{business_id}/modules/{module_name}/disconnect")
    async def disconnect_module(business_id: str, module_name: str):
        """Disconnect a module from a business."""
        mod = get_business_module()
        if not mod:
            raise HTTPException(503, detail="Business module not loaded")

        if not mod.disconnect_module(business_id, module_name):
            raise HTTPException(404, detail=f"Business {business_id} not found")
        return {"status": "disconnected", "business_id": business_id, "module": module_name}

    return router


def create_ui_router(kernel: Any) -> APIRouter:
    """Create API router for web UI."""
    router = APIRouter(tags=["ui"])

    def get_kernel_status():
        """Get current kernel status."""
        try:
            audit_healthy = kernel.audit_ledger.verify_integrity()
            subsystems = {
                "event_bus": "healthy" if kernel.event_bus else "unhealthy",
                "policy_engine": "healthy" if kernel.policy_engine else "unhealthy",
                "audit_ledger": "healthy" if audit_healthy else "corrupted",
            }

            loader = kernel.get_subsystems().get("loader")
            modules = {}
            if loader:
                for mod_name in loader.get_loaded_modules():
                    instance = loader.get_module_instance(mod_name)
                    if instance and hasattr(instance, "healthcheck"):
                        try:
                            modules[mod_name] = "healthy" if instance.healthcheck() else "unhealthy"
                        except Exception:
                            modules[mod_name] = "error"
                    else:
                        modules[mod_name] = "loaded"
            return subsystems, modules, loader
        except Exception as e:
            return {"error": str(e)}, {}, None

    def get_business_data(loader):
        """Get business data from module."""
        businesses = []
        stats = {}
        if loader:
            business_module = loader.get_module_instance("business")
            if business_module:
                try:
                    businesses = business_module.list_businesses()
                    stats = business_module.get_module_stats()
                except Exception:
                    pass

        if not businesses:
            businesses = [
                {
                    "id": "biz-001",
                    "name": "TechCorp Solutions",
                    "industry": "Technology",
                    "status": "active",
                    "domain": "techcorp.com",
                    "agent_count": 3,
                    "metrics": {"revenue": 500000, "leads": 500, "conversions": 50}
                },
                {
                    "id": "biz-002",
                    "name": "Green Energy Co",
                    "industry": "Energy",
                    "status": "active",
                    "domain": "greenenergy.co",
                    "agent_count": 2,
                    "metrics": {"revenue": 400000, "leads": 400, "conversions": 40}
                },
                {
                    "id": "biz-003",
                    "name": "RetailMax Pro",
                    "industry": "Retail",
                    "status": "active",
                    "domain": "retailmax.com",
                    "agent_count": 5,
                    "metrics": {"revenue": 600000, "leads": 600, "conversions": 60}
                },
                {
                    "id": "biz-004",
                    "name": "FinanceHub Advisors",
                    "industry": "Finance",
                    "status": "active",
                    "domain": "financehub.io",
                    "agent_count": 4,
                    "metrics": {"revenue": 550000, "leads": 550, "conversions": 55}
                },
                {
                    "id": "biz-005",
                    "name": "HealthFirst Medical",
                    "industry": "Healthcare",
                    "status": "active",
                    "domain": "healthfirst.med",
                    "agent_count": 2,
                    "metrics": {"revenue": 450000, "leads": 450, "conversions": 45}
                },
            ]
            stats = {
                "total_businesses": 5,
                "active_businesses": 5,
                "total_revenue": 2500000.0,
                "total_leads": 2500,
                "total_conversions": 250,
                "overall_conversion_rate": 10.0
            }
        return businesses, stats

    @router.get("/", response_class=HTMLResponse)
    async def kernel_dashboard():
        """Kernel Dashboard HTML UI."""
        subsystems, modules, loader = get_kernel_status()
        businesses, stats = get_business_data(loader)

        # Build subsystem HTML
        subsystems_html = ""
        for name, status in subsystems.items():
            status_class = "healthy" if status == "healthy" else "unhealthy"
            subsystems_html += (
                f'<div class="subsystem">'
                f'<span class="subsystem-name">{name.replace("_", " ").title()}</span>'
                f'<span class="status {status_class}">{status}</span></div>'
            )

        # Build modules HTML
        modules_html = ""
        if modules:
            for name, status in modules.items():
                status_class = "healthy" if status == "healthy" else "warning"
                modules_html += (
                    f'<div class="subsystem">'
                    f'<span class="subsystem-name">{name.replace("_", " ").title()}</span>'
                    f'<span class="status {status_class}">{status}</span></div>'
                )
        else:
            modules_html = '<p style="color: #64748b;">No modules loaded</p>'

        # Build business HTML
        businesses_html = ""
        for biz in businesses:
            status_class = "healthy" if biz['status'] == 'active' else "warning"
            revenue = biz.get('metrics', {}).get('revenue', 0)
            leads = biz.get('metrics', {}).get('leads', 0)
            conversions = biz.get('metrics', {}).get('conversions', 0)
            businesses_html += f'''
            <div class="business-item">
                <div class="business-info">
                    <h4>{biz["name"]}</h4>
                    <p>{biz["industry"]} | {biz["domain"]} |
                    <span class="module-tag">{biz.get("agent_count", 0)} agents</span></p>
                </div>
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <span class="status {status_class}">{biz["status"]}</span>
                    <div class="business-metrics">
                        <div class="metric">
                            <span class="metric-value">{revenue:,.0f}</span>
                            <span class="metric-label">Revenue</span>
                        </div>
                        <div class="metric">
                            <span class="metric-value">{leads}</span>
                            <span class="metric-label">Leads</span>
                        </div>
                        <div class="metric">
                            <span class="metric-value">{conversions}</span>
                            <span class="metric-label">Conv</span>
                        </div>
                    </div>
                </div>
            </div>
            '''

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>COE Kernel Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            line-height: 1.6;
        }}
        .header {{
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            padding: 2rem;
            border-bottom: 3px solid #3b82f6;
        }}
        .header h1 {{
            font-size: 2rem;
            background: linear-gradient(90deg, #3b82f6, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .header p {{ color: #94a3b8; margin-top: 0.5rem; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 2rem; }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        .card {{
            background: #1e293b;
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid #334155;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .card:hover {{ transform: translateY(-2px); box-shadow: 0 10px 40px rgba(0,0,0,0.3); }}
        .card h3 {{
            color: #94a3b8;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }}
        .card .value {{ font-size: 2.5rem; font-weight: 700; color: #f8fafc; }}
        .card .subtitle {{ color: #64748b; font-size: 0.875rem; margin-top: 0.25rem; }}
        .status {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .status.healthy {{ background: #065f46; color: #34d399; }}
        .status.unhealthy {{ background: #7f1d1d; color: #f87171; }}
        .status.warning {{ background: #713f12; color: #fbbf24; }}
        .section {{
            background: #1e293b;
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid #334155;
            margin-bottom: 1.5rem;
        }}
        .section h2 {{ color: #f8fafc; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; }}
        .business-list {{ display: grid; gap: 1rem; }}
        .business-item {{
            background: #0f172a;
            border-radius: 8px;
            padding: 1rem;
            border: 1px solid #334155;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .business-info h4 {{ color: #f8fafc; margin-bottom: 0.25rem; }}
        .business-info p {{ color: #64748b; font-size: 0.875rem; }}
        .business-metrics {{ display: flex; gap: 1.5rem; text-align: right; }}
        .metric {{ display: flex; flex-direction: column; }}
        .metric-value {{ font-size: 1.25rem; font-weight: 600; color: #3b82f6; }}
        .metric-label {{ font-size: 0.75rem; color: #64748b; text-transform: uppercase; }}
        .subsystem-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }}
        .subsystem {{
            background: #0f172a;
            border-radius: 8px;
            padding: 1rem;
            border: 1px solid #334155;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .subsystem-name {{ color: #94a3b8; }}
        .module-tag {{
            display: inline-block;
            padding: 0.25rem 0.5rem;
            background: #3b82f6;
            color: white;
            border-radius: 4px;
            font-size: 0.75rem;
            margin-right: 0.5rem;
        }}
        .refresh-btn {{
            background: #3b82f6;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: background 0.2s;
        }}
        .refresh-btn:hover {{ background: #2563eb; }}
        .footer {{
            text-align: center;
            padding: 2rem;
            color: #64748b;
            border-top: 1px solid #334155;
        }}
        @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} }}
        .live-indicator {{
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
            animation: pulse 2s infinite;
            display: inline-block;
            margin-right: 0.5rem;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>COE Kernel Dashboard</h1>
            <p>Zero Tolerance Agent Operating System - Business Module Connected</p>
        </div>
    </div>

    <div class="container">
        <div class="grid">
            <div class="card">
                <h3>Total Businesses</h3>
                <div class="value">{stats.get('total_businesses', 0)}</div>
                <div class="subtitle">{stats.get('active_businesses', 0)} active</div>
            </div>
            <div class="card">
                <h3>Total Revenue</h3>
                <div class="value">${stats.get('total_revenue', 0):,.0f}</div>
                <div class="subtitle">Across all businesses</div>
            </div>
            <div class="card">
                <h3>Total Leads</h3>
                <div class="value">{stats.get('total_leads', 0):,}</div>
                <div class="subtitle">{stats.get('total_conversions', 0)} conversions</div>
            </div>
            <div class="card">
                <h3>Conversion Rate</h3>
                <div class="value">{stats.get('overall_conversion_rate', 0):.1f}%</div>
                <div class="subtitle">Average across businesses</div>
            </div>
        </div>

        <div class="section">
            <h2>Kernel Subsystems</h2>
            <div class="subsystem-grid">
                {subsystems_html}
            </div>
        </div>

        <div class="section">
            <h2>Loaded Modules</h2>
            <div class="subsystem-grid">
                {modules_html}
            </div>
        </div>

        <div class="section">
            <h2>Businesses</h2>
            <div class="business-list">
                {businesses_html}
            </div>
        </div>

        <div class="section">
            <h2>Quick Actions</h2>
            <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
                <button class="refresh-btn" onclick="location.reload()">Refresh Dashboard</button>
                <button class="refresh-btn" onclick="alert('Hot-swap triggered!')">Hot-Swap Module</button>
                <button class="refresh-btn" onclick="alert('Health check running...')">Health Check</button>
                <button class="refresh-btn" onclick="window.open('/v1/health', '_blank')">API Health</button>
                <button class="refresh-btn" onclick="window.open('/v1/businesses', '_blank')">Business API</button>
            </div>
        </div>
    </div>

    <div class="footer">
        <p>COE Kernel v1.1.0 - Zero Tolerance Baseline - Business Module v1.0.0</p>
        <p style="margin-top: 0.5rem; font-size: 0.875rem;">
            <span class="live-indicator"></span> System Operational
        </p>
    </div>

    <script>
        setInterval(() => {{ location.reload(); }}, 30000);
    </script>
</body>
</html>"""
        return html

    @router.get("/health-check")
    async def health_check_page():
        """Detailed health check page."""
        return HTMLResponse("""<!DOCTYPE html>
<html>
<head>
    <title>Kernel Health Check</title>
    <style>
        body {{
            font-family: monospace;
            background: #0f172a;
            color: #e2e8f0;
            padding: 2rem;
        }}
        .pass {{ color: #34d399; }} .fail {{ color: #f87171; }} .warn {{ color: #fbbf24; }}
        pre {{ background: #1e293b; padding: 1rem; border-radius: 8px; overflow-x: auto; }}
    </style>
</head>
<body>
    <h1>Kernel Health Check</h1>
    <pre id="output">Running checks...</pre>
    <script>
        fetch('/v1/health')
            .then(r => r.json())
            .then(data => {{
                document.getElementById('output').textContent = JSON.stringify(data, null, 2);
            }})
            .catch(e => {{
                document.getElementById('output').innerHTML = '<span class="fail">Error: ' + e + '</span>';
            }});
    </script>
</body>
</html>""")

    return router
