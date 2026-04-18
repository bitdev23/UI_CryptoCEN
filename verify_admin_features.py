#!/usr/bin/env python3
"""
Admin Features Migration Verifier & Applier
Checks if required tables exist and applies migrations if needed.
Usage: python verify_admin_features.py --apply
"""

import sys
import os
from datetime import datetime

# Add app context
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def verify_tables(supabase):
    """Check if all required tables exist."""
    required_tables = [
        'notifications',
        'notification_templates',
        'error_logs',
        'error_alert_rules',
        'feature_flags',
        'feature_flag_overrides',
        'feature_flag_rollout_hash',
        'revenue_metrics',
        'cohort_analytics'
    ]
    
    print("\n🔍 Verifying tables exist...")
    missing_tables = []
    
    for table in required_tables:
        try:
            # Try to query the table to see if it exists
            result = supabase.table(table).select('1').limit(1).execute()
            print(f"  ✓ {table:<30} exists")
        except Exception as e:
            if 'not found' in str(e).lower() or '404' in str(e):
                missing_tables.append(table)
                print(f"  ✗ {table:<30} MISSING")
            else:
                print(f"  ? {table:<30} (error: {str(e)[:50]})")
    
    return len(missing_tables) == 0, missing_tables


def apply_migrations(supabase):
    """Apply database migrations from SQL file."""
    migration_file = os.path.join(
        os.path.dirname(__file__),
        'database',
        'admin_features_migration.sql'
    )
    
    if not os.path.exists(migration_file):
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    print(f"\n📝 Reading migration file: {migration_file}")
    with open(migration_file, 'r') as f:
        sql_content = f.read()
    
    # Split by semicolon to get individual statements
    statements = [
        s.strip() for s in sql_content.split(';')
        if s.strip() and not s.strip().startswith('--')
    ]
    
    print(f"📋 Found {len(statements)} SQL statements to execute")
    print("\n⚙️  Executing migrations...\n")
    
    # Try to execute each statement
    errors = []
    for i, stmt in enumerate(statements, 1):
        try:
            # Use raw SQL execution via Supabase RPC if possible
            # Otherwise, we'll use the REST API approach
            print(f"  [{i:2d}/{len(statements)}] {stmt[:60]:60s}...", end='', flush=True)
            
            # Execute via Supabase - for complex migrations, we may need
            # to use the Python client with different approaches
            supabase.rpc('exec_sql', {'sql': stmt}).execute()
            print(" ✓")
        except Exception as e:
            error_msg = str(e)
            # Some statements might fail but that's OK (e.g., IF NOT EXISTS failures in updates)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                print(" ✓ (already exists)")
            else:
                print(f" ✗")
                errors.append((stmt[:50], str(e)[:80]))
    
    if errors:
        print(f"\n⚠️  {len(errors)} statements had warnings:")
        for stmt, error in errors[:5]:  # Show first 5 errors
            print(f"  - {stmt}... → {error}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more")
    
    return len(errors) == 0


def verify_api_routes(app):
    """Verify that admin_features blueprint is registered."""
    print("\n🔌 Verifying API routes...")
    
    required_routes = [
        '/api/admin/features/notifications',
        '/api/admin/features/errors',
        '/api/admin/features/flags',
        '/api/admin/features/revenue/metrics'
    ]
    
    registered = False
    for blueprint in app.blueprints.values():
        if 'features' in str(blueprint):
            registered = True
            break
    
    if registered:
        print("  ✓ admin_features blueprint is registered")
    else:
        print("  ✗ admin_features blueprint NOT registered")
        print("    Ensure app.py has:")
        print("    from routes.admin_features import create_admin_features_blueprint")
        print("    app.register_blueprint(create_admin_features_blueprint(...))")
    
    return registered


def verify_template_ui(templates_dir):
    """Verify that admin dashboard has feature tabs."""
    print("\n🎨 Verifying frontend UI...")
    
    dashboard_file = os.path.join(templates_dir, 'admin_dashboard.html')
    if not os.path.exists(dashboard_file):
        print(f"  ✗ admin_dashboard.html not found")
        return False
    
    with open(dashboard_file, 'r') as f:
        content = f.read()
    
    features = {
        'Notifications': 'feature-tab-notifications',
        'Errors': 'feature-tab-errors',
        'Revenue': 'feature-tab-revenue',
        'Feature Flags': 'feature-tab-flags'
    }
    
    all_found = True
    for name, element_id in features.items():
        if element_id in content:
            print(f"  ✓ {name:20} UI tab found")
        else:
            print(f"  ✗ {name:20} UI tab NOT found")
            all_found = False
    
    return all_found


def print_status_report(supabase, app, templates_dir, all_ok):
    """Print comprehensive status report."""
    print("\n" + "=" * 60)
    print("ADMIN FEATURES SETUP STATUS")
    print("=" * 60)
    
    if all_ok:
        print("\n✅ ALL CHECKS PASSED")
        print("\nYou can now:")
        print("  1. Visit http://localhost:5000/admin/")
        print("  2. Click on tab buttons: 🔔 🎨 📊 🚩")
        print("  3. Send test notifications and errors")
        print("\nNext steps:")
        print("  - Guide: ADMIN_FEATURES_DEPLOYMENT.md")
        print("  - Backend: routes/admin_features.py")
        print("  - Frontend: templates/admin_dashboard.html")
    else:
        print("\n⚠️  SOME CHECKS FAILED")
        print("\nAction items:")
        print("  1. Run: python verify_admin_features.py --apply")
        print("  2. Check logs above for specific issues")
        print("  3. Review ADMIN_FEATURES_DEPLOYMENT.md")
    
    print("\n" + "=" * 60 + "\n")


def main():
    """Main verification flow."""
    apply_migrations_flag = '--apply' in sys.argv
    verbose = '--verbose' in sys.argv
    
    print("🚀 Admin Features Setup Verifier")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Import app context
    try:
        from app import app, supabase
        print("✓ Flask app loaded")
    except Exception as e:
        print(f"❌ Failed to load Flask app: {e}")
        sys.exit(1)
    
    # Get template directory
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    
    # Run verifications
    tables_ok, missing = verify_tables(supabase)
    routes_ok = verify_api_routes(app)
    ui_ok = verify_template_ui(templates_dir)
    
    all_ok = tables_ok and routes_ok and ui_ok
    
    # If not OK and user wants to apply, attempt migrations
    if not tables_ok and apply_migrations_flag:
        print("\n📦 Attempting to apply migrations...")
        try:
            apply_migrations(supabase)
            tables_ok, missing = verify_tables(supabase)
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            print("\n💡 Tip: Try manual migration via Supabase dashboard:")
            print("   1. Go to SQL Editor")
            print("   2. Copy contents of database/admin_features_migration.sql")
            print("   3. Execute the query")
    
    # Print status report
    print_status_report(supabase, app, templates_dir, all_ok)
    
    # Exit with appropriate code
    sys.exit(0 if all_ok else 1)


if __name__ == '__main__':
    main()
