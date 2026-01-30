
import json
from datetime import datetime

file_path = "c:\\BotEntregador\\bot_multidelivery\\services\\financial_service.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False

for line in lines:
    if "def close_day(" in line:
        new_lines.append(line)
        new_lines.append("        date: datetime,\n")
        new_lines.append("        revenue: float,\n")
        new_lines.append("        deliverer_costs: Dict[str, float],\n")
        new_lines.append("        other_costs: float = 0.0,\n")
        new_lines.append("        total_packages: int = 0,\n")
        new_lines.append("        total_deliveries: int = 0,\n")
        new_lines.append("        expenses: List[dict] = None\n")
        new_lines.append("    ) -> DailyFinancialReport:\n")
        skip = True
    elif skip and "-> DailyFinancialReport:" in line:
        skip = False
        # Continue appending the body logic replacement
        new_lines.append('        """\n')
        new_lines.append('        Fecha o dia financeiro\n')
        new_lines.append('        """\n')
        new_lines.append('        total_delivery_cost = sum(deliverer_costs.values())\n')
        new_lines.append('\n')
        new_lines.append('        if other_costs == 0.0 and expenses:\n')
        new_lines.append("            other_costs = sum(e['value'] for e in expenses)\n")
        new_lines.append('\n')
        new_lines.append('        net_profit = revenue - total_delivery_cost - other_costs\n')
        new_lines.append('\n')
        new_lines.append('        report = DailyFinancialReport(\n')
        new_lines.append("            date=date.strftime('%Y-%m-%d'),\n")
        new_lines.append('            revenue=revenue,\n')
        new_lines.append('            delivery_costs=total_delivery_cost,\n')
        new_lines.append('            other_costs=other_costs,\n')
        new_lines.append('            net_profit=net_profit,\n')
        new_lines.append('            total_packages=total_packages,\n')
        new_lines.append('            total_deliveries=total_deliveries,\n')
        new_lines.append('            deliverer_breakdown=deliverer_costs,\n')
        new_lines.append('            expenses=expenses or []\n')
        new_lines.append('        )\n')
        new_lines.append('\n')
        new_lines.append('        # Salva o dia\n')
        new_lines.append('        file_path = self.daily_dir / f"{report.date}.json"\n')
        new_lines.append("        with open(file_path, 'w', encoding='utf-8') as f:\n")
        new_lines.append('            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)\n')
        new_lines.append('\n')
        new_lines.append('        logger.info(f"✅ Fechamento diário salvo: {file_path}")\n')
        new_lines.append('        return report\n')

        # Skip original body lines until next method or end
        continue 
    elif "return report" in line and skip:
        # End of skipping
        skip = False
        continue

    if not skip:
        # Hacky skip logic for lines inside the function being replaced
        # Better: Just read file, find start/end index, replace block.
        pass

# The python logic above is too fragile with `skip`. I will use simple string replacement via python script using read()
