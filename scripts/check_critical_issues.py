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


# ============= generate_bug_report.py =============
"""
Generate markdown bug report from index
Usage: python generate_bug_report.py --index TDS_DEV_INDEX.json --output MAPPING_BUGS.md
"""

import json
import argparse
from datetime import datetime

def generate_bug_report(index_path, output_path):
    with open(index_path, 'r') as f:
        index = json.load(f)
    
    # Start markdown report
    report = []
    report.append("# 🐛 TDS Automation Bug Report")
    report.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    
    # Summary section
    issues = index.get('issues', {})
    report.append("## 📊 Summary\n")
    report.append(f"- **Critical Issues:** {len(issues.get('critical', []))}")
    report.append(f"- **Warnings:** {len(issues.get('warnings', []))}")
    report.append(f"- **Mapping Issues:** {len(issues.get('mapping_issues', []))}")
    report.append(f"- **Fixed Issues:** {len(issues.get('fixed', []))}\n")
    
    # Critical Issues
    if issues.get('critical'):
        report.append("## 🚨 Critical Issues\n")
        report.append("These must be fixed immediately:\n")
        for i, issue in enumerate(issues['critical'], 1):
            report.append(f"{i}. {issue}")
        report.append("")
    
    # PDF→Excel Mapping Pipeline
    mapping = index.get('mapping_pipeline', {})
    report.append("## 🔄 PDF→Excel Mapping Pipeline\n")
    
    # PDF Extraction
    pdf_info = mapping.get('pdf_extraction', {})
    report.append("### PDF Extraction")
    report.append(f"- **Functions Found:** {len(pdf_info.get('functions', []))}")
    report.append(f"- **Fields Extracted:** {', '.join(set(pdf_info.get('input_fields', [])))}")
    if pdf_info.get('issues'):
        report.append("- **Issues:**")
        for issue in pdf_info['issues']:
            report.append(f"  - {issue}")
    report.append("")
    
    # Excel Processing
    excel_info = mapping.get('excel_processing', {})
    report.append("### Excel Processing")
    report.append(f"- **Functions Found:** {len(excel_info.get('functions', []))}")
    report.append(f"- **Column Mappings:** {len(excel_info.get('column_mappings', {}))}")
    report.append("- **Transformations:**")
    for transform in excel_info.get('transformations', []):
        report.append(f"  - {transform}")
    report.append("")
    
    # Column Mappings Table
    report.append("### Column Code Mappings\n")
    report.append("| Code | Maps To | Status |")
    report.append("|------|---------|--------|")
    
    column_mappings = excel_info.get('column_mappings', {})
    for code, name in column_mappings.items():
        status = "✅" if code in ["(415)", "(416)", "(421)"] else "⚠️"
        report.append(f"| {code} | {name} | {status} |")
    report.append("")
    
    # Known Bug Patterns Found
    report.append("## 🔍 Bug Patterns Detected\n")
    
    cells_with_issues = [c for c in index.get('cells', {}).values() if c.get('issues')]
    if cells_with_issues:
        report.append("| Cell | Title | Issues |")
        report.append("|------|-------|--------|")
        for cell in cells_with_issues[:10]:  # Show first 10
            title = cell.get('title', 'Untitled')[:30]
            issues = ', '.join(cell['issues'][:2])  # First 2 issues
            report.append(f"| {cell['index']} | {title} | {issues} |")
    report.append("")
    
    # Forward Dependencies
    forward_deps = index.get('dependency_graph', {}).get('forward_dependencies', 0)
    if forward_deps > 0:
        report.append("## ⚠️ Forward Dependencies\n")
        report.append(f"Found {forward_deps} cells with forward dependencies.\n")
        report.append("These cells call functions that are defined later in the notebook:")
        
        for cell_id, cell_info in index.get('cells', {}).items():
            if cell_info.get('dependencies', {}).get('forward'):
                report.append(f"- Cell {cell_info['index']}: {cell_info.get('title', 'Untitled')}")
                for dep in cell_info['dependencies']['forward']:
                    report.append(f"  - Depends on {dep}")
        report.append("")
    
    # Test Coverage
    test_coverage = index.get('test_coverage', {})
    report.append("## 🧪 Test Coverage\n")
    report.append(f"- **Test Functions:** {test_coverage.get('coverage_count', 0)}")
    report.append(f"- **PDF Tests:** {'✅' if test_coverage.get('has_pdf_tests') else '❌'}")
    report.append(f"- **Excel Tests:** {'✅' if test_coverage.get('has_excel_tests') else '❌'}")
    report.append(f"- **Validation Tests:** {'✅' if test_coverage.get('has_validation_tests') else '❌'}")
    report.append("")
    
    # Recommendations
    report.append("## 💡 Recommendations\n")
    report.append("1. **Fix Forward Dependencies:** Reorder cells so functions are defined before use")
    report.append("2. **Add Missing Functions:** Implement any critical functions that are called but not defined")
    report.append("3. **Validate Column Mappings:** Ensure all column codes map correctly")
    report.append("4. **Test Data Transformations:** Verify BSR padding, date formatting, and rate conversions")
    report.append("5. **Add More Tests:** Increase test coverage for PDF and Excel operations\n")
    
    # Write report
    with open(output_path, 'w') as f:
        f.write('\n'.join(report))
    
    print(f"✅ Bug report generated: {output_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate bug report')
    parser.add_argument('--index', required=True, help='Path to index JSON')
    parser.add_argument('--output', required=True, help='Output markdown file')
    args = parser.parse_args()
    
    generate_bug_report(args.index, args.output)
