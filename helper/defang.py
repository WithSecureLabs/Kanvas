# code reviewed 
import re
import logging
from openpyxl import load_workbook

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='kanvas.log')
logger = logging.getLogger(__name__)

def defang_text(text):
    if not text or not isinstance(text, str):
        return text
    ip_regex = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3})\.(\d{1,3})')
    http_regex = re.compile(r'(https?)(://)', re.IGNORECASE)
    domain_regex = re.compile(r'([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z0-9][-a-zA-Z0-9]*)\.([a-zA-Z]{2,})')
    defanged_text = text
    defanged_text = ip_regex.sub(r'\1[.]\2', defanged_text)
    defanged_text = http_regex.sub(r'hxxp\2', defanged_text)
    defanged_text = domain_regex.sub(r'\1[.]\2', defanged_text)
    return defanged_text

def defang_excel_file(input_file_path, output_file_path, progress_callback=None):
    try:
        logger.info(f"Starting defanging process for file: {input_file_path}")
        workbook = load_workbook(input_file_path)
        total_sheets = len(workbook.sheetnames)
        logger.info(f"Processing {total_sheets} sheets")
        for sheet_idx, sheet_name in enumerate(workbook.sheetnames):
            if progress_callback:
                progress_callback(sheet_idx, total_sheets, f"Defanging: {sheet_name}")
            logger.info(f"Processing sheet: {sheet_name}")
            sheet = workbook[sheet_name]
            for row in range(1, sheet.max_row + 1):
                for col in range(1, sheet.max_column + 1):
                    cell = sheet.cell(row=row, column=col)
                    if cell.value and isinstance(cell.value, str):
                        original_value = cell.value
                        cell.value = defang_text(original_value)
                        if original_value != cell.value:
                            logger.debug(f"Defanged: '{original_value}' -> '{cell.value}'")
        workbook.save(output_file_path)
        logger.info(f"Defanged file saved to: {output_file_path}")
        return True
    except Exception as e:
        logger.error(f"Error during defanging: {e}")
        raise Exception(f"Error during defanging: {str(e)}")

def defang_string(text):
    return defang_text(text)