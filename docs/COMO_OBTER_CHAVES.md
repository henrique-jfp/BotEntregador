# 🔑 Guia: Como Obter as Chaves de API

Este guia detalha o passo a passo para você obter gratuitamente todas as chaves (tokens) necessárias para rodar o **Bot Entregador**. O sistema foi desenhado para utilizar APIs com generosos limites gratuitos (Free Tier), permitindo que você opere a logística sem precisar de cartão de crédito inicialmente.

---

## 1. 🤖 Token do Telegram (Obrigatório)

O Telegram é a interface principal para os entregadores e para você (Admin).

1. Abra o aplicativo do Telegram e busque por **[@BotFather](https://t.me/BotFather)** (é o bot oficial com selo de verificado).
2. Envie o comando `/newbot`.
3. Escolha um **Nome** (Ex: `Logística Expresso`).
4. Escolha um **Username** (deve terminar com `_bot` ou `Bot`, Ex: `logistica_expresso_bot`).
5. O BotFather responderá com uma mensagem contendo o seu token. Será algo como: `1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij`.
6. Copie esse valor e cole na variável `TELEGRAM_BOT_TOKEN` no arquivo `.env`.

---

## 2. 👤 Seu ID do Telegram (Obrigatório)

Para que você tenha privilégios de Administrador no painel e receba os alertas de rotas finalizadas.

1. No Telegram, busque pelo bot **[@userinfobot](https://t.me/userinfobot)**.
2. Envie qualquer mensagem (ex: `/start`) para ele.
3. Ele responderá com os seus dados. Procure a linha que diz `Id: 123456789`.
4. Copie os números e coloque na variável `ADMIN_TELEGRAM_ID`.

---

## 3. 🌍 LocationIQ (Altamente Recomendado)

O LocationIQ é nossa principal API de geocodificação (transformar textos de endereços em coordenadas Latitude/Longitude no mapa). Eles oferecem **5.000 requisições por dia de graça**.

1. Acesse: [https://locationiq.com/](https://locationiq.com/)
2. Clique em **"Sign Up"** (ou "Get Your Free API Key").
3. Preencha seus dados (Nome, Email, Senha) ou faça login com o Google/GitHub.
4. Após o login, você será redirecionado para o Dashboard.
5. Vá na aba **"Tokens"** ou **"API Access Tokens"**.
6. Se não houver um token, clique em "Create New Token".
7. Copie o valor (geralmente começa com `pk.`) e cole em `LOCATIONIQ_API_KEY`.

---

## 4. 🗺️ Geoapify (Altamente Recomendado)

O Geoapify atua como nossa segunda opção de geocodificação, além de ser o **motor principal para gerar as imagens dos mapas** que os entregadores recebem pelo Telegram. Oferece **3.000 requisições por dia de graça**.

1. Acesse: [https://www.geoapify.com/](https://www.geoapify.com/)
2. Clique no botão **"Sign Up"** ou "Get Free API Key".
3. Crie sua conta. Você receberá um e-mail de confirmação. Clique no link para verificar a conta.
4. Entre no Dashboard: [https://myprojects.geoapify.com/](https://myprojects.geoapify.com/)
5. Clique em **"Add new project"**, dê um nome como "Bot Entregador".
6. Dentro do projeto, você verá sua `API Key`. Copie a sequência de letras e números.
7. Cole no `.env` na variável `GEOAPIFY_API_KEY`.

---

## 5. 🔀 OpenRouteService (Opcional, mas recomendado)

O ORS é utilizado para **otimizar a ordem das entregas** (especialmente útil para entregas a pé ou de scooter) garantindo que o caminho traçado seja o mais eficiente possível pela malha viária real (e não apenas linha reta).

1. Acesse: [https://openrouteservice.org/sign-up/](https://openrouteservice.org/sign-up/)
2. Crie uma conta (Account Type: "Standard/Free").
3. Confirme seu e-mail.
4. Acesse o Dashboard: [https://openrouteservice.org/dev/#/home](https://openrouteservice.org/dev/#/home)
5. Clique em **"Request a token"**.
6. Escolha o tipo de token como "Free", dê um nome (Ex: "Roteador").
7. Copie o token gerado (é uma string bem longa).
8. Adicione ao `.env` como `ORS_API_KEY`.

---

## 6. 🌐 Google Maps API (Opcional / Apenas se necessário)

O sistema possui o Google Maps como o **último recurso** de geocodificação. Como ele exige cadastro de cartão de crédito (mesmo oferecendo $200 de crédito gratuito mensal), sugerimos deixar em branco a menos que as opções gratuitas acima não estejam sendo precisas o suficiente para sua cidade.

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/).
2. Crie um novo projeto.
3. Vá em "APIs e Serviços" -> "Biblioteca".
4. Pesquise e ative a **"Geocoding API"**.
5. Vá em "Credenciais" e clique em "Criar Credenciais" -> "Chave de API".
6. *(Recomendado)* Restrinja a chave para ser usada apenas com a API de Geocoding.
7. O Google solicitará que você configure o faturamento (Billing) adicionando um cartão de crédito.
8. Após configurado, copie a chave (começa com `AIzaSy...`) e coloque em `GOOGLE_API_KEY`.

---

### 🛡️ API_SECRET_KEY

Esta chave não se "obtém" em nenhum site. É uma senha interna que você mesmo inventa para proteger seu sistema.

1. Simplesmente digite uma combinação aleatória de letras, números e símbolos.
2. Exemplo: `G8#mP9$xL2@qW5!nY7&vC4*bZ1^kF0`
3. Cole na variável `API_SECRET_KEY`.

### 💡 Resumo do Fluxo Gratuito
Se você configurar apenas **LocationIQ**, **Geoapify** e o **Token do Telegram**, seu sistema terá capacidade para geocodificar até **8.000 endereços por dia** e gerar mapas de rotas totalmente de graça, sem precisar fornecer cartão de crédito em lugar nenhum.