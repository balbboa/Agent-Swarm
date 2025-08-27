import os
import requests
from bs4 import BeautifulSoup
import zipfile

# Lista de URLs
urls = [
    "https://www.infinitepay.io",
    "https://www.infinitepay.io/maquininha",
    "https://www.infinitepay.io/maquininha-celular",
    "https://www.infinitepay.io/tap-to-pay",
    "https://www.infinitepay.io/pdv",
    "https://www.infinitepay.io/receba-na-hora",
    "https://www.infinitepay.io/gestao-de-cobranca",
    "https://www.infinitepay.io/gestao-de-cobranca-2",
    "https://www.infinitepay.io/link-de-pagamento",
    "https://www.infinitepay.io/loja-online",
    "https://www.infinitepay.io/boleto",
    "https://www.infinitepay.io/conta-digital",
    "https://www.infinitepay.io/conta-pj",
    "https://www.infinitepay.io/pix",
    "https://www.infinitepay.io/pix-parcelado",
    "https://www.infinitepay.io/emprestimo",
    "https://www.infinitepay.io/cartao",
    "https://www.infinitepay.io/rendimento",
    "https://www.infinitepay.io/legal/contrato-de-afiliacao",
    "https://www.infinitepay.io/legal/cedula-credito-bancario"
]

output_dir = "infinitepay_txts"
os.makedirs(output_dir, exist_ok=True)

def clean_text_from_url(url):
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        response.encoding = "utf-8"

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove elementos desnecessários
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "form", "button"]):
            tag.extract()

        # Pega apenas texto visível
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    except Exception as e:
        return f"Erro ao acessar {url}: {str(e)}"

# Criar os arquivos .txt
txt_files = []
for url in urls:
    filename = url.replace("https://www.infinitepay.io", "infinitepay").replace("/", "_").strip("_") + ".txt"
    filepath = os.path.join(output_dir, filename)
    content = clean_text_from_url(url)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    txt_files.append(filepath)
    print(f"✅ Gerado: {filename}")

# Compactar em ZIP
zip_path = "infinitepay_txts.zip"
with zipfile.ZipFile(zip_path, "w") as zipf:
    for file in txt_files:
        zipf.write(file, os.path.basename(file))

print(f"\n📦 Arquivos salvos em: {zip_path}")
