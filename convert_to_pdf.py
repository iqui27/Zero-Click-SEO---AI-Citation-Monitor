#!/usr/bin/env python3
"""
Converte o manual do usuário de Markdown para PDF
"""

import markdown
import pdfkit
import os
from pathlib import Path

def markdown_to_pdf(md_file, pdf_file):
    """Converte arquivo Markdown para PDF"""
    
    # Ler o arquivo Markdown
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Converter Markdown para HTML
    html = markdown.markdown(
        md_content, 
        extensions=['tables', 'fenced_code', 'toc', 'codehilite']
    )
    
    # CSS para melhor formatação
    css_style = """
    <style>
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        line-height: 1.6;
        color: #333;
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
    }
    h1 {
        color: #2c3e50;
        border-bottom: 3px solid #3498db;
        padding-bottom: 10px;
    }
    h2 {
        color: #34495e;
        border-bottom: 2px solid #ecf0f1;
        padding-bottom: 5px;
        margin-top: 30px;
    }
    h3 {
        color: #7f8c8d;
        margin-top: 25px;
    }
    code {
        background-color: #f8f9fa;
        padding: 2px 4px;
        border-radius: 3px;
        font-family: 'Consolas', 'Monaco', monospace;
    }
    pre {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 5px;
        border-left: 4px solid #3498db;
        overflow-x: auto;
    }
    blockquote {
        border-left: 4px solid #3498db;
        margin: 0;
        padding-left: 20px;
        color: #7f8c8d;
    }
    table {
        border-collapse: collapse;
        width: 100%;
        margin: 20px 0;
    }
    th, td {
        border: 1px solid #ddd;
        padding: 12px;
        text-align: left;
    }
    th {
        background-color: #f2f2f2;
        font-weight: bold;
    }
    ul, ol {
        padding-left: 30px;
    }
    li {
        margin-bottom: 5px;
    }
    .page-break {
        page-break-before: always;
    }
    </style>
    """
    
    # HTML completo
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Manual do Usuário - Zero-Click SEO & AI Citation Monitor</title>
        {css_style}
    </head>
    <body>
        {html}
    </body>
    </html>
    """
    
    # Opções para wkhtmltopdf
    options = {
        'page-size': 'A4',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
        'encoding': "UTF-8",
        'no-outline': None,
        'enable-local-file-access': None
    }
    
    try:
        # Converter HTML para PDF
        pdfkit.from_string(full_html, pdf_file, options=options)
        print(f"✅ PDF criado com sucesso: {pdf_file}")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar PDF: {e}")
        return False

if __name__ == "__main__":
    # Caminhos dos arquivos
    current_dir = Path(__file__).parent
    md_file = current_dir / "MANUAL_DO_USUARIO.md"
    pdf_file = current_dir / "Manual_do_Usuario_Zero_Click_SEO.pdf"
    
    if not md_file.exists():
        print(f"❌ Arquivo não encontrado: {md_file}")
        exit(1)
    
    print(f"📄 Convertendo {md_file} para PDF...")
    success = markdown_to_pdf(md_file, pdf_file)
    
    if success:
        print(f"🎉 Conversão concluída! Arquivo salvo em: {pdf_file}")
    else:
        print("❌ Falha na conversão")
