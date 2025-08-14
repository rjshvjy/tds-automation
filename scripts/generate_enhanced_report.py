#!/usr/bin/env python3
"""
Generate enhanced implementation report from v2.0 analyzer output
Location: scripts/generate_enhanced_report.py
"""

import json
import argparse
from datetime import datetime

def generate_enhanced_report(index_path, output_path):
    with open(index_path, 'r') as f:
        index = json.load(f)
    
    report = []
    report.append("# 📋 TDS Implementation Report")
    report.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    report.append(f"*Analyzer Version: {index.get('metadata', {}).get('analyzer_version', 'unknown')}*\n")
    
    # Function Signatures
    funcs = index.get('function_signatures', {})
    if funcs:
        report.append("## 🔧 Function Documentation\n")
        report.append(f"**Total Functions:** {len(funcs)}\n")
        
        for name, details in list(funcs.items())[:10]:  # First 10
            params = ', '.join([p['name'] for p in details.get('parameters', [])])
            report.append(f"### `{name}({params})`")
            if details.get('docstring'):
                report.append(f"> {details['docstring']}")
            report.append(f"- **Category:** {details.get('category', 'utility')}")
            report.append(f"- **Cell:** {details.get('cell', 'unknown')}")
            if details.get('returns'):
                report.append(f"- **Returns:** {', '.join(details['returns'][:3])}")
            report.append("")
    
    # Data Structures
    structs = index.get('data_structures', {})
    if structs:
        report.append("## 📊 Data Structures\n")
        for name, details in structs.items():
            report.append(f"### {name}")
            report.append(f"- **Type:** {details.get('type', 'unknown')}")
            report.append(f"- **Description:** {details.get('description', '')}")
            if 'keys' in details:
                report.append("- **Keys:**")
                for key, desc in list(details['keys'].items())[:5]:
                    report.append(f"  - `{key}`: {desc}")
            report.append("")
    
    # Excel Mappings
    mappings = index.get('excel_mappings', {})
    if mappings:
        report.append("## 📑 Excel Column Mappings\n")
        tds_sheet = mappings.get('tds_parties_sheet', {})
        if tds_sheet:
            report.append("### TDS PARTIES Sheet")
            report.append(f"- **Code Row:** {tds_sheet.get('code_row', 'unknown')}")
            report.append(f"- **Data Start:** {tds_sheet.get('data_start_row', 'unknown')}")
            
            critical = tds_sheet.get('critical_columns', {})
            if critical:
                report.append("\n**Critical Columns:**")
                report.append("| Code | Name | Required | Type |")
                report.append("|------|------|----------|------|")
                for code, info in list(critical.items())[:10]:
                    req = '✅' if info.get('required') else '⚪'
                    report.append(f"| {code} | {info.get('name', '')} | {req} | {info.get('data_type', '')} |")
            report.append("")
    
    # PDF Patterns
    patterns = index.get('pdf_patterns', {})
    if patterns:
        report.append("## 🔍 PDF Extraction Patterns\n")
        extraction = patterns.get('extraction_patterns', {})
        if extraction:
            report.append("**Key Patterns:**")
            for field, pattern in list(extraction.items())[:5]:
                report.append(f"- `{field}`: `{pattern[:50]}...`")
        report.append("")
    
    # Validation Rules
    validation = index.get('validation_rules', {})
    if validation:
        report.append("## ✅ Validation Rules\n")
        if 'pan_validation' in validation:
            pan = validation['pan_validation']
            report.append(f"- **PAN Format:** `{pan.get('pattern', '')}`")
            report.append(f"  - Example: {pan.get('example', '')}")
        if 'amount_validation' in validation:
            amt = validation['amount_validation']
            report.append(f"- **Amount Tolerance:** ±{amt.get('tolerance', 0)} rupee")
            report.append(f"  - Rounding: {amt.get('rounding', '')}")
        report.append("")
    
    # GitHub Integration Status
    github = index.get('github_integration', {})
    if github:
        report.append("## 🌐 GitHub Integration\n")
        report.append(f"- **Repository:** {github.get('repository', '')}")
        templates = github.get('template_structure', {}).get('files_needed', [])
        if templates:
            report.append("- **Required Templates:**")
            for template in templates:
                report.append(f"  - `{template.get('name', '')}`: {template.get('purpose', '')}")
        report.append("")
    
    # Issues Summary
    issues = index.get('issues', {})
    if issues:
        report.append("## 📌 Status Summary\n")
        critical = issues.get('critical', [])
        warnings = issues.get('warnings', [])
        info = issues.get('info', [])
        
        report.append(f"- **Critical Issues:** {len(critical)}")
        report.append(f"- **Warnings:** {len(warnings)}")
        report.append(f"- **Info:** {len(info)}")
        
        if info:
            report.append("\n**Status Items:**")
            for item in info[:10]:
                report.append(f"- {item}")
    
    # Write report
    with open(output_path, 'w') as f:
        f.write('\n'.join(report))
    
    print(f"✅ Enhanced report generated: {output_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate enhanced implementation report')
    parser.add_argument('--index', required=True, help='Path to index JSON')
    parser.add_argument('--output', required=True, help='Output markdown file')
    args = parser.parse_args()
    
    generate_enhanced_report(args.index, args.output)
