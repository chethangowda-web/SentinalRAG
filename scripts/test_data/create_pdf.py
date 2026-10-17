import os

lines = """Quarterly Financial Report - Q4 2025

Executive Summary
The company achieved record revenue of $12.5 million in Q4 2025,
representing 23% year-over-year growth. Operating expenses were
$8.2 million, resulting in an operating margin of 34.4%. Net income
reached $3.1 million, up 18% from Q4 2024.

Key Highlights:
1. Customer acquisition cost decreased by 15% to $245 per customer
2. Monthly recurring revenue grew to $4.2 million
3. Enterprise customer count increased by 40% to 280 accounts
4. Product development team expanded to 45 engineers
5. New market entry in APAC region contributed $1.8 million in revenue

Forward Outlook
For Q1 2026, management projects revenue between $13.0 million and
$13.5 million, with operating margins improving to approximately 36%
as operational leverage continues to scale. The company plans to launch
two new products in the first half of 2026.
"""

# Create minimal valid PDF
pdf = """%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj
4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
5 0 obj<</Length 6 0 R>>
stream
BT
/F1 12 Tf 50 750 Td(Quarterly Financial Report - Q4 2025)Tj
/F1 10 Tf 50 720 Td(Executive Summary)Tj
50 700 Td(The company achieved record revenue of $12.5 million in Q4 2025,)Tj
50 685 Td(representing 23% year-over-year growth. Operating expenses were)Tj
50 670 Td($8.2 million, resulting in an operating margin of 34.4%.)Tj
50 655 Td(Net income reached $3.1 million, up 18% from Q4 2024.)Tj
50 630 Td(Key Highlights:)Tj
50 615 Td(1. Customer acquisition cost decreased by 15% to $245/customer)Tj
50 600 Td(2. Monthly recurring revenue grew to $4.2 million)Tj
50 585 Td(3. Enterprise customer count increased by 40% to 280 accounts)Tj
50 570 Td(4. Product development team expanded to 45 engineers)Tj
50 555 Td(5. New market entry in APAC region contributed $1.8 million)Tj
50 530 Td(Forward Outlook)Tj
50 515 Td(For Q1 2026, management projects revenue between $13.0M and)Tj
50 500 Td($13.5M, with margins improving to ~36% as leverage scales.)Tj
50 485 Td(The company plans to launch two new products in H1 2026.)Tj
ET
endstream
endobj
6 0 obj
STREAM_LEN
endobj
xref
0 7
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000266 00000 n 
0000000335 00000 n 
000000XXXX 00000 n 
trailer
<</Size 7/Root 1 0 R>>
startxref
XXXX
%%EOF"""

# Calculate stream length
start_marker = "stream\n"
end_marker = "\nendstream"
s = pdf.find(start_marker) + len(start_marker)
e = pdf.find(end_marker)
stream_len = e - s

# Calculate xref offset
xref_marker = "xref\n"
xref_pos = pdf.find(xref_marker)

# Replace placeholders
pdf = pdf.replace("\nSTREAM_LEN\n", f"\n{stream_len}\n")
pdf = pdf.replace("000000XXXX", f"{xref_pos:010d}")
pdf = pdf.replace("startxref\nXXXX", f"startxref\n{xref_pos}")

# Fix the last xref entry
lines_list = pdf.split("\n")
for i, line in enumerate(lines_list):
    if "000000XXXX" in line:
        lines_list[i] = f"{xref_pos:010d} 00000 n "
        break
pdf = "\n".join(lines_list)

outpath = r"K:\SentinalRAG\test_data\sample.pdf"
with open(outpath, "wb") as f:
    f.write(pdf.encode("latin-1"))
print(f"Created {outpath} ({os.path.getsize(outpath)} bytes)")
