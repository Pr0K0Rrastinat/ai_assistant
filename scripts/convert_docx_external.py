# scripts/convert_docx_external.py
from docx2pdf import convert
import sys
from pathlib import Path

docx_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])
convert(str(docx_path), str(output_path))
