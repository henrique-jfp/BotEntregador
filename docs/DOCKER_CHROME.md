DOCKER: instalar Chromium, Chromedriver e libzbar (exemplo)

Resumo
- Este guia mostra um Dockerfile base (Debian-slim) que instala:
  - Chromium (navegador headless)
  - Chromedriver (compatível com a versão do Chromium)
  - libzbar0 (nativo para `pyzbar`)
  - Dependências comuns (fonts, libs X11 necessárias para headless)
- Observação: é importante usar a versão do Chromedriver que corresponde à versão do Chromium instalada.

Exemplo de Dockerfile (Python 3.11 slim, Debian)

```Dockerfile
# Use imagem Python oficial
FROM python:3.11-slim

# Variáveis de build
ARG DEBIAN_FRONTEND=noninteractive
ARG CHROMIUM_VERSION=114.0.5735.90
ARG CHROMEDRIVER_VERSION=114.0.5735.90

# Dependências do sistema (inclui libzbar)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates wget gnupg unzip xz-utils \
       fonts-liberation libnss3 libxss1 libatk1.0-0 libatk-bridge2.0-0 libcups2 libx11-xcb1 libxcomposite1 libxcursor1 libxrandr2 libgbm1 libasound2 libgtk-3-0 libxdamage1 libxfixes3 libzbar0 \
    && rm -rf /var/lib/apt/lists/*

# Instalar Chromium (via apt se disponível) e Chromedriver (download manual para garantir versão compatível)
# Nota: você pode ajustar para instalar a versão desejada de Chromium; aqui usamos simples fallback.
RUN apt-get update && apt-get install -y --no-install-recommends chromium && rm -rf /var/lib/apt/lists/* || true

# Baixar chromedriver (garanta que CHROMEDRIVER_VERSION seja compatível com Chromium)
RUN wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" \
    && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver \
    && rm /tmp/chromedriver.zip

# Instalar dependências Python
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install -r /app/requirements.txt

# Copiar app
COPY . /app

# Expor porta e comando padrão
EXPOSE 8080
CMD ["uvicorn", "bot_multidelivery.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

Dicas importantes
- Versões: verifique a versão do Chromium instalada (`chromium --version`) e baixe a mesma major-version do Chromedriver.
- Alternativa leve: usar uma imagem base que já contenha Chrome e Chromedriver, por exemplo `selenium/standalone-chrome` ou imagens não oficiais como `zenika/alpine-chrome` (precisa de adaptações).
- `libzbar0` é necessário para `pyzbar` funcionar; certifique-se de que o wheel/pyzbar é instalado no `requirements.txt`.
- Se o build do Docker ficar muito grande, considere separar a construção do frontend (build) e copiar apenas `webapp/dist` para a imagem final.

Railway notes
- No Railway, ajuste a variável de ambiente `DISABLE_STATIC_MAPS=1` para evitar geração pesada enquanto prepara a imagem com Chromium.
- Após configurar a imagem customizada com Chromium e Chromedriver, remova `DISABLE_STATIC_MAPS` para reativar a geração PNG.

Exemplo de comando para localizar versão do Chromium no container de build

```bash
# dentro do container
chromium --version || chromium-browser --version
```


Alternativa: evitar screenshots server-side
- Usar provedores de mapas estáticos (Geoapify/Mapbox) via API (mais simples, reduz custo infra). Recomendado se não precisar do estilo visual exato.
