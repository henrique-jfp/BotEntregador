# 📄 Documentação Técnica: Servidor Home Lab (M21s)

**Data de Atualização:** 24/11/2025
**Status:** 🟢 Operacional (Produção)
**Tipo:** Edge Server / Headless
**OS:** Android 10+ (via Termux F-Droid)
**Hostname:** `m21s` / `terminal.henriquedejesus.dev`
**Responsável:** Henrique

---

## 1. Hardware e Infraestrutura
Servidor de baixo consumo energético baseado em arquitetura ARM64, operando como nó de processamento leve e orquestração de IA.

### Dispositivo Principal
*   **Modelo:** Samsung Galaxy M21s
*   **Processador (CPU):** Exynos 9611 (Octa-core)
*   **Memória RAM:** 4 GB LPDDR4X
*   **Armazenamento Interno:** 64 GB
*   **Energia:** Bateria de 6000 mAh (Atua como UPS/No-Break nativo com autonomia de ~24h em caso de falha elétrica).

###  Nuvem Pessoal Híbrida
Uma solução de armazenamento acessível via navegador e explorador de arquivos.
1.  **Interface Web:** O usuário acessa `drive.henriquedejesus.dev` para gestão visual rápida.
2.  **Integração Desktop:** O PC conecta via **RaiDrive** em `dav.henriquedejesus.dev`, montando um disco virtual (`Z:`).
3.  **Backend:** O `rclone` serve a pasta local `~/nuvem` via protocolo WebDAV, permitindo edição direta de arquivos sem necessidade de download prévio.

### Rede e Conectividade
*   **Interface:** Wi-Fi 5GHz (`wlan0`).
*   **IP Local:** Dinâmico (Gerenciado via DHCP).
*   **Acesso Externo:** **Cloudflare Tunnel** (Sem exposição de portas no roteador/CGNAT).

---

## 2. Arquitetura de Acesso (Zero Trust)
O servidor não expõe portas públicas (Port Forwarding). Todo o acesso é intermediado pela rede Edge da Cloudflare.

### Fluxo de Conexão
1.  **Entrada:** `https://terminal.henriquedejesus.dev`
2.  **Firewall de Identidade (Cloudflare Access):**
    *   **Política:** `Admin Only`.
    *   **Autenticação:** Via **GitHub OAuth** ou **Token via E-mail**.
3.  **Transporte:** Túnel Criptografado (`cloudflared` daemon).
4.  **Destino:** Termux Local (`localhost:8022`).
5.  **Interface:** Renderização de terminal via Browser (SSH over HTTPS).

---

## 3. Stack de Software

### Sistema Base (Termux)
| Ferramenta | Pacote | Função |
| :--- | :--- | :--- |
| **Termux** | F-Droid | Ambiente Linux/Unix base. |
| **OpenSSH** | `openssh` | Servidor SSH (`sshd`) ouvindo na porta 8022. |
| **Cloudflared**| `cloudflared` | Agente de tunelamento para acesso remoto seguro. |
| **Termux:Boot**| F-Droid | Gerenciador de inicialização pós-boot do Android. |
| **FileBrowser**| `filebrowser`| Interface web para gerenciamento de arquivos (Nuvem Pessoal). |
| **Git** | `git` | Versionamento de código. |

### Runtimes e Processamento
*   **Python 3.x:** Execução de scripts de automação, web scraping e lógica de IA.
*   **Node.js (LTS):** Backend auxiliar e Runtime do PM2.
*   **FFmpeg:** Manipulação e conversão de mídia (áudio/vídeo).
*   **Build Essential:** Compiladores (`clang`, `make`, `rust`) para dependências nativas.

### Gerenciamento de Processos (PM2)
O **PM2** atua como *Process Manager* vitalício, garantindo alta disponibilidade.
*   **Monitoramento:** Logs em tempo real e check de status (`online`/`stopped`).
*   **Resiliência:** Reinício automático em caso de falha do script (Crash).
*   **Persistência:** Recuperação de estado após reboot do celular (`pm2 resurrect`).

---

## 4. Automação e Boot (Ciclo de Vida)

Devido às restrições do Android, o servidor possui um ciclo de vida automatizado para garantir que permaneça ativo "Headless".

### 1. Inicialização (Boot)
Ao ligar/reiniciar o celular, o aplicativo **Termux:Boot** executa automaticamente o script `~/.termux/boot/start-server.sh`:
1.  **Wake Lock:** Impede que a CPU entre em suspensão profunda.
2.  **SSHD:** Inicia o servidor SSH.
3.  **Tunnel:** O `cloudflared` inicia como serviço (se configurado) ou via PM2.
4.  **PM2 Resurrect:** Traz de volta todos os bots que estavam rodando antes de desligar.

### 2. Manutenção de Energia
*   **Bateria:** Configurado em "Sem Restrições" nas configurações do Android.
*   **Tela:** Deve permanecer desligada, mas o sistema não dorme devido ao *Wake Lock*.

---

## 5. Arquitetura dos Projetos (RAG e IA)

O servidor atua como **Orquestrador**, delegando o processamento pesado para a nuvem para economizar RAM.

### Fluxo de Dados (Futebol/Apostas/Trader)
1.  **Cérebro (Raciocínio):**
    *   **Groq API:** Inferência ultra-rápida (Llama 3 / Mixtral).
    *   **Gemini Flash:** Janelas de contexto longas e análise multimodal.
2.  **Memória (Conhecimento):**
    *   **Banco de Dados Local:** Utiliza `SQLite` como banco de dados nativo para simplicidade e portabilidade na maioria dos projetos.
    *   **Flexibilidade:** Outros projetos podem ser configurados para usar `PostgreSQL` (local ou em nuvem) quando uma solução mais robusta é necessária.
3.  **Olhos (Extração):**
    *   Scripts Locais Python.
    *   Conversão HTML -> Markdown para ingestão de dados.

---

## 6. Guia de Comandos (Cheat Sheet)

### Gerenciamento de Processos (PM2)
```bash
pm2 list              # Ver tabela de bots ativos
pm2 logs              # Ver logs de todos os bots (stream)
pm2 logs [ID/Nome]    # Ver log de um bot específico
pm2 start script.py   # Iniciar novo bot
pm2 restart all       # Reiniciar tudo
pm2 stop [ID]         # Parar um bot
pm2 delete [ID]       # Remover da lista
pm2 save              # SALVAR lista atual (Essencial para o boot funcionar)