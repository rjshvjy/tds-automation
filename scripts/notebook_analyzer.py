#!/usr/bin/env python3
"""
TDS Notebook Analyzer for rjshvjy/tds-automation
Location: scripts/notebook_analyzer.py

Analyzes TDS_Automation_V2.ipynb (in repository root) for:
- Dependencies and forward references
- PDF→Excel data flow and mapping issues
- Widget state management
- Test coverage
"""

import json
import re
import ast
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple, Any
import subprocess

class TDSNotebookAnalyzer:
    def __init__(self, notebook_path: str, verbose: bool = False):
        self.notebook_path = Path(notebook_path)
        self.verbose = verbose
        self.cells = []
        self.index = {
            "metadata": {},
            "cells": {},
            "dependency_graph": {},
            "mapping_pipeline": {},
            "issues": {
                "critical": [],
                "warnings": [],
                "mapping_issues": [],
                "fixed": []
            },
            "pdf_excel_flow": {},
            "test_coverage": {}
        }
        
        # Critical functions for PDF→Excel mapping
        self.critical_functions = {
            "extract_challan_data_from_pdf": "PDF extraction",
            "extract_all_challans": "Bulk PDF processing",
            "read_tds_masters": "Excel reading",
            "update_tds_masters_with_challans": "Challan integration",
            "validate_tds_totals": "Amount validation",
            "GovernmentTemplateBuilder": "Template generation",
            "ValidationEngine": "Field validation",
            "ReconciliationReport": "Report generation"
        }
        
        # Column code mappings to track
        self.column_mappings = {
            "(415)": "Deductee Code",
            "(415A)": "Section/Nature of Payment",
            "(416)": "PAN",
            "(417)": "Name",
            "(418)": "Date of Payment",
            "(419)": "Amount Paid",
            "(420)": "Paid by Book Entry",
            "(421)": "TDS Amount",
            "(425D)": "BSR Code",
            "(425E)": "Challan Serial No",
            "(425F)": "Date Deposited",
            "(427)": "Rate"
        }
        
        # Known bug patterns
        self.bug_patterns = {
            "nan_values": r"NaN|\.fillna|notna|isna",
            "leading_zeros": r"str\.zfill|\.zfill|pad.*0|leading.*zero",
            "date_format": r"strftime|strptime|to_datetime|DD/MM/YYYY",
            "rate_conversion": r"\*\s*100|/\s*100|percentage|%",
            "round_up": r"ROUND_HALF_UP|round.*up|math\.ceil",
            "string_preserve": r"astype.*str|str\(|as.*string"
        }
    
    def analyze(self) -> Dict:
        """Main analysis pipeline"""
        if self.verbose:
            print(f"📊 Analyzing: {self.notebook_path}")
        
        self.load_notebook()
        self.extract_metadata()
        self.analyze_cells()
        self.build_dependency_graph()
        self.analyze_pdf_excel_mapping()
        self.detect_issues()
        self.check_test_coverage()
        self.add_git_metadata()
        
        return self.index
    
    def load_notebook(self):
        """Load Jupyter notebook"""
        with open(self.notebook_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)
        
        self.cells = notebook.get('cells', [])
        self.index['metadata']['total_cells'] = len(self.cells)
        self.index['metadata']['notebook_path'] = str(self.notebook_path)
        self.index['metadata']['last_scan'] = datetime.now().isoformat()
    
    def extract_metadata(self):
        """Extract notebook metadata"""
        self.index['metadata']['version'] = "3.0"
        self.index['metadata']['repository'] = "rjshvjy/tds-automation"
        self.index['metadata']['type'] = "widget_based"
        self.index['metadata']['flow_type'] = "branching"
    
    def analyze_cells(self):
        """Analyze each cell for functions, dependencies, and issues"""
        for idx, cell in enumerate(self.cells):
            if cell.get('cell_type') != 'code':
                continue
            
            source = ''.join(cell.get('source', []))
            if not source.strip():
                continue
            
            cell_info = {
                "index": idx,
                "title": self._extract_cell_title(source),
                "status": "unknown",
                "imports": self._extract_imports(source),
                "defines": {
                    "functions": self._extract_functions(source),
                    "classes": self._extract_classes(source)
                },
                "calls": self._extract_function_calls(source),
                "dependencies": {"backward": [], "forward": []},
                "issues": [],
                "mapping_related": False
            }
            
            # Check if cell is mapping-related
            for func in self.critical_functions:
                if func in source:
                    cell_info["mapping_related"] = True
                    break
            
            # Check for column mappings
            column_refs = []
            for code, name in self.column_mappings.items():
                if code in source or name in source:
                    column_refs.append(code)
            if column_refs:
                cell_info["column_references"] = column_refs
            
            # Check for bug patterns
            for pattern_name, pattern in self.bug_patterns.items():
                if re.search(pattern, source, re.IGNORECASE):
                    cell_info["issues"].append(f"Contains {pattern_name} pattern")
            
            self.index['cells'][f"cell_{idx}"] = cell_info
    
    def _extract_cell_title(self, source: str) -> str:
        """Extract cell title from first comment"""
        match = re.search(r'^#\s*Cell\s*\d*:?\s*(.+)$', source, re.MULTILINE)
        return match.group(1) if match else "Untitled"
    
    def _extract_imports(self, source: str) -> List[str]:
        """Extract import statements"""
        imports = []
        for line in source.split('\n'):
            if re.match(r'^(from\s+\S+\s+)?import\s+', line.strip()):
                imports.append(line.strip())
        return imports
    
    def _extract_functions(self, source: str) -> List[str]:
        """Extract function definitions"""
        return re.findall(r'^def\s+(\w+)\s*\(', source, re.MULTILINE)
    
    def _extract_classes(self, source: str) -> List[str]:
        """Extract class definitions"""
        return re.findall(r'^class\s+(\w+)\s*[:\(]', source, re.MULTILINE)
    
    def _extract_function_calls(self, source: str) -> List[str]:
        """Extract function calls"""
        # Remove comments and strings to avoid false positives
        cleaned = re.sub(r'#.*$', '', source, flags=re.MULTILINE)
        cleaned = re.sub(r'["\'].*?["\']', '', cleaned)
        calls = re.findall(r'(\w+)\s*\(', cleaned)
        return list(set(calls))
    
    def build_dependency_graph(self):
        """Build dependency graph between cells"""
        # Track where functions/classes are defined
        definitions = {}
        for cell_id, cell_info in self.index['cells'].items():
            for func in cell_info['defines']['functions']:
                definitions[func] = cell_id
            for cls in cell_info['defines']['classes']:
                definitions[cls] = cell_id
        
        # Find dependencies
        execution_order = []
        for cell_id, cell_info in self.index['cells'].items():
            deps = set()
            forward_deps = set()
            
            for call in cell_info['calls']:
                if call in definitions:
                    def_cell = definitions[call]
                    def_idx = int(def_cell.split('_')[1])
                    curr_idx = cell_info['index']
                    
                    if def_idx < curr_idx:
                        deps.add(def_cell)
                    elif def_idx > curr_idx:
                        forward_deps.add(def_cell)
                        self.index['issues']['critical'].append(
                            f"Cell {curr_idx}: Forward dependency on {call} defined in Cell {def_idx}"
                        )
            
            cell_info['dependencies']['backward'] = list(deps)
            cell_info['dependencies']['forward'] = list(forward_deps)
            execution_order.append(cell_info['index'])
        
        self.index['dependency_graph'] = {
            "execution_order": execution_order,
            "definitions": definitions,
            "forward_dependencies": len([c for c in self.index['cells'].values() 
                                        if c['dependencies']['forward']])
        }
    
    def analyze_pdf_excel_mapping(self):
        """Analyze PDF to Excel data flow and mappings"""
        mapping_flow = {
            "pdf_extraction": {
                "functions": [],
                "input_fields": [],
                "output_structure": {},
                "issues": []
            },
            "excel_processing": {
                "functions": [],
                "column_mappings": self.column_mappings.copy(),
                "transformations": [],
                "issues": []
            },
            "validation": {
                "mandatory_fields": 20,
                "validation_functions": [],
                "issues": []
            }
        }
        
        # Find PDF extraction functions
        for cell_id, cell_info in self.index['cells'].items():
            source = ''.join(self.cells[cell_info['index']].get('source', []))
            
            # PDF extraction patterns
            if 'extract_challan' in source or 'extract_pdf' in source.lower():
                mapping_flow['pdf_extraction']['functions'].append({
                    "cell": cell_id,
                    "functions": cell_info['defines']['functions']
                })
                
                # Look for field extraction patterns
                field_patterns = re.findall(r'["\'](\w+_no|bsr_code|amount|date)["\']', source)
                mapping_flow['pdf_extraction']['input_fields'].extend(field_patterns)
            
            # Excel processing patterns
            if 'read_tds' in source or 'update_tds' in source or 'masters' in source.lower():
                mapping_flow['excel_processing']['functions'].append({
                    "cell": cell_id,
                    "functions": cell_info['defines']['functions']
                })
                
                # Check for transformation patterns
                if 'zfill(7)' in source:
                    mapping_flow['excel_processing']['transformations'].append("BSR padding to 7 digits")
                if 'ROUND_HALF_UP' in source:
                    mapping_flow['excel_processing']['transformations'].append("Amount rounding up")
                if 'strftime' in source or 'DD/MM/YYYY' in source:
                    mapping_flow['excel_processing']['transformations'].append("Date formatting")
            
            # Validation patterns
            if 'ValidationEngine' in source or 'validate' in source.lower():
                mapping_flow['validation']['validation_functions'].append({
                    "cell": cell_id,
                    "functions": cell_info['defines']['functions']
                })
        
        # Check for missing column mappings
        for cell_info in self.index['cells'].values():
            if 'column_references' in cell_info:
                for code in cell_info['column_references']:
                    if code not in self.column_mappings:
                        mapping_flow['excel_processing']['issues'].append(
                            f"Unknown column code: {code}"
                        )
        
        self.index['mapping_pipeline'] = mapping_flow
    
    def detect_issues(self):
        """Detect potential issues and bugs"""
        # Check for missing critical functions
        defined_functions = set()
        for cell_info in self.index['cells'].values():
            defined_functions.update(cell_info['defines']['functions'])
            defined_functions.update(cell_info['defines']['classes'])
        
        for func_name, description in self.critical_functions.items():
            if func_name not in defined_functions:
                self.index['issues']['critical'].append(
                    f"Missing critical function: {func_name} ({description})"
                )
        
        # Check for undefined function calls
        all_calls = set()
        for cell_info in self.index['cells'].values():
            all_calls.update(cell_info['calls'])
        
        undefined = all_calls - defined_functions - set(['print', 'len', 'str', 'int', 
                                                         'float', 'range', 'open', 'isinstance'])
        for func in undefined:
            if func and not func.startswith('_'):
                self.index['issues']['warnings'].append(
                    f"Undefined function called: {func}"
                )
        
        # Check for widget state issues
        widget_cells = [c for c in self.index['cells'].values() 
                       if 'widget' in ' '.join(c.get('imports', [])).lower()]
        if widget_cells:
            if len(widget_cells) > 1:
                self.index['issues']['warnings'].append(
                    f"Multiple widget cells found ({len(widget_cells)}), may cause state conflicts"
                )
        
        # Mapping-specific issues
        mapping_cells = [c for c in self.index['cells'].values() if c.get('mapping_related')]
        if not mapping_cells:
            self.index['issues']['critical'].append(
                "No PDF→Excel mapping functions found!"
            )
    
    def check_test_coverage(self):
        """Check which components have test functions"""
        test_functions = []
        for cell_info in self.index['cells'].values():
            for func in cell_info['defines']['functions']:
                if func.startswith('test_'):
                    test_functions.append(func)
        
        self.index['test_coverage'] = {
            "test_functions": test_functions,
            "coverage_count": len(test_functions),
            "has_pdf_tests": any('pdf' in f.lower() for f in test_functions),
            "has_excel_tests": any('excel' in f.lower() or 'masters' in f.lower() 
                                  for f in test_functions),
            "has_validation_tests": any('validat' in f.lower() for f in test_functions)
        }
    
    def add_git_metadata(self):
        """Add git commit information"""
        try:
            commit_hash = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'], 
                cwd=self.notebook_path.parent
            ).decode().strip()
            self.index['metadata']['commit_hash'] = commit_hash
        except:
            self.index['metadata']['commit_hash'] = "unknown"
    
    def save_index(self, output_path: str):
        """Save index to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)
        
        if self.verbose:
            print(f"✅ Index saved to: {output_path}")
            print(f"   - Critical issues: {len(self.index['issues']['critical'])}")
            print(f"   - Warnings: {len(self.index['issues']['warnings'])}")
            print(f"   - Mapping issues: {len(self.index['issues']['mapping_issues'])}")


def main():
    parser = argparse.ArgumentParser(description='Analyze TDS Jupyter Notebook in rjshvjy/tds-automation')
    parser.add_argument('--notebook', default='TDS_Automation_V2.ipynb',
                       help='Path to notebook file (default: TDS_Automation_V2.ipynb in root)')
    parser.add_argument('--output', default='TDS_DEV_INDEX.json',
                       help='Output JSON file path (default: TDS_DEV_INDEX.json in root)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Check if notebook exists
    if not Path(args.notebook).exists():
        print(f"❌ Error: Notebook not found: {args.notebook}")
        print(f"   Looking in: {Path(args.notebook).absolute()}")
        print(f"   Current directory: {Path.cwd()}")
        sys.exit(1)
    
    # Run analysis
    analyzer = TDSNotebookAnalyzer(args.notebook, verbose=args.verbose)
    index = analyzer.analyze()
    analyzer.save_index(args.output)
    
    # Exit with error code if critical issues found
    if index['issues']['critical']:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == '__main__':
    main()
