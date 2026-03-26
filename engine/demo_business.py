#!/usr/bin/env python3
"""Simple Kernel Demo with Business Module.

This script demonstrates the kernel with business module loaded.
For full functionality, install dependencies: pip install -r coe-kernel/requirements.txt
"""

import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "coe-kernel"))
sys.path.insert(0, str(Path(__file__).parent / "modules"))

print("=" * 70)
print("🔷 COE Kernel Demo — Business Module Hot-Swap")
print("=" * 70)

# Test imports
print("\n📦 Checking Components...")

try:
    from business.entry import Module as BusinessModule
    print("✓ Business Module: Available")

    # Create and test business module
    biz_mod = BusinessModule()
    print("✓ Business Module: Initialized")
    print(f"  - Loaded {len(biz_mod.businesses)} sample businesses:")
    for biz_id, biz in biz_mod.businesses.items():
        print(f"    • {biz.name} ({biz.industry}) - {biz.domain}")

    # Test healthcheck
    health = biz_mod.healthcheck()
    print(f"✓ Business Module Health: {'HEALTHY' if health else 'UNHEALTHY'}")

    # Test stats
    stats = biz_mod.get_module_stats()
    print("\n📊 Business Statistics:")
    print(f"  - Total Businesses: {stats['total_businesses']}")
    print(f"  - Active: {stats['active_businesses']}")
    print(f"  - Total Revenue: ${stats['total_revenue']:,.2f}")
    print(f"  - Total Leads: {stats['total_leads']:,}")
    print(f"  - Conversions: {stats['total_conversions']}")
    print(f"  - Conversion Rate: {stats['overall_conversion_rate']:.1f}%")
    print(f"  - Industries: {', '.join(stats['industries'])}")

except Exception as e:
    print(f"✗ Business Module Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("🚀 To start the full kernel with API server:")
print("   pip install -r coe-kernel/requirements.txt")
print("   python start_with_business.py")
print("=" * 70)

# Simulate API responses
print("\n📡 Simulated API Responses:")
print("-" * 40)

biz_mod = BusinessModule()

print("\nGET /v1/businesses")
print("{" + "}")
businesses = biz_mod.list_businesses()
for b in businesses[:3]:
    print(f"  {b['id']}: {b['name']} ({b['status']})")
print("  ...")

print("\nGET /v1/businesses/biz-001")
biz = biz_mod.get_business("biz-001")
if biz:
    print(f"  Name: {biz['name']}")
    print(f"  Industry: {biz['industry']}")
    print(f"  Revenue: ${biz['metrics']['revenue']:,.2f}")
    print(f"  Leads: {biz['metrics']['leads']}")

print("\nGET /v1/businesses/stats")
stats = biz_mod.get_module_stats()
print(f"  Total Revenue: ${stats['total_revenue']:,.2f}")
print(f"  Conversion Rate: {stats['overall_conversion_rate']:.1f}%")

print("\n" + "=" * 70)
print("✅ Business Module Demo Complete!")
print("=" * 70)
