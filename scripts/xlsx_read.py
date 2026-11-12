"""Minimal read-only .xlsx reader (standard library only). Returns the first sheet as a list of dicts."""
import re
import zipfile
import xml.etree.ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def _col_index(ref):
    letters = re.match(r"[A-Z]+", ref).group()
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def _text(el):
    return "".join(t.text or "" for t in el.iter(f"{{{NS['m']}}}t"))


def read_first_sheet(path):
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            shared = [_text(si) for si in root.findall("m:si", NS)]
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rid = wb.find("m:sheets/m:sheet", NS).attrib[REL_NS]
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        target = next(r.attrib["Target"] for r in rels if r.attrib["Id"] == rid)
        target = target.lstrip("/")
        sheet_path = target if target.startswith("xl/") else "xl/" + target
        sheet = ET.fromstring(z.read(sheet_path))

    grid = []
    for row in sheet.iter(f"{{{NS['m']}}}row"):
        cells = {}
        for c in row.findall("m:c", NS):
            t = c.attrib.get("t")
            v = c.find("m:v", NS)
            if t == "s" and v is not None:
                val = shared[int(v.text)]
            elif t == "inlineStr":
                val = _text(c)
            else:
                val = v.text if v is not None else ""
            cells[_col_index(c.attrib["r"])] = val
        if any(str(x).strip() for x in cells.values()):
            width = max(cells) + 1
            grid.append([cells.get(i, "") for i in range(width)])
    if not grid:
        return []
    header = grid[0]
    rows = []
    for g in grid[1:]:
        g = g + [""] * (len(header) - len(g))
        rows.append({(h or f"col{i}"): g[i] for i, h in enumerate(header)})
    return rows
