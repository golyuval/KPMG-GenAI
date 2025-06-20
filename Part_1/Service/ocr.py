from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult
from azure.core.credentials import AzureKeyCredential
from typing import Dict, List, Tuple
import base64
import io

from Core.log_config import get_module_logger

logger = get_module_logger(__name__)


class OCR:

    def __init__(self, endpoint: str, key: str):
        
        self.client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key)
        )

        logger.info("OCR Service initialized successfully")
      
    # ---------- main functinality ---------------------------------------------------

    def extract_text(self, file_content: bytes, file_type: str) -> Dict:

        logger.info(f"Starting OCR analysis for {file_type} file ({len(file_content)} bytes)")

        # ---------- prepare file -----------------------------

        mime_map = {
            'pdf': 'application/pdf',
            'jpg': 'image/jpg',
            'jpeg': 'image/jpeg',
            'png': 'image/png'
        }

        type = mime_map.get(file_type.lower(), 'application/pdf')
        logger.debug(f"Using MIME type: {type}")
        
        # ---------- analyze file -----------------------------

        poller = self.client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=file_content,
            content_type=type
        )
        logger.info("Document analysis request submitted, waiting for results...")
        
        result: AnalyzeResult = poller.result()
        logger.info(f"OCR analysis completed. Found {len(result.pages)} pages")
        
        # ---------- process results -----------------------------

        extracted_data = self.process(result)
        logger.info(f"OCR processing completed successfully. Extracted {len(extracted_data.get('lines', []))} lines")
        
        return extracted_data   
    
    def process(self, result: AnalyzeResult) -> Dict:
        
        extracted = {
            "full_text": "",
            "pages": [],
            "tables": [],
            "key_value_pairs": [],
            "lines": []
        }
        
        # ------- lines ---------------------------

        for page_idx, page in enumerate(result.pages):
            
            page_text = ""
            page_lines = []
            
            if hasattr(page, 'lines') and page.lines:
                for line in page.lines:
                    line_text = line.content
                    page_text += line_text + "\n"
                    
                    line_info = {
                        "text": line_text,
                        "page": page_idx + 1,
                        "bounding_box": self.bounding_box(line)
                    }
                    page_lines.append(line_info)
                    extracted["lines"].append(line_info)
            
            extracted["pages"].append({
                "page_number": page_idx + 1,
                "text": page_text,
                "lines": page_lines
            })
            
            extracted["full_text"] += page_text + "\n"
        
        # ------- tables ---------------------------

        if hasattr(result, 'tables') and result.tables:
            for table_idx, table in enumerate(result.tables):
                table_data = self.table(table)
                extracted["tables"].append({
                    "table_index": table_idx,
                    "data": table_data
                })
        
        # ------- key value pairs ---------------------------

        if hasattr(result, 'key_value_pairs') and result.key_value_pairs:
            for kv_pair in result.key_value_pairs:
                if kv_pair.key and kv_pair.value:
                    extracted["key_value_pairs"].append({
                        "key": kv_pair.key.content,
                        "value": kv_pair.value.content if kv_pair.value else ""
                    })
        
        logger.info(f"Extracted {len(extracted['lines'])} lines, {len(extracted['tables'])} tables")
        
        return extracted
    
    # ---------- helpers ---------------------------------------------------
    
    def bounding_box(self, element) -> List[float]:

        if hasattr(element, 'polygon') and element.polygon:
            return [float(point) for point in element.polygon] + [float(point) for point in element.polygon]
        
        return []
    
    def table(self, table) -> List[List[str]]:
        
        rows = table.row_count
        cols = table.column_count
        table_data = [["" for _ in range(cols)] for _ in range(rows)]
        
        for cell in table.cells:
            row_idx = cell.row_index
            col_idx = cell.column_index
            if row_idx < rows and col_idx < cols:
                table_data[row_idx][col_idx] = cell.content
        
        return table_data
    