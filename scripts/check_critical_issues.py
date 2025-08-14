#!/usr/bin/env python3
"""
Helper scripts for GitHub Actions workflow
1. check_critical_issues.py - Check for critical bugs
2. generate_bug_report.py - Generate markdown bug report
"""

# ============= check_critical_issues.py =============
"""
Check for critical issues in the index and exit with error if found
Usage: python check_critical_issues.py TDS_DEV_INDEX.json
"""

import json
import sys

def check_critical_issues(index_path):
    with open(index_path, 'r') as f:
        index = json.load(f)
    
    critical = index.get('issues', {}).get('critical', [])
    mapping_issues = index.get('issues', {}).get('mapping_issues', [])
    
    # Define what makes an issue critical
    critical_patterns = [
        'Forward dependency',
        'Missing critical function',
        'No PDF→Excel mapping',
        'undefined function',
        'ValidationEngine',
        'GovernmentTemplateBuilder'
    ]
    
    # Count critical issues
    critical_count = len(critical)
    
    # Check mapping pipeline
    mapping_pipeline = index.get('mapping_pipeline', {})
    pdf_functions = mapping_pipeline.get('pdf_extraction', {}).get('functions', [])
    excel_functions = mapping_pipeline.get('excel_processing', {}).get('functions', [])
    
    if not pdf_functions:
        print("❌ CRITICAL: No PDF extraction functions found!")
        critical_count += 1
    
    if not excel_functions:
        print("❌ CRITICAL: No Excel processing functions found!")
        critical_count += 1
    
    # Check for forward dependencies
    forward_deps = index.get('dependency_graph', {}).get('forward_dependencies', 0)
    if forward_deps > 0:
        print(f"❌ CRITICAL: {forward_deps} forward dependencies found!")
        critical_count += 1
    
    # Print summary
    print(f"\n📊 Analysis Summary:")
    print(f"  Critical Issues: {critical_count}")
    print(f"  Mapping Issues: {len(mapping_issues)}")
    print(f"  Forward Dependencies: {forward_deps}")
    
    if critical_count > 0:
        print("\n⚠️ Critical issues detected! Please fix before merging.")
        for issue in critical[:5]:  # Show first 5
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("\n✅ No critical issues found!")
        sys.exit(0)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python check_critical_issues.py TDS_DEV_INDEX.json")
        sys.exit(1)
    check_critical_issues(sys.argv[1])
