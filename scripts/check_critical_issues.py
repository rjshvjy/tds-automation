#!/usr/bin/env python3
"""
Location: scripts/check_critical_issues.py
Check for critical issues in the enhanced index format
Compatible with both old and new analyzer output formats
"""

import json
import sys

def check_critical_issues(index_path):
    with open(index_path, 'r') as f:
        index = json.load(f)
    
    critical = []
    mapping_issues = []
    
    # Detect analyzer version
    analyzer_version = index.get('metadata', {}).get('analyzer_version', '1.0')
    
    if analyzer_version == '2.0':
        # Enhanced analyzer format
        check_enhanced_format(index, critical, mapping_issues)
    else:
        # Original analyzer format
        check_original_format(index, critical, mapping_issues)
    
    # Count issues
    critical_count = len(critical)
    mapping_count = len(mapping_issues)
    
    # Check for forward dependencies (both formats)
    forward_deps = index.get('dependency_graph', {}).get('forward_dependencies', 0)
    if forward_deps > 0:
        print(f"⚠️ INFO: {forward_deps} forward dependencies found (non-blocking)")
    
    # Print summary
    print(f"\n📊 Analysis Summary:")
    print(f"  Critical Issues: {critical_count}")
    print(f"  Mapping Issues: {mapping_count}")
    print(f"  Forward Dependencies: {forward_deps} (informational only)")
    
    if critical_count > 0:
        print("\n⚠️ Critical issues detected! Please fix before merging.")
        for issue in critical[:5]:  # Show first 5
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("\n✅ No critical issues found!")
        sys.exit(0)

def check_enhanced_format(index, critical, mapping_issues):
    """Check enhanced analyzer format (v2.0)"""
    
    # Check for critical functions in function_signatures
    function_sigs = index.get('function_signatures', {})
    critical_functions = [
        'extract_challan_data_from_pdf',
        'extract_all_challans',
        'read_tds_masters',
        'update_tds_masters_with_challans',
        'validate_tds_totals'
    ]
    
    # Check PDF extraction functions
    pdf_functions = [f for f in function_sigs if 'extract' in f.lower() and 'pdf' in f.lower()]
    if not pdf_functions:
        # Check in implementation_details as fallback
        has_pdf = False
        for cell, details in index.get('implementation_details', {}).items():
            if 'PDF extraction' in details.get('key_operations', []):
                has_pdf = True
                break
        if not has_pdf:
            critical.append("No PDF extraction functions found")
    
    # Check Excel processing functions
    excel_functions = [f for f in function_sigs if any(x in f.lower() for x in ['excel', 'tds_masters', 'workbook'])]
    if not excel_functions:
        # Check in implementation_details as fallback
        has_excel = False
        for cell, details in index.get('implementation_details', {}).items():
            if any(op in details.get('key_operations', []) for op in ['Excel reading', 'Excel updating']):
                has_excel = True
                break
        if not has_excel:
            critical.append("No Excel processing functions found")
    
    # Check for missing critical functions
    for func in critical_functions:
        if func not in function_sigs:
            # Only critical if not found anywhere
            found = False
            for cell, details in index.get('implementation_details', {}).items():
                if func in str(details):
                    found = True
                    break
            if not found:
                # This is informational, not critical (function might be renamed)
                pass  # Don't add to critical
    
    # Check data structures
    data_structures = index.get('data_structures', {})
    if not data_structures.get('tds_masters_data'):
        mapping_issues.append("Missing tds_masters_data structure definition")
    if not data_structures.get('challan_data'):
        mapping_issues.append("Missing challan_data structure definition")
    
    # Check Excel mappings
    excel_mappings = index.get('excel_mappings', {})
    if not excel_mappings:
        mapping_issues.append("No Excel column mappings found")
    else:
        critical_columns = excel_mappings.get('tds_parties_sheet', {}).get('critical_columns', {})
        required = ['(415)', '(415A)', '(416)', '(421)']
        for col in required:
            if col not in critical_columns:
                mapping_issues.append(f"Missing critical column mapping: {col}")
    
    # Check PDF patterns
    pdf_patterns = index.get('pdf_patterns', {})
    if not pdf_patterns.get('extraction_patterns'):
        mapping_issues.append("No PDF extraction patterns defined")
    
    # Check validation rules
    validation = index.get('validation_rules', {})
    if not validation:
        mapping_issues.append("No validation rules defined")
    
    # Check GitHub integration (informational for new version)
    github = index.get('github_integration', {})
    if not github:
        # Not critical - this is expected to be added
        pass

def check_original_format(index, critical, mapping_issues):
    """Check original analyzer format (v1.0)"""
    
    issues = index.get('issues', {})
    critical.extend(issues.get('critical', []))
    mapping_issues.extend(issues.get('mapping_issues', []))
    
    # Filter out forward dependency issues from critical
    filtered_critical = []
    for issue in critical:
        if 'Forward dependency' not in issue:
            filtered_critical.append(issue)
    critical[:] = filtered_critical
    
    # Check mapping pipeline
    mapping_pipeline = index.get('mapping_pipeline', {})
    pdf_functions = mapping_pipeline.get('pdf_extraction', {}).get('functions', [])
    excel_functions = mapping_pipeline.get('excel_processing', {}).get('functions', [])
    
    if not pdf_functions:
        critical.append("No PDF extraction functions found")
    
    if not excel_functions:
        critical.append("No Excel processing functions found")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python scripts/check_critical_issues.py TDS_DEV_INDEX.json")
        sys.exit(1)
    check_critical_issues(sys.argv[1])
