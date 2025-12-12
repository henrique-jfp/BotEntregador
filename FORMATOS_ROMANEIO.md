# 📋 FORMATOS DE ROMANEIO ACEITOS

O bot agora aceita **3 formatos** de romaneio:

---

## 1️⃣ TEXTO MANUAL (Mais Simples)

### Como enviar:
1. Inicie sessão: "📦 Nova Sessão do Dia"
2. Defina base
3. **Cole endereços** diretamente no chat (um por linha)

### Formatos aceitos:

#### Básico (um por linha)
```
Rua das Flores, 123
Av. Paulista, 1000
Praça da Sé, 100
```

#### Com numeração
```
1. Rua das Flores, 123
2. Av. Paulista, 1000
3. Praça da Sé, 100
```

#### Com emojis
```
📦 Rua das Flores, 123
📦 Av. Paulista, 1000
📦 Praça da Sé, 100
```

**Todas as variações acima funcionam!**

---

## 2️⃣ ARQUIVO CSV (Excel/Planilhas)

### Como enviar:
1. Inicie sessão: "📦 Nova Sessão do Dia"
2. Defina base
3. **Anexe arquivo CSV** (clique 📎)

### Formatos suportados:

#### Opção 1: Uma coluna com endereço completo
```csv
endereco
Rua das Flores, 123, São Paulo
Av. Paulista, 1000, Bela Vista
Praça da Sé, 100, Centro
```

**Nomes de coluna aceitos:**
- `endereco` / `endereço`
- `address`
- `addr`
- `end`

#### Opção 2: Colunas separadas
```csv
rua,numero,bairro,cidade
Rua das Flores,123,Jardim Paulista,São Paulo
Av. Paulista,1000,Bela Vista,São Paulo
Praça da Sé,100,Centro,São Paulo
```

**Bot combina automaticamente em endereço completo!**

#### Opção 3: Uma coluna sem cabeçalho
```csv
Rua das Flores, 123
Av. Paulista, 1000
Praça da Sé, 100
```

### Delimitadores aceitos:
- `,` (vírgula)
- `;` (ponto-e-vírgula)
- `\t` (tab)
- `|` (pipe)

**Bot detecta automaticamente!**

### Como criar CSV:

#### Excel:
1. Preencha endereços
2. Salvar Como → CSV UTF-8

#### Google Sheets:
1. Preencha endereços
2. Arquivo → Fazer download → CSV

---

## 3️⃣ ARQUIVO PDF (Documentos)

### Como enviar:
1. Inicie sessão: "📦 Nova Sessão do Dia"
2. Defina base
3. **Anexe arquivo PDF** (clique 📎)

### Tipos suportados:

#### PDF Digital (texto selecionável)
- Bot extrai texto automaticamente
- Procura padrões de endereço:
  - Rua X, 123
  - Av. Y, 456
  - Etc.

#### PDF Escaneado (imagem)
- Bot usa **OCR** (reconhecimento óptico)
- Requer **Tesseract** instalado (veja seção Instalação)

### Formatos dentro do PDF:

Qualquer estrutura que contenha endereços:

```
Lista de Entregas
1. Rua das Flores, 123
2. Av. Paulista, 1000
3. Praça da Sé, 100
```

```
ROMANEIO DIÁRIO
- Rua das Flores, 123
- Av. Paulista, 1000
- Praça da Sé, 100
```

```
Cliente: João Silva
Endereço: Rua das Flores, 123

Cliente: Maria Santos
Endereço: Av. Paulista, 1000
```

**Bot detecta padrões automaticamente!**

---

## 🔧 INSTALAÇÃO DE DEPENDÊNCIAS

### Básico (CSV + PDF digitais):
```bash
pip install pdfplumber PyPDF2
```

### Completo (inclui OCR para PDFs escaneados):

#### Windows:
1. Baixe Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
2. Instale (padrão: `C:\Program Files\Tesseract-OCR`)
3. Adicione ao PATH:
   ```powershell
   $env:PATH += ";C:\Program Files\Tesseract-OCR"
   ```
4. Instale bibliotecas Python:
   ```bash
   pip install pytesseract pdf2image
   ```

#### Linux:
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-por
pip install pytesseract pdf2image
```

#### macOS:
```bash
brew install tesseract tesseract-lang
pip install pytesseract pdf2image
```

---

## 📊 COMPARAÇÃO DE FORMATOS

| Formato | Facilidade | Velocidade | Melhor para |
|---------|------------|------------|-------------|
| **Texto Manual** | ⭐⭐⭐⭐⭐ | ⚡⚡⚡ | Poucas entregas, colar de outro lugar |
| **CSV** | ⭐⭐⭐⭐ | ⚡⚡⚡ | Planilhas existentes, muitas entregas |
| **PDF** | ⭐⭐⭐ | ⚡⚡ | Documentos prontos, romaneios impressos |

---

## 🎯 RECOMENDAÇÕES

### Use **TEXTO MANUAL** se:
- ✅ Tem menos de 20 endereços
- ✅ Já tem lista copiada de outro lugar
- ✅ Quer ser rápido

### Use **CSV** se:
- ✅ Tem planilha Excel/Google Sheets
- ✅ Precisa organizar dados estruturados
- ✅ Vai reutilizar romaneios

### Use **PDF** se:
- ✅ Recebe romaneio em PDF de fornecedor
- ✅ Tem documento escaneado
- ✅ Não pode editar formato original

---

## ❓ PROBLEMAS COMUNS

### "Nenhum endereço válido encontrado"
**Causas:**
- Arquivo vazio
- Formato não reconhecido
- PDF sem texto (precisa OCR)

**Solução:**
- Verifique se há endereços no arquivo
- Tente exportar novamente
- Para PDF escaneado, instale Tesseract

### "Erro ao processar arquivo"
**Causas:**
- Dependência faltando (pdfplumber, PyPDF2)
- Arquivo corrompido
- Formato incompatível

**Solução:**
```bash
pip install pdfplumber PyPDF2 pytesseract pdf2image
```

### CSV não detecta colunas
**Causas:**
- Delimitador não padrão
- Encoding errado

**Solução:**
- Salve como "CSV UTF-8"
- Teste com `;` em vez de `,`

---

## 📝 EXEMPLOS PRÁTICOS

### Exemplo 1: Texto Manual
```
Chat do Bot:
Você: 📦 Nova Sessão do Dia
Bot: Onde está a base?
Você: Rua X, 100

Bot: Agora envie romaneios
Você: [Cola lista de endereços]
Rua A, 123
Rua B, 456
Rua C, 789

Bot: ✅ Romaneio #ABC123 adicionado!
     📦 3 pacotes
```

### Exemplo 2: CSV
```
Arquivo: entregas.csv
endereco
Rua A, 123
Rua B, 456
Rua C, 789

Chat do Bot:
Você: 📦 Nova Sessão do Dia
Bot: Onde está a base?
Você: Rua X, 100

Bot: Agora envie romaneios
Você: [Anexa entregas.csv]

Bot: 📄 Processando CSV...
     ✅ Romaneio #XYZ789 adicionado!
     📦 3 pacotes
```

### Exemplo 3: PDF
```
Arquivo: romaneio_hoje.pdf
(Conteúdo do PDF)
ROMANEIO - 12/12/2025
1. Rua A, 123
2. Rua B, 456
3. Rua C, 789

Chat do Bot:
Você: 📦 Nova Sessão do Dia
Bot: Onde está a base?
Você: Rua X, 100

Bot: Agora envie romaneios
Você: [Anexa romaneio_hoje.pdf]

Bot: 📕 Processando PDF...
     ✅ Romaneio #PDF456 adicionado!
     📦 3 pacotes
```

---

## 🚀 FLUXO COMPLETO (Com Arquivo)

```
1. /start
2. "📦 Nova Sessão do Dia"
3. Digite endereço da base
4. Clique 📎 (anexar)
5. Escolha arquivo (.csv ou .pdf)
6. Bot processa automaticamente
7. Veja total: "Total acumulado: X pacotes"
8. Pode anexar mais arquivos (repete passo 4)
9. Quando terminar: /fechar_rota
10. Bot divide em rotas otimizadas
11. Atribua rotas aos entregadores
```

---

## 🔄 MISTURANDO FORMATOS

**Pode usar vários formatos na mesma sessão!**

```
1. Anexa CSV com 50 endereços
   ✅ 50 pacotes

2. Cola texto manual com 5 endereços
   ✅ 5 pacotes
   Total: 55 pacotes

3. Anexa PDF com 10 endereços
   ✅ 10 pacotes
   Total: 65 pacotes

4. /fechar_rota
   Bot divide 65 pacotes em 2 rotas
```

---

**Documentação completa!** 📋  
Escolha o formato que funciona melhor para você!
