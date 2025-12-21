"""
📄 SERVIÇO DE EXPORTAÇÃO
Exporta relatórios financeiros para Excel e PDF
"""
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ExportService:
    """Serviço de exportação de relatórios"""
    
    def __init__(self, output_dir: str = "data/exports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_to_excel(
        self, 
        daily_reports: List[Dict],
        week_start: Optional[datetime] = None,
        week_end: Optional[datetime] = None
    ) -> str:
        """
        Exporta relatórios para Excel
        
        Args:
            daily_reports: Lista de relatórios diários
            week_start: Data de início (opcional)
            week_end: Data de fim (opcional)
        
        Returns:
            Caminho do arquivo gerado
        """
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
            from openpyxl.utils import get_column_letter
        except ImportError:
            logger.error("openpyxl não instalado. Instale com: pip install openpyxl")
            raise ImportError("openpyxl é necessário para exportar Excel")
        
        # Cria workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Relatório Financeiro"
        
        # Estilos
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True, size=12)
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Título
        ws['A1'] = "RELATÓRIO FINANCEIRO"
        ws['A1'].font = Font(bold=True, size=16)
        ws.merge_cells('A1:G1')
        
        # Período
        if week_start and week_end:
            ws['A2'] = f"Período: {week_start.strftime('%d/%m/%Y')} a {week_end.strftime('%d/%m/%Y')}"
        else:
            ws['A2'] = f"Exportado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        ws.merge_cells('A2:G2')
        
        # Headers
        row = 4
        headers = ['Data', 'Receita', 'Custos Entregadores', 'Outros Custos', 'Lucro Líquido', 'Pacotes', 'Entregas']
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
            cell.border = border
        
        # Dados
        total_revenue = 0
        total_delivery_costs = 0
        total_other_costs = 0
        total_profit = 0
        total_packages = 0
        total_deliveries = 0
        
        for report in daily_reports:
            row += 1
            data = [
                report['date'],
                report['revenue'],
                report['delivery_costs'],
                report['other_costs'],
                report['net_profit'],
                report['total_packages'],
                report['total_deliveries']
            ]
            
            for col, value in enumerate(data, start=1):
                cell = ws.cell(row=row, column=col, value=value)
                cell.border = border
                
                # Formatação de moeda
                if col in [2, 3, 4, 5]:
                    cell.number_format = 'R$ #,##0.00'
                    cell.alignment = Alignment(horizontal='right')
                elif col == 1:
                    cell.alignment = Alignment(horizontal='center')
                else:
                    cell.alignment = Alignment(horizontal='center')
            
            # Acumula totais
            total_revenue += report['revenue']
            total_delivery_costs += report['delivery_costs']
            total_other_costs += report['other_costs']
            total_profit += report['net_profit']
            total_packages += report['total_packages']
            total_deliveries += report['total_deliveries']
        
        # Linha de totais
        row += 1
        ws.cell(row=row, column=1, value="TOTAL").font = Font(bold=True)
        ws.cell(row=row, column=2, value=total_revenue).number_format = 'R$ #,##0.00'
        ws.cell(row=row, column=3, value=total_delivery_costs).number_format = 'R$ #,##0.00'
        ws.cell(row=row, column=4, value=total_other_costs).number_format = 'R$ #,##0.00'
        ws.cell(row=row, column=5, value=total_profit).number_format = 'R$ #,##0.00'
        ws.cell(row=row, column=6, value=total_packages)
        ws.cell(row=row, column=7, value=total_deliveries)
        
        for col in range(1, 8):
            cell = ws.cell(row=row, column=col)
            cell.fill = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
            cell.font = Font(bold=True)
            cell.border = border
        
        # Ajusta largura das colunas
        for col in range(1, 8):
            ws.column_dimensions[get_column_letter(col)].width = 18
        
        # Salva arquivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"relatorio_financeiro_{timestamp}.xlsx"
        filepath = self.output_dir / filename
        
        wb.save(filepath)
        logger.info(f"Excel exportado: {filepath}")
        
        return str(filepath)
    
    def export_to_pdf(
        self,
        daily_reports: List[Dict],
        week_start: Optional[datetime] = None,
        week_end: Optional[datetime] = None,
        partner_config: Optional[Dict] = None,
        weekly_summary: Optional[Dict] = None
    ) -> str:
        """
        Exporta relatórios para PDF
        
        Args:
            daily_reports: Lista de relatórios diários
            week_start: Data de início
            week_end: Data de fim
            partner_config: Configuração dos sócios
            weekly_summary: Resumo semanal com divisão
        
        Returns:
            Caminho do arquivo gerado
        """
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
        except ImportError:
            logger.error("reportlab não instalado. Instale com: pip install reportlab")
            raise ImportError("reportlab é necessário para exportar PDF")
        
        # Cria documento
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"relatorio_financeiro_{timestamp}.pdf"
        filepath = self.output_dir / filename
        
        doc = SimpleDocTemplate(str(filepath), pagesize=landscape(A4))
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#366092'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#666666'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        # Título
        elements.append(Paragraph("RELATÓRIO FINANCEIRO", title_style))
        
        # Período
        if week_start and week_end:
            period_text = f"Período: {week_start.strftime('%d/%m/%Y')} a {week_end.strftime('%d/%m/%Y')}"
        else:
            period_text = f"Exportado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
        
        elements.append(Paragraph(period_text, subtitle_style))
        elements.append(Spacer(1, 20))
        
        # Tabela de dados diários
        data = [['Data', 'Receita', 'Custos\nEntregadores', 'Outros\nCustos', 'Lucro\nLíquido', 'Pacotes', 'Entregas']]
        
        total_revenue = 0
        total_delivery_costs = 0
        total_other_costs = 0
        total_profit = 0
        total_packages = 0
        total_deliveries = 0
        
        for report in daily_reports:
            data.append([
                report['date'],
                f"R$ {report['revenue']:,.2f}",
                f"R$ {report['delivery_costs']:,.2f}",
                f"R$ {report['other_costs']:,.2f}",
                f"R$ {report['net_profit']:,.2f}",
                str(report['total_packages']),
                str(report['total_deliveries'])
            ])
            
            total_revenue += report['revenue']
            total_delivery_costs += report['delivery_costs']
            total_other_costs += report['other_costs']
            total_profit += report['net_profit']
            total_packages += report['total_packages']
            total_deliveries += report['total_deliveries']
        
        # Linha de totais
        data.append([
            'TOTAL',
            f"R$ {total_revenue:,.2f}",
            f"R$ {total_delivery_costs:,.2f}",
            f"R$ {total_other_costs:,.2f}",
            f"R$ {total_profit:,.2f}",
            str(total_packages),
            str(total_deliveries)
        ])
        
        # Cria tabela
        table = Table(data, colWidths=[3*cm, 3.5*cm, 3.5*cm, 3*cm, 3.5*cm, 2.5*cm, 2.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#DCE6F1')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 30))
        
        # Se tiver resumo semanal, adiciona divisão de lucros
        if weekly_summary and partner_config:
            elements.append(Paragraph("DIVISÃO DE LUCROS", title_style))
            elements.append(Spacer(1, 10))
            
            division_data = [
                ['Item', 'Valor'],
                ['Lucro Bruto', f"R$ {weekly_summary['gross_profit']:,.2f}"],
                [f"Reserva ({partner_config['reserve_percentage']*100:.0f}%)", 
                 f"R$ {weekly_summary['reserve_amount']:,.2f}"],
                ['Lucro Distribuível', f"R$ {weekly_summary['distributable_profit']:,.2f}"],
                ['', ''],
                [f"{partner_config['partner_1_name']} ({partner_config['partner_1_share']*100:.0f}%)", 
                 f"R$ {weekly_summary['partner_1_share']:,.2f}"],
                [f"{partner_config['partner_2_name']} ({partner_config['partner_2_share']*100:.0f}%)", 
                 f"R$ {weekly_summary['partner_2_share']:,.2f}"],
            ]
            
            division_table = Table(division_data, colWidths=[12*cm, 8*cm])
            division_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#F0F0F0')),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -2), (-1, -1), 11),
            ]))
            
            elements.append(division_table)
        
        # Gera PDF
        doc.build(elements)
        logger.info(f"PDF exportado: {filepath}")
        
        return str(filepath)


# Instância global
export_service = ExportService()
