import streamlit as st
import pandas as pd
import numpy as np
import PyPDF2
import re
import os
import io
import shutil
import tempfile
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import openpyxl
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font
import warnings

warnings.filterwarnings("ignore")

# --- Core Processing Functions from the Notebook ---
# (Slightly modified to use st.write for logging instead of print)

def extract_challan_data_from_pdf(pdf_path, progress_bar):
    """Extract challan data from a single PDF file"""
    challan_data = {}
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            if len(pdf_reader.pages) > 0:
                text = pdf_reader.pages[0].extract_text()

            patterns = {
                'tan': r'TAN\s*:\s*([A-Z0-9]+)',
                'nature_of_payment': r'Nature of Payment\s*:\s*(\d+[A-Z])',
                'cin': r'CIN\s*:\s*([A-Z0-9]+)',
                'bsr_code': r'BSR code\s*:\s*([\d]+)',
                'challan_no': r'Challan No\.\s*:\s*([\d]+)',
                'tender_date': r'Tender Date\s*:\s*(\d{2}/\d{2}/\d{4})',
                'mode_of_payment': r'Mode of Payment\s*:\s*([^\n]+)',
            }
            for field, pattern in patterns.items():
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    if field == "mode_of_payment":
                        value = value.upper()
                    elif field in ['bsr_code', 'challan_no']:
                        value = value.zfill(7) if field == 'bsr_code' else value
                    challan_data[field] = value
                else:
                    challan_data[field] = ""

            tax_patterns = [
                r'A\s+Tax\s+\s*([\d,]+)', r'Tax\s+\s*([\d,]+)', r'A\s+Tax[^0-9]+([\d,]+)'
            ]
            tax_amount = ""
            for pattern in tax_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    tax_amount = match.group(1).strip().replace(',', '')
                    break
            if not tax_amount:
                amount_patterns = [r'Amount \(in Rs\.\)\s*:\s*\s*([\d,]+)', r'Amount.*?\s*([\d,]+)']
                for pattern in amount_patterns:
                    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                    if match:
                        tax_amount = match.group(1).strip().replace(',', '')
                        break
            challan_data['tax_amount'] = tax_amount

            amount_fields = {
                'surcharge': [r'B\s+Surcharge\s+\s*([\d,]+)', r'Surcharge\s+\s*([\d,]+)'],
                'cess': [r'C\s+Cess\s+\s*([\d, ]+)', r'Cess\s+\s*([\d,]+)'],
                'interest': [r'D\s+Interest\s+\s*([\d,]+)', r'Interest\s+\s*([\d,]+)'],
                'penalty': [r'E\s+Penalty\s+\s*([\d,]+)', r'Penalty\s+\s*([\d,]+)'],
            }
            for field, patterns_list in amount_fields.items():
                value = ""
                for pattern in patterns_list:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip().replace(',', '')
                        break
                challan_data[field] = value if value else "0"

            total_patterns = [r'Total \(A\+B\+C\+D\+E\+F\)\s+\s*([\d,]+)', r'Total.*?\s*([\d,]+)']
            total_amount = ""
            for pattern in total_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    total_amount = match.group(1).strip().replace(',', '')
                    break
            challan_data['total_amount'] = total_amount
            challan_data['file_name'] = os.path.basename(pdf_path)
            
    except Exception as e:
        st.error(f"Error processing {os.path.basename(pdf_path)}: {str(e)}")
        challan_data['error'] = str(e)
    return challan_data

def extract_all_challans(pdf_folder_path, log_expander):
    """Extract data from all PDF files in a folder and deduplicate"""
    all_challan_data = []
    challan_map = {}
    pdf_files = [f for f in os.listdir(pdf_folder_path) if f.lower().endswith('.pdf')]
    if not pdf_files:
        st.warning("No PDF files found in the uploaded batch.")
        return all_challan_data, pd.DataFrame()

    log_expander.info(f"Found {len(pdf_files)} PDF files to process...")
    
    progress_bar = st.progress(0)
    duplicate_count = 0
    
    for i, pdf_file in enumerate(pdf_files):
        pdf_path = os.path.join(pdf_folder_path, pdf_file)
        challan_data = extract_challan_data_from_pdf(pdf_path, progress_bar)
        
        challan_no = challan_data.get('challan_no', "")
        if challan_no and challan_no in challan_map:
            duplicate_count += 1
            existing_challan = challan_map[challan_no]
            if challan_data.get('tax_amount') != existing_challan.get('tax_amount'):
                log_expander.warning(f"Duplicate challan {challan_no} has different tax amounts!")
        else:
            if challan_no:
                challan_map[challan_no] = challan_data
                all_challan_data.append(challan_data)
            else:
                log_expander.warning(f"Skipping file {pdf_file}, no challan number found.")
        progress_bar.progress((i + 1) / len(pdf_files))

    log_expander.success(f"Total PDF files processed: {len(pdf_files)}")
    log_expander.info(f"Unique challans found: {len(all_challan_data)}")
    if duplicate_count > 0:
        log_expander.info(f"Duplicate challans skipped: {duplicate_count}")

    summary = {}
    total_all = 0
    for challan in all_challan_data:
        nop = challan.get('nature_of_payment', 'Unknown')
        if nop:
            if nop not in summary:
                summary[nop] = {'count': 0, 'total_tax': 0}
            summary[nop]['count'] += 1
            try:
                tax_amt = float(challan.get('tax_amount', 0))
                summary[nop]['total_tax'] += tax_amt
                total_all += tax_amt
            except:
                pass
    
    summary_df = pd.DataFrame.from_dict(summary, orient='index')
    summary_df.index.name = "Nature of Payment"
    summary_df.columns = ["Challan Count", "Total Tax"]
    summary_df["Total Tax"] = summary_df["Total Tax"].map('{:,.2f}'.format)
    
    return all_challan_data, summary_df

def read_tds_masters(file_path, log_expander):
    """Read the TDS Masters Excel file"""
    try:
        tds_codes = pd.read_excel(file_path, sheet_name='TDS CODES', keep_default_na=False)
        tds_rates = pd.read_excel(file_path, sheet_name='TDS RATES', keep_default_na=False)
        
        wb = load_workbook(file_path, data_only=True)
        ws_parties = wb['TDS PARTIES']
        
        code_row = None
        for idx in range(1, 11):
            row_values = [str(ws_parties.cell(row=idx, column=col).value) for col in range(1, ws_parties.max_column + 1) if ws_parties.cell(row=idx, column=col).value]
            code_patterns = ['(415)', '(427)', '(416)', '(415A)', '-415', '-427', '-416']
            if any(pattern in val for val in row_values for pattern in code_patterns):
                code_row = idx
                log_expander.info(f"Found column codes at row {idx}")
                break
        
        header_row = code_row - 1 if code_row else 1
        headers = [ws_parties.cell(row=header_row, column=col).value or f"Column_{col}" for col in range(1, ws_parties.max_column + 1)]
        
        code_to_column_name = {}
        if code_row:
            for col in range(1, ws_parties.max_column + 1):
                code_val = ws_parties.cell(row=code_row, column=col).value
                if code_val:
                    code_str = str(code_val).strip()
                    match = re.search(r'\(?([0-9A-Z]+)\)?', code_str)
                    if match:
                        extracted_code = match.group(1)
                        normalized_code = f'({extracted_code})'
                        code_to_column_name[normalized_code] = headers[col - 1]

        data_rows = []
        data_start_row = code_row + 1 if code_row else 2
        for row in range(data_start_row, ws_parties.max_row + 1):
            row_data = [ws_parties.cell(row=row, column=col).value for col in range(1, ws_parties.max_column + 1)]
            if any(cell is not None and str(cell).strip() != '' for cell in row_data):
                data_rows.append(row_data)

        tds_parties = pd.DataFrame(data_rows, columns=headers)
        
        numeric_codes = ['(419)', '(421)']
        for code in numeric_codes:
            col_name = code_to_column_name.get(code)
            if col_name and col_name in tds_parties.columns:
                tds_parties[col_name] = pd.to_numeric(
                    tds_parties[col_name].astype(str).str.replace(',', '').str.replace('₹', '').str.strip(),
                    errors='coerce'
                ).apply(lambda x: Decimal(str(x)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP) if pd.notna(x) else x)

        date_codes = ['(418)', '(425F)']
        for code in date_codes:
            col_name = code_to_column_name.get(code)
            if col_name and col_name in tds_parties.columns:
                tds_parties[col_name] = pd.to_datetime(tds_parties[col_name], errors='coerce', dayfirst=True)

        challan_details = pd.read_excel(file_path, sheet_name='Challan Details', header=1, keep_default_na=False)
        wb.close()
        log_expander.success(f"Successfully read TDS Masters file: {len(tds_parties)} parties found.")
        return {
            'tds_codes': tds_codes, 'tds_parties': tds_parties, 'challan_details': challan_details,
            'tds_rates': tds_rates, 'file_path': file_path, 'code_to_column_name': code_to_column_name,
            'code_row': code_row
        }
    except Exception as e:
        st.error(f"Error reading TDS Masters: {str(e)}")
        return None

def validate_tds_totals(tds_masters_data, challan_data_list):
    """Validate that party-wise TDS totals match challan amounts"""
    try:
        tds_parties = tds_masters_data['tds_parties']
        code_to_column_name = tds_masters_data.get('code_to_column_name', {})
        payment_col = code_to_column_name.get('(415A)')
        tds_col = code_to_column_name.get('(421)')

        if not payment_col or not tds_col:
            st.warning("Could not find payment type or TDS amount columns in Masters file for validation.")
            return False, pd.DataFrame()

        party_totals = {}
        for index, row in tds_parties.iterrows():
            payment_type = str(row.get(payment_col, '')).strip()
            if payment_type and payment_type not in ['nan', 'NaT', '']:
                tds_amount = 0
                val = row.get(tds_col)
                if pd.notna(val):
                    tds_amount = Decimal(str(val)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
                
                payment_type_clean = payment_type.replace(' ', '')
                party_totals[payment_type_clean] = party_totals.get(payment_type_clean, 0) + tds_amount

        challan_totals = {}
        for challan in challan_data_list:
            nop = challan.get('nature_of_payment', '').replace(' ', '')
            tax_amount = Decimal(challan.get('tax_amount', 0)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
            if nop:
                challan_totals[nop] = tax_amount

        validation_data = []
        all_nops = sorted(set(list(party_totals.keys()) + list(challan_totals.keys())))
        validation_passed = True

        for nop in all_nops:
            party_total = party_totals.get(nop, 0)
            challan_total = challan_totals.get(nop, 0)
            difference = abs(party_total - challan_total)
            status = "✅ PASS" if difference <= 1 else "❌ FAIL"
            if difference > 1:
                validation_passed = False
            validation_data.append({
                "Nature of Payment": nop,
                "Party Total (Masters)": f"{party_total:,.0f}",
                "Challan Total (PDFs)": f"{challan_total:,.0f}",
                "Status": status
            })
        
        return validation_passed, pd.DataFrame(validation_data)
    except Exception as e:
        st.error(f"Error during validation: {str(e)}")
        return False, pd.DataFrame()

def get_output_filename_from_masters(tds_masters_data):
    """Generate output filename from TDS Masters payment dates"""
    try:
        code_to_column_name = tds_masters_data.get('code_to_column_name', {})
        date_col = code_to_column_name.get('(418)')
        if date_col and date_col in tds_masters_data['tds_parties'].columns:
            dates = tds_masters_data['tds_parties'][date_col].dropna()
            if not dates.empty:
                first_date = pd.to_datetime(dates.iloc[0])
                return f"TDS_{first_date.strftime('%B')}_{first_date.strftime('%Y')}.xlsx"
    except:
        pass
    current_date = datetime.now()
    return f"TDS_{current_date.strftime('%B')}_{current_date.strftime('%Y')}.xlsx"

def update_output_file(template_path, output_path, updated_masters_data, challan_data_list, log_expander):
    """Creates the final output file from the template"""
    wb = load_workbook(template_path)

    # Update CHALLAN DETAILS sheet
    ws_challan = wb['CHALLAN DETAILS']
    log_expander.info("Updating CHALLAN DETAILS sheet in output file...")
    # Clear existing data
    for row in ws_challan.iter_rows(min_row=4, max_row=ws_challan.max_row):
        for cell in row:
            cell.value = None
    
    for idx, challan in enumerate(challan_data_list, start=4):
        row_idx = idx
        tax_amt = Decimal(challan.get('tax_amount', 0)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
        ws_challan.cell(row=row_idx, column=1).value = idx - 3
        ws_challan.cell(row=row_idx, column=2).value = challan.get('nature_of_payment', '')
        ws_challan.cell(row=row_idx, column=3).value = int(tax_amt)
        # ... (add other challan fields if necessary) ...
        ws_challan.cell(row=row_idx, column=8).value = f'=SUM(C{row_idx}:G{row_idx})'
        ws_challan.cell(row=row_idx, column=9).value = challan.get('mode_of_payment', '')
        ws_challan.cell(row=row_idx, column=10).value = challan.get('bsr_code', '')
        date_str = challan.get('tender_date', '')
        if date_str:
            try:
                date_obj = datetime.strptime(date_str, '%d/%m/%Y')
                ws_challan.cell(row=row_idx, column=11).value = date_obj
                ws_challan.cell(row=row_idx, column=11).number_format = 'DD/MM/YYYY'
            except:
                ws_challan.cell(row=row_idx, column=11).value = date_str
        ws_challan.cell(row=row_idx, column=12).value = challan.get('challan_no', '')
        ws_challan.cell(row=row_idx, column=13).value = 'NO'

    # Update DEDUCTEE BREAK-UP sheet
    ws_deductee = wb['DEDUCTEE BREAK-UP']
    log_expander.info("Updating DEDUCTEE BREAK-UP sheet in output file...")
    # Clear existing data
    for row in ws_deductee.iter_rows(min_row=4, max_row=ws_deductee.max_row):
        for cell in row:
            cell.value = None
            
    tds_parties = updated_masters_data['tds_parties']
    code_to_column_name = updated_masters_data['code_to_column_name']
    
    challan_map = {c.get('nature_of_payment', '').replace(' ', ''): c for c in challan_data_list}

    for idx, party_row in enumerate(tds_parties.itertuples(), start=4):
        row_idx = idx
        ws_deductee.cell(row=row_idx, column=1).value = idx - 3 # Sr.No
        
        payment_type = getattr(party_row, code_to_column_name.get('(415A)').replace(' ', '_'), '')
        challan = challan_map.get(str(payment_type).replace(' ', ''), {})
        
        ws_deductee.cell(row=row_idx, column=2).value = getattr(party_row, code_to_column_name.get('(415)').replace(' ', '_'), '')
        ws_deductee.cell(row=row_idx, column=3).value = payment_type
        ws_deductee.cell(row=row_idx, column=4).value = getattr(party_row, code_to_column_name.get('(416)').replace(' ', '_'), '')
        ws_deductee.cell(row=row_idx, column=5).value = getattr(party_row, code_to_column_name.get('(417)').replace(' ', '_'), '')
        
        date_payment = getattr(party_row, code_to_column_name.get('(418)').replace(' ', '_'), '')
        if pd.notna(date_payment):
            ws_deductee.cell(row=row_idx, column=6).value = date_payment
            ws_deductee.cell(row=row_idx, column=6).number_format = 'DD/MM/YYYY'
        
        amount_paid = getattr(party_row, code_to_column_name.get('(419)').replace(' ', '_'), 0)
        ws_deductee.cell(row=row_idx, column=7).value = int(amount_paid) if pd.notna(amount_paid) else 0

        tds_amount = getattr(party_row, code_to_column_name.get('(421)').replace(' ', '_'), 0)
        ws_deductee.cell(row=row_idx, column=9).value = int(tds_amount) if pd.notna(tds_amount) else 0
        
        ws_deductee.cell(row=row_idx, column=12).value = f'=SUM(I{row_idx}:K{row_idx})'
        ws_deductee.cell(row=row_idx, column=13).value = f'=L{row_idx}'
        
        ws_deductee.cell(row=row_idx, column=17).value = challan.get('bsr_code', '')
        ws_deductee.cell(row=row_idx, column=18).value = challan.get('challan_no', '')

        date_deposited = challan.get('tender_date', '')
        if date_deposited:
             try:
                date_obj = datetime.strptime(date_deposited, '%d/%m/%Y')
                ws_deductee.cell(row=row_idx, column=19).value = date_obj
                ws_deductee.cell(row=row_idx, column=19).number_format = 'DD/MM/YYYY'
             except:
                ws_deductee.cell(row=row_idx, column=19).value = date_deposited
        
        if pd.notna(date_payment):
            ws_deductee.cell(row=row_idx, column=20).value = date_payment
            ws_deductee.cell(row=row_idx, column=20).number_format = 'DD/MM/YYYY'
            
    wb.save(output_path)
    wb.close()
    log_expander.success(f"Generated output file: {os.path.basename(output_path)}")


# --- Streamlit App UI ---

st.set_page_config(page_title="TDS Automation Tool", layout="wide")

st.title("📄 TDS Return Automation Tool")
st.markdown("""
This tool automates the process of preparing TDS returns. Upload your files in the sidebar, 
and the application will extract data, perform validations, and generate the final output file for you.
""")

# --- Sidebar for File Uploads ---
with st.sidebar:
    st.header("📂 Upload Files")
    
    pdf_files = st.file_uploader(
        "1. Upload TDS Challan PDFs", 
        type="pdf", 
        accept_multiple_files=True,
        help="Select all the PDF challan files for the period."
    )
    
    masters_file = st.file_uploader(
        "2. Upload TDS Masters File", 
        type="xlsx",
        help="The Excel file containing party details (e.g., TDS_Masters.xlsx)."
    )
    
    template_file = st.file_uploader(
        "3. Upload TDS Template File", 
        type="xlsx",
        help="The blank TDS return template file provided by the department."
    )
    
    process_button = st.button("🚀 Process Files", use_container_width=True)

# --- Main App Logic ---
if process_button:
    if not pdf_files or not masters_file or not template_file:
        st.error("🚨 Please upload all three file types: PDFs, Masters, and Template.")
    else:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create subdirectories
            pdf_dir = os.path.join(temp_dir, 'pdfs')
            output_dir = os.path.join(temp_dir, 'output')
            os.makedirs(pdf_dir, exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)

            # Save uploaded files to temp directory
            for pdf in pdf_files:
                with open(os.path.join(pdf_dir, pdf.name), "wb") as f:
                    f.write(pdf.getbuffer())
            
            masters_path = os.path.join(temp_dir, masters_file.name)
            with open(masters_path, "wb") as f:
                f.write(masters_file.getbuffer())
            
            template_path = os.path.join(temp_dir, template_file.name)
            with open(template_path, "wb") as f:
                f.write(template_file.getbuffer())

            st.info("All files uploaded. Starting the automation process...")
            
            log_expander = st.expander("Show Processing Logs", expanded=False)

            with st.spinner('Step 1: Extracting data from PDF challans...'):
                challan_data_list, summary_df = extract_all_challans(pdf_dir, log_expander)
            
            if not challan_data_list:
                st.warning("No valid challans could be extracted from the PDFs. Aborting.")
            else:
                st.subheader("📊 Challan Data Summary")
                st.dataframe(summary_df)
                total_tax = summary_df["Total Tax"].str.replace(',', '').astype(float).sum()
                st.metric("Grand Total Tax (from PDFs)", f"₹{total_tax:,.2f}")

                with st.spinner('Step 2: Reading TDS Masters file...'):
                    tds_masters_data = read_tds_masters(masters_path, log_expander)
                
                if tds_masters_data:
                    st.subheader("✅ Pre-Update Validation")
                    with st.spinner('Step 3: Validating TDS totals...'):
                        pre_validation_passed, pre_validation_df = validate_tds_totals(tds_masters_data, challan_data_list)
                    
                    st.dataframe(pre_validation_df)
                    if pre_validation_passed:
                        st.success("Pre-update validation passed successfully!")
                    else:
                        st.error("Pre-update validation failed. Please check the discrepancies above.")

                    # Generate Output File
                    output_filename = get_output_filename_from_masters(tds_masters_data)
                    output_path = os.path.join(output_dir, output_filename)
                    
                    with st.spinner('Step 4: Generating final output file...'):
                        update_output_file(template_path, output_path, tds_masters_data, challan_data_list, log_expander)
                    
                    st.balloons()
                    st.header("🎉 Processing Complete!")
                    st.success(f"Successfully generated the output file: **{output_filename}**")

                    # Provide download buttons
                    st.subheader("⬇️ Download Your Files")
                    col1, col2 = st.columns(2)
                    
                    with open(output_path, "rb") as f:
                        output_bytes = f.read()
                    
                    col1.download_button(
                        label="📥 Download Final TDS Return File",
                        data=output_bytes,
                        file_name=output_filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
