# ForgePDF Editor

Local-first Windows PDF editor for personal use. **Do not upload official documents or CAC credentials to GitHub.** This repository contains source code only.

## Features (initial version)
- Open, preview and navigate PDFs
- Append/merge PDFs; reorder, rotate, delete and extract pages
- Add overlay text by clicking on a page
- Replace selected existing text via search-and-redact (layout preservation is best-effort)
- Create and fill PDF text fields
- Place an unsigned PDF signature field for later CAC signing
- Optional CAC signing using pyHanko and PKCS#11 middleware (requires local configuration and testing)
- Save As, preserving the original document

## Install
Install Python 3.11+ on Windows, then in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python forgepdf.py
```

## CAC signing
Your CAC's private key remains on the card. To sign, first save the document with a signature field, then select **Sign > CAC Sign (PKCS#11)**. You must provide the path to your locally installed PKCS#11 middleware DLL and the certificate label or ID appropriate for your CAC. The app never stores your PIN. Middleware configuration varies; successful Acrobat signing does not prove that PKCS#11 signing will work. Test on a dummy PDF and validate in Acrobat before relying on this workflow. **Do not edit signed documents**: edits may invalidate signatures.

## Limitations
- Text replacement removes matching text within the selected region and inserts replacement text; it is not a full reflow editor.
- Scanned pages need OCR before existing text can be edited.
- PDF signature field creation uses pyHanko; CAC signing requires compatible middleware and is not yet verified on your reader.
- PDF forms and signature fields should be added before signing.
- Local-only processing does not itself authorize handling classified/CUI/official documents on personal equipment; follow applicable DoD/USAF handling policies.
