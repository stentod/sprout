#!/usr/bin/env python3
"""
Simple script to run phantom expense cleanup
Run this on your production server to clean up phantom expenses
"""

import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cleanup_phantom_expenses import cleanup_phantom_expenses, deactivate_old_recurring_expenses

def main():
    print("🧹 Phantom Expenses Cleanup Tool")
    print("=" * 40)
    
    # Run the analysis
    print("\n1. Analyzing phantom expenses...")
    results = cleanup_phantom_expenses()
    
    if not results:
        print("❌ Failed to run analysis")
        return
    
    print(f"\n📊 Analysis Results:")
    print(f"  - Duplicate expenses: {results['duplicates']}")
    print(f"  - Old recurring expenses: {results['old_recurring']}")
    print(f"  - Suspicious patterns: {results['suspicious_patterns']}")
    
    # If there are old recurring expenses, offer to deactivate them
    if results['old_recurring'] > 0:
        print(f"\n⚠️ Found {results['old_recurring']} old recurring expenses that could cause phantom expenses.")
        
        response = input("\nDo you want to deactivate these old recurring expenses? (y/N): ").strip().lower()
        
        if response in ['y', 'yes']:
            print("\n2. Deactivating old recurring expenses...")
            success = deactivate_old_recurring_expenses()
            
            if success:
                print("✅ Old recurring expenses deactivated successfully!")
                print("🎯 This should prevent future phantom expenses from old test data.")
            else:
                print("❌ Failed to deactivate old recurring expenses")
        else:
            print("⏭️ Skipping deactivation of old recurring expenses")
    else:
        print("\n✅ No old recurring expenses found - no action needed!")
    
    print("\n🎉 Cleanup complete!")
    print("\n💡 The app will now:")
    print("  - Only process recurring expenses created in the last 30 days")
    print("  - Skip duplicate expenses")
    print("  - Provide detailed logging for troubleshooting")

if __name__ == "__main__":
    main()
