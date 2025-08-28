#!/usr/bin/env python3
"""
Converte o manual do usuário de Markdown para HTML e depois para PDF usando bibliotecas simples
"""

import markdown
import os
from pathlib import Path

def markdown_to_html_pdf(md_file, output_dir):
    """Converte arquivo Markdown para HTML formatado"""
    
    # Ler o arquivo Markdown
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Converter Markdown para HTML
    html = markdown.markdown(
        md_content, 
        extensions=['tables', 'fenced_code', 'toc', 'codehilite']
    )
    
    # CSS para melhor formatação e impressão
    css_style = """
    <style>
    @media print {
        body { margin: 0; }
        .no-print { display: none; }
    }
    
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        line-height: 1.6;
        color: #333;
        max-width: 210mm;
        margin: 0 auto;
        padding: 20mm;
        background: white;
    }
    
    h1 {
        color: #2c3e50;
        border-bottom: 3px solid #3498db;
        padding-bottom: 10px;
        page-break-after: avoid;
        font-size: 2.2em;
        margin-top: 0;
    }
    
    h2 {
        color: #34495e;
        border-bottom: 2px solid #ecf0f1;
        padding-bottom: 5px;
        margin-top: 30px;
        page-break-after: avoid;
        font-size: 1.8em;
    }
    
    h3 {
        color: #7f8c8d;
        margin-top: 25px;
        page-break-after: avoid;
        font-size: 1.4em;
    }
    
    h4 {
        color: #95a5a6;
        margin-top: 20px;
        page-break-after: avoid;
        font-size: 1.2em;
    }
    
    code {
        background-color: #f8f9fa;
        padding: 2px 6px;
        border-radius: 3px;
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        font-size: 0.9em;
    }
    
    pre {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 5px;
        border-left: 4px solid #3498db;
        overflow-x: auto;
        page-break-inside: avoid;
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        font-size: 0.85em;
    }
    
    pre code {
        background: none;
        padding: 0;
    }
    
    blockquote {
        border-left: 4px solid #3498db;
        margin: 20px 0;
        padding-left: 20px;
        color: #7f8c8d;
        font-style: italic;
    }
    
    table {
        border-collapse: collapse;
        width: 100%;
        margin: 20px 0;
        page-break-inside: avoid;
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
        margin: 15px 0;
    }
    
    li {
        margin-bottom: 8px;
        page-break-inside: avoid;
    }
    
    p {
        margin: 15px 0;
        text-align: justify;
    }
    
    hr {
        border: none;
        border-top: 2px solid #ecf0f1;
        margin: 30px 0;
        page-break-after: avoid;
    }
    
    .emoji {
        font-size: 1.2em;
    }
    
    /* Quebras de página estratégicas */
    h1 {
        page-break-before: auto;
    }
    
    h2 {
        page-break-before: avoid;
    }
    
    .page-break {
        page-break-before: always;
    }
    
    /* Cabeçalho e rodapé para impressão */
    @page {
        margin: 2cm;
        @top-center {
            content: "Manual do Usuário - Zero-Click SEO & AI Citation Monitor";
            font-size: 10pt;
            color: #666;
        }
        @bottom-center {
            content: "Página " counter(page);
            font-size: 10pt;
            color: #666;
        }
    }
    </style>
    """
    
    # HTML completo
    full_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Manual do Usuário - Zero-Click SEO & AI Citation Monitor</title>
    {css_style}
</head>
<body>
    <div class="no-print" style="background: #3498db; color: white; padding: 15px; margin: -20mm -20mm 20px -20mm; text-align: center;">
        <h2 style="margin: 0; border: none; color: white;">📄 Para converter para PDF: Ctrl+P → Salvar como PDF</h2>
        <p style="margin: 5px 0 0 0; opacity: 0.9;">Configure margens personalizadas e ative "Gráficos de fundo" para melhor resultado</p>
    </div>
    {html}
    <div style="margin-top: 50px; padding-top: 20px; border-top: 2px solid #ecf0f1; text-align: center; color: #7f8c8d; font-size: 0.9em;">
        <p><strong>Manual do Usuário - Zero-Click SEO & AI Citation Monitor</strong></p>
        <p>Gerado automaticamente em {Path(md_file).stat().st_mtime}</p>
    </div>
</body>
</html>"""
    
    # Salvar HTML
    html_file = output_dir / "Manual_do_Usuario_Zero_Click_SEO.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print(f"✅ HTML criado: {html_file}")
    print(f"🌐 Abra o arquivo HTML no navegador e use Ctrl+P para salvar como PDF")
    print(f"💡 Dica: Configure margens personalizadas (1cm) e ative 'Gráficos de fundo' para melhor resultado")
    
    return html_file

if __name__ == "__main__":
    # Instalar markdown se necessário
    try:
        import markdown
    except ImportError:
        print("📦 Instalando markdown...")
        os.system("pip install markdown")
        import markdown
    
    # Caminhos dos arquivos
    current_dir = Path(__file__).parent
    md_file = current_dir / "MANUAL_DO_USUARIO.md"
    
    if not md_file.exists():
        print(f"❌ Arquivo não encontrado: {md_file}")
        exit(1)
    
    print(f"📄 Convertendo {md_file} para HTML...")
    html_file = markdown_to_html_pdf(md_file, current_dir)
    
    # Tentar abrir no navegador
    try:
        os.startfile(str(html_file))
        print(f"🚀 Abrindo {html_file} no navegador...")
    except:
        print(f"📁 Arquivo salvo em: {html_file}")
