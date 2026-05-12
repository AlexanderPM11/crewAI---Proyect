import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin, urlparse

def scrape_tripletecnologia():
    base_url = "https://tripletecnologia.com/"
    visited = set()
    to_visit = {base_url}
    all_content = ["# Información Completa de Triple Tecnología\n\nExtraída automáticamente de la web.\n"]

    print(f"Iniciando rastreo completo de {base_url}...")

    while to_visit and len(visited) < 15:  # Limitamos a 15 páginas para ser eficientes
        url = to_visit.pop()
        if url in visited:
            continue
        
        try:
            print(f"Rastreando: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            visited.add(url)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. Extraer Título y Contenido Principal
            title = soup.find('h1') or soup.find('title')
            title_text = title.get_text(strip=True) if title else url
            
            all_content.append(f"## Sección: {title_text}\nURL: {url}\n")
            
            # 2. Extraer párrafos y listas relevantes
            # Evitamos menús y footers centrándonos en etiquetas de contenido
            for element in soup.find_all(['p', 'h2', 'h3', 'li']):
                # Filtrar textos cortos o de navegación
                text = element.get_text(strip=True)
                if len(text) > 40 and not any(x in text.lower() for x in ['copyright', 'todos los derechos', 'cookies']):
                    prefix = "### " if element.name in ['h2', 'h3'] else "- " if element.name == 'li' else ""
                    all_content.append(f"{prefix}{text}")

            all_content.append("\n---\n")

            # 3. Encontrar nuevos enlaces internos
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(base_url, href)
                # Solo seguir enlaces del mismo dominio y que no sean anclas
                if urlparse(full_url).netloc == urlparse(base_url).netloc:
                    clean_url = full_url.split('#')[0].rstrip('/')
                    if clean_url not in visited and clean_url.startswith(base_url):
                        to_visit.add(clean_url)

        except Exception as e:
            print(f"Error en {url}: {e}")

    # Guardar todo en faqs.md
    with open("faqs.md", "w", encoding="utf-8") as f:
        f.write("\n".join(all_content))
    
    print(f"Exito: Ratreo completado. {len(visited)} páginas procesadas.")
    print("Archivo faqs.md actualizado con toda la información de la web.")

if __name__ == "__main__":
    scrape_tripletecnologia()
