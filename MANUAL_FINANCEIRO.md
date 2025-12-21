# 💰 MANUAL DO SISTEMA FINANCEIRO EMPRESARIAL

## 📋 VISÃO GERAL

Sistema completo de gestão financeira empresarial integrado ao bot, com:
- **Fechamento diário** automático com cálculo de custos
- **Divisão de lucros** 70/30 entre sócios
- **Reserva de caixa** 10% do lucro semanal
- **Relatórios** diários, semanais e mensais

---

## 🎯 FLUXO DIÁRIO

### 1. Realizar Operações Normais
- Importar romaneios
- Distribuir rotas
- Entregadores fazem entregas

### 2. Fechar o Dia (`/fechar_dia`)

```
1. Bot calcula automaticamente:
   - Total de pacotes
   - Entregas realizadas
   - Custo com cada entregador

2. Admin informa:
   - Receita bruta do dia
   - Outros custos operacionais (se houver)

3. Bot gera relatório:
   - Receita vs Custos
   - Lucro líquido
   - Breakdown por entregador
   - Salva automaticamente em JSON
```

**Exemplo:**
```
/fechar_dia

Bot: "Qual foi a receita bruta de hoje?"
Você: 850.00

Bot: "Houve outros custos? (combustível, estacionamento)"
Você: 25.50

✅ Relatório salvo!
```

---

## 📊 VISUALIZAR RELATÓRIOS

### Relatório Diário
```bash
/financeiro
```
Mostra fechamento do dia atual.

### Resumo Semanal
```bash
/financeiro semana
```
Últimos 7 dias com:
- Receita total
- Custos totais
- Lucro total
- Médias diárias

### Resumo Mensal
```bash
/financeiro mes
```
Mês atual com:
- Totais consolidados
- Médias diárias
- Melhor e pior dia
- Total de pacotes/entregas

---

## 💼 FECHAMENTO SEMANAL

### Quando Fazer?
- Final de cada semana (domingo)
- Ou início da próxima (segunda)

### Como Fazer?
```bash
/fechar_semana
```

### O que Acontece?

1. **Bot calcula automaticamente:**
   - Soma receitas da semana
   - Soma custos com entregadores
   - Pede custos operacionais (aluguel, contas, etc)

2. **Bot calcula divisão:**
   ```
   Lucro Bruto = Receita - Custos
   Reserva (10%) = Lucro × 0.10
   Distribuível (90%) = Lucro - Reserva
   
   Sócio 1 (70%) = Distribuível × 0.70
   Sócio 2 (30%) = Distribuível × 0.30
   ```

3. **Bot gera relatório completo:**
   - Período da semana
   - Totais de receita e custos
   - Lucro bruto
   - Valor da reserva
   - Valor para cada sócio

**Exemplo:**
```
Lucro Bruto Semanal: R$ 5.000,00

🏦 Reserva (10%): R$ 500,00
💼 Distribuível (90%): R$ 4.500,00

👤 João (70%): R$ 3.150,00
👤 Maria (30%): R$ 1.350,00
```

---

## ⚙️ CONFIGURAR SÓCIOS

### Ver Configuração Atual
```bash
/config_socios
```

### Alterar Configuração
```bash
/config_socios Nome1 70 Nome2 30 10
```

**Parâmetros:**
1. Nome do sócio 1
2. Percentual do sócio 1 (%)
3. Nome do sócio 2
4. Percentual do sócio 2 (%)
5. Percentual de reserva (%)

**Exemplo:**
```bash
/config_socios João 70 Maria 30 10
```

**Validação:**
- Percentuais dos sócios devem somar 100%
- Todos os valores são salvos automaticamente

---

## 📁 ONDE FICAM OS DADOS?

```
data/
└── financial/
    ├── config.json              # Configuração dos sócios
    ├── daily/
    │   ├── daily_2025-12-21.json
    │   ├── daily_2025-12-22.json
    │   └── ...
    └── weekly/
        ├── week_2025-12-16.json  # Segunda-feira da semana
        └── ...
```

### Formato dos Arquivos

**config.json:**
```json
{
  "partner_1_name": "João",
  "partner_1_share": 0.70,
  "partner_2_name": "Maria",
  "partner_2_share": 0.30,
  "reserve_percentage": 0.10
}
```

**daily_YYYY-MM-DD.json:**
```json
{
  "date": "2025-12-21",
  "revenue": 850.0,
  "delivery_costs": 120.0,
  "other_costs": 25.5,
  "net_profit": 704.5,
  "total_packages": 65,
  "total_deliveries": 62,
  "deliverer_breakdown": {
    "Carlos": 60.0,
    "Ana": 60.0
  }
}
```

**week_YYYY-MM-DD.json:**
```json
{
  "week_start": "2025-12-16",
  "week_end": "2025-12-22",
  "total_revenue": 5000.0,
  "total_delivery_costs": 800.0,
  "total_operational_costs": 200.0,
  "gross_profit": 4000.0,
  "reserve_amount": 400.0,
  "distributable_profit": 3600.0,
  "partner_1_share": 2520.0,
  "partner_2_share": 1080.0,
  "daily_reports": ["2025-12-16", "2025-12-17", ...]
}
```

---

## 🔥 CENÁRIOS DE USO

### Cenário 1: Dia Simples
```
1. Fazer entregas normalmente
2. Ao final: /fechar_dia
3. Informar receita: 450.00
4. Informar custos extras: 0
5. ✅ Pronto! Lucro calculado automaticamente
```

### Cenário 2: Dia com Custos Extras
```
1. Fazer entregas
2. /fechar_dia
3. Receita: 850.00
4. Custos extras: 50.00 (combustível + estacionamento)
5. ✅ Lucro líquido = 850 - custos entregadores - 50
```

### Cenário 3: Fechamento Semanal
```
1. Domingo à noite ou segunda de manhã
2. /fechar_semana
3. Informar custos operacionais da semana: 350.00
   (aluguel, energia, internet, etc)
4. Bot calcula divisão automática
5. Cada sócio vê quanto vai receber
```

### Cenário 4: Consultar Histórico
```
# Ver hoje
/financeiro

# Ver semana
/financeiro semana

# Ver mês
/financeiro mes
```

---

## 💡 BOAS PRÁTICAS

### ✅ FAZER

1. **Fechar todo dia** mesmo sem entregas (zerar dados)
2. **Anotar custos** durante o dia (não esquecer)
3. **Fechar semana** sempre no mesmo dia
4. **Backup** da pasta `data/financial/` regularmente
5. **Conferir** relatórios antes de pagar sócios

### ❌ EVITAR

1. ❌ Esquecer de fechar dias (dados incompletos)
2. ❌ Alterar JSONs manualmente (pode corromper)
3. ❌ Fechar semana sem ter fechado todos os dias
4. ❌ Mudar percentuais no meio da semana
5. ❌ Deletar arquivos de relatórios antigos

---

## 🆘 TROUBLESHOOTING

### "Nenhum dado encontrado para hoje"
**Causa:** Ainda não fechou o dia.  
**Solução:** Use `/fechar_dia` primeiro.

### "Nenhum relatório diário encontrado para a semana"
**Causa:** Falta fechar dias da semana.  
**Solução:** Feche os dias pendentes com `/fechar_dia`.

### "Percentuais devem somar 100%"
**Causa:** Config inválida.  
**Solução:** Certifique-se que os % dos sócios somam exatamente 100.

### "Nenhuma operação hoje"
**Causa:** Não há rotas distribuídas.  
**Solução:** Importe romaneios e distribua rotas antes de fechar.

---

## 📞 COMANDOS RESUMIDOS

| Comando | Descrição |
|---------|-----------|
| `/fechar_dia` | Fecha o dia e registra receita |
| `/financeiro` | Relatório de hoje |
| `/financeiro semana` | Últimos 7 dias |
| `/financeiro mes` | Mês atual |
| `/fechar_semana` | Fechamento semanal com divisão |
| `/config_socios` | Ver/alterar configuração |

---

## 🎓 EXEMPLO COMPLETO

### Segunda-feira
```
# Fazer operações
/importar
/otimizar

# Final do dia
/fechar_dia
> Receita: 680.00
> Custos: 20.00
✅ Lucro: R$ 560,00
```

### Terça a Sábado
```
# Repetir processo diário
/fechar_dia (cada dia)
```

### Domingo (Fechamento Semanal)
```
/fechar_semana
> Custos operacionais: 400.00

📊 RESULTADO:
━━━━━━━━━━━━━━━━━━
Receita Total: R$ 4.500,00
Custos Entregadores: R$ 600,00
Custos Operacionais: R$ 400,00

💰 Lucro Bruto: R$ 3.500,00

🏦 Reserva (10%): R$ 350,00
💼 Distribuível (90%): R$ 3.150,00

👤 João (70%): R$ 2.205,00
👤 Maria (30%): R$ 945,00
```

---

## 🚀 PRÓXIMOS PASSOS (Futuro)

1. **Dashboard Web** com gráficos
2. **Exportação** para Excel/PDF
3. **Integração bancária** (API Banco Inter)
4. **Projeções** de lucro futuro
5. **Alertas** de anomalias

---

**📝 Última atualização:** 21/12/2025  
**🔢 Versão:** 1.0  
**👨‍💻 Status:** ✅ Produção
