import zipfile
import xml.etree.ElementTree as ET
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

with zipfile.ZipFile('양식/회의록 양식.hwpx', 'r') as z:
    raw = z.read('Contents/section0.xml')
    root = ET.fromstring(raw)
    
    ns = {
        'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph',
        'hs': 'http://www.hancom.co.kr/hwpml/2011/section'
    }
    
    # Check paragraphs outside tables
    print("=== All Top-level / Paragraph Texts ===")
    for p in root.findall('.//hp:p', ns):
        texts = [t.text for t in p.findall('.//hp:t', ns) if t.text]
        if texts:
            print("P text:", "".join(texts))
            
    print("\n=== Tables ===")
    tbls = root.findall('.//hp:tbl', ns)
    print(f"Total tables: {len(tbls)}")
    for i, tbl in enumerate(tbls):
        print(f"\n--- Table {i+1} ---")
        for tr in tbl.findall('.//hp:tr', ns):
            row_cells = []
            for tc in tr.findall('./hp:tc', ns):
                texts = [t.text for t in tc.findall('.//hp:t', ns) if t.text]
                cell_text = " ".join(texts).strip()
                cell_addr = tc.find('hp:cellAddr', ns)
                addr_str = f"({cell_addr.get('colAddr')},{cell_addr.get('rowAddr')})" if cell_addr is not None else ""
                row_cells.append(f"{addr_str}: '{cell_text}'")
            print(" | ".join(row_cells))
