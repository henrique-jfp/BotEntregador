# Bot Entregador - Project Context

## Project Overview
BotEntregador is an enterprise-grade logistics management platform designed to automate and optimize delivery operations. It features a hybrid architecture:
- **Telegram Bot:** For deliverers to manage their daily routes, check balances (`/saldo`), and receive notifications.
- **WebApp Dashboard (React):** For admins to import manifests (romaneios), optimize routes using AI clustering, track deliveries in real-time via WebSockets, and manage finances.

### Key Features
- **AI Route Optimization:** Uses K-Means clustering to balance routes and Google OR-Tools for TSP (Traveling Salesman Problem) sequence optimization.
- **Real-time Tracking:** WebSocket-based dashboard for live monitoring of delivery progress.
- **Automated Financials:** Weekly balance calculation and reporting for deliverers.
- **Intelligent Parsers:** Supports PDF (with OCR), CSV, and Excel (Shopee, etc.) manifest imports.
- **Geocoding Cascade:** Efficient use of free APIs (LocationIQ, Geoapify, OSM) before falling back to Google Maps.

---

## Tech Stack

### Backend (Python 3.11+)
- **Framework:** FastAPI
- **Bot Engine:** python-telegram-bot (v22+)
- **ORM:** SQLAlchemy (with Alembic for migrations)
- **Database:** PostgreSQL
- **Optimization:** scikit-learn (Clustering), Google OR-Tools (TSP)
- **Image/OCR:** Pillow, OpenCV, pyzbar, Tesseract, pdfplumber

### Frontend (React 18+)
- **Build Tool:** Vite
- **Styling:** TailwindCSS
- **Maps:** Leaflet & React-Leaflet
- **Charts:** Recharts
- **Icons:** Lucide React

---
## 🌐 IDIOMA E COMUNICAÇÃO 
- **Interação com o Usuário:** Responda SEMPRE em Português do Brasil (PT-BR).
- **Comentários no Código:** Em Português, alinhados ao padrão do projeto.
- **Controle de Versão (Git):** STRICTLY PORTUGUESE. Commits, mensagens de merge, títulos de PR e descrições devem ser 100% em Português, seguindo o padrão do projeto.

## Building and Running

### Backend Setup
1.  **Environment:** Create a `.env` file based on the template in `README.md`.
2.  **Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Database Migrations:**
    ```bash
    alembic upgrade head
    ```
4.  **Run Application:**
    ```bash
    python main_multidelivery.py
    ```
    *Note: This starts both the FastAPI server (on PORT 8080 by default) and the Telegram Bot polling.*

### Frontend Setup
1.  **Navigate to webapp:**
    ```bash
    cd webapp
    ```
2.  **Install Dependencies:**
    ```bash
    npm install
    ```
3.  **Run Development Server:**
    ```bash
    npm run dev
    ```
4.  **Production Build:**
    ```bash
    npm run build
    ```

---

## Architecture & Project Structure

- `bot_multidelivery/`: Core backend logic.
    - `routers/`: Modular API endpoints (admin, auth, financial, romaneio, etc.).
    - `services/`: Business logic services (geocoding, financial, dashboard, etc.).
    - `parsers/`: Logic for extracting data from various file formats.
    - `models.py`: SQLAlchemy database models.
    - `session.py`: Session management singleton and logic.
- `webapp/`: React frontend source code.
- `alembic/`: Database migration scripts.
- `docs/`: Comprehensive documentation on architecture, deployment, and usage.
- `data/`: Local cache and exports.

---

## Development Conventions

- **Modular APIs:** New functionality should be added as a new router in `bot_multidelivery/routers/` and registered in `main_multidelivery.py`.
- **Type Hinting:** Use Python type hints throughout the backend for better maintainability and editor support.
- **Asynchronous Code:** Prefer `async/await` for API endpoints and bot handlers.
- **Frontend State:** The webapp is a SPA; use React Router for navigation and standard hooks for state management.
- **Deployment:** The project is configured for Railway using `nixpacks.toml`.

## 🔄 WORKFLOW DE FINALIZAÇÃO DA TAREFA
Ao finalizar a implementação ou correção:
1.  Apresente um resumo conciso do que foi feito (em PT-BR).
2.  Faça uma analise do README.md decida se é necessário atualizar(em PT-BR)
3.  Sugira um descrição de commit para salvar o trabalho, **garantindo a regra do idioma em Português**:
    ```bash
    git commit -m "feat(scope): descrição concisa em português da mudança"
    ```