# ============= check_critical_issues.py =============
"""
Location: scripts/check_critical_issues.py
Check for critical issues in the index and exit with error if found
Usage: python scripts/check_critical_issues.py TDS_DEV_INDEX.json
"""

import json
import sys

def check_critical_issues(index_path):
    with open(index_path, 'r') as f:
        index = json.load(f)
    
    critical = index.get('issues', {}).get('critical', [])
    mapping_issues = index.get('issues', {}).get('mapping_issues', [])
    
    # Define what makes an issue critical (excluding forward dependencies)
    critical_patterns = [
        'Missing critical function',
        'No PDF→Excel mapping',
        'ValidationEngine not found',
        'GovernmentTemplateBuilder not found'
    ]
    
    # Filter out forward dependency issues from critical
    filtered_critical = []
    for issue in critical:
        if 'Forward dependency' not in issue:
            filtered_critical.append(issue)
    
    # Count only non-forward-dependency critical issues
    critical_count = len(filtered_critical)
    
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
    
    # Check for forward dependencies (now just informational)
    forward_deps = index.get('dependency_graph', {}).get('forward_dependencies', 0)
    if forward_deps > 0:
        print(f"⚠️ INFO: {forward_deps} forward dependencies found (non-blocking)")
    
    # Print summary
    print(f"\n📊 Analysis Summary:")
    print(f"  Critical Issues: {critical_count}")
    print(f"  Mapping Issues: {len(mapping_issues)}")
    print(f"  Forward Dependencies: {forward_deps} (informational only)")
    
    if critical_count > 0:
        print("\n⚠️ Critical issues detected! Please fix before merging.")
        for issue in filtered_critical[:5]:  # Show first 5
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("\n✅ No critical issues found!")
        sys.exit(0)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python scripts/check_critical_issues.py TDS_DEV_INDEX.json")
        sys.exit(1)
    check_critical_issues(sys.argv[1])
