"""
SportTracker Pro - Service d'Export PDF
=====================================
Génération de rapports PDF pour joueurs, équipes et séances
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def generate_player_report(player, metrics, injuries, wellness_records):
    """
    Génère un rapport PDF complet d'un joueur
    
    Inclut:
    - Infos personnelles
    - Métriques de charge (ACWR, TSB, etc.)
    - Historique blessures
    - Suivi bien-être (derniers 30 jours)
    """
    
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch
        )
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a6aff'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1a6aff'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )
        
        story = []
        
        # 1. HEADER
        story.append(Paragraph(f"📋 FICHE JOUEUR", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # 2. INFOS PERSONNELLES
        story.append(Paragraph("Informations Personnelles", heading_style))
        
        info_data = [
            ["Joueur", f"{player.full_name}"],
            ["Poste", player.position or "-"],
            ["Équipe", player.team.name if player.team else "-"],
            ["N° Maillot", str(player.jersey_number) if player.jersey_number else "-"],
            ["Date de naissance", player.date_of_birth.strftime('%d/%m/%Y') if player.date_of_birth else "-"],
            ["Âge", f"{player.age} ans" if hasattr(player, 'age') else "-"],
            ["Statut", player.status or "-"],
        ]
        
        table = Table(info_data, colWidths=[2*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f3ff')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        
        # 3. MÉTRIQUES DE CHARGE
        if metrics:
            story.append(Paragraph("Métriques Actuelles", heading_style))
            
            metrics_data = [
                ["Métrique", "Valeur", "État"],
                ["ACWR", f"{metrics.get('acwr', 0):.2f}", _get_acwr_status(metrics.get('acwr', 0))],
                ["TSB", f"{metrics.get('tsb', 0):.0f}", _get_tsb_status(metrics.get('tsb', 0))],
                ["Charge Hebdo", f"{metrics.get('weekly_load', 0):.0f} AU", ""],
                ["Charge Chronique", f"{metrics.get('chronic_load', 0):.0f} AU", ""],
                ["Fitness (CTL)", f"{metrics.get('fitness', 0):.0f}", ""],
                ["Fatigue (ATL)", f"{metrics.get('fatigue', 0):.0f}", ""],
            ]
            
            table = Table(metrics_data, colWidths=[2*inch, 2*inch, 2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a6aff')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')])
            ]))
            
            story.append(table)
            story.append(Spacer(1, 0.3*inch))
        
        # 4. HISTORIQUE BLESSURES
        if injuries:
            story.append(Paragraph(f"Historique des Blessures ({len(injuries)})", heading_style))
            
            injury_data = [
                ["Date", "Type", "Zone", "Durée", "Statut"],
            ]
            
            for injury in injuries[:10]:  # Limiter à 10 dernières
                injury_data.append([
                    injury.date_injury.strftime('%d/%m/%Y'),
                    injury.injury_type,
                    injury.body_part,
                    f"{injury.days_out}j",
                    "Guéri" if not injury.is_active else "ACTIF"
                ])
            
            table = Table(injury_data, colWidths=[1.2*inch, 1.5*inch, 1.2*inch, 1*inch, 1.1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff6b6b')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fff5f5')])
            ]))
            
            story.append(table)
            story.append(Spacer(1, 0.3*inch))
        else:
            story.append(Paragraph("✅ Aucune blessure enregistrée", heading_style))
            story.append(Spacer(1, 0.3*inch))
        
        # 5. BIEN-ÊTRE (derniers 30 jours)
        if wellness_records:
            story.append(PageBreak())
            story.append(Paragraph("Suivi Bien-être (30 derniers jours)", heading_style))
            
            wellness_data = [
                ["Date", "Score", "Fatigue", "Sommeil", "Douleurs", "Statut"],
            ]
            
            for record in wellness_records[-10:]:  # Derniers 10 records
                wellness_data.append([
                    record.date.strftime('%d/%m/%Y'),
                    f"{record.total_score}/25",
                    f"{record.fatigue}/5",
                    f"{record.sleep_hours or '-'}h",
                    f"{record.muscle_soreness}/5",
                    "✅ BON" if record.total_score > 15 else "⚠️ À SURVEILLER"
                ])
            
            table = Table(wellness_data, colWidths=[1*inch, 1.2*inch, 1*inch, 1.2*inch, 1*inch, 1.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34d27b')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fff4')])
            ]))
            
            story.append(table)
        
        # 6. FOOTER
        story.append(Spacer(1, 0.5*inch))
        footer_text = f"Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} | SportTrackerPro v2.0"
        story.append(Paragraph(f"<i>{footer_text}</i>", styles['Normal']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        logger.info(f"✅ Rapport PDF généré pour {player.full_name}")
        return buffer
        
    except Exception as e:
        logger.error(f"❌ Erreur génération PDF: {str(e)}")
        return None


def _get_acwr_status(acwr):
    """Retourne le statut ACWR"""
    if acwr > 1.5:
        return "🔴 DANGER"
    elif acwr > 1.3:
        return "🟠 WARNING"
    else:
        return "🟢 OK"


def _get_tsb_status(tsb):
    """Retourne le statut TSB"""
    if tsb < -20:
        return "🔴 FATIGUE"
    elif tsb < -10:
        return "🟠 FATIGUE"
    elif tsb > 10:
        return "🟢 FRAIS"
    else:
        return "🟡 ÉQUILIBRÉ"


def generate_team_report(team, players, metrics_summary):
    """Génère un rapport d'équipe aggrégé"""
    
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        
        styles = getSampleStyleSheet()
        story = []
        
        # Titre
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#1a6aff'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        story.append(Paragraph(f"📊 Rapport Équipe: {team.name}", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Infos équipe
        info_data = [
            ["Équipe", team.name],
            ["Catégorie", team.category or "-"],
            ["Nombre de joueurs", str(len(players))],
            ["Joueurs disponibles", str(sum(1 for p in players if p.status == 'Disponible'))],
            ["Joueurs blessés", str(sum(1 for p in players if p.status == 'Blessé'))],
        ]
        
        table = Table(info_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f3ff')),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        
        # Résumé métrique
        if metrics_summary:
            story.append(Paragraph("Métriques Collectifs", styles['Heading2']))
            
            metrics_data = [
                ["ACWR Moyen", f"{metrics_summary.get('avg_acwr', 0):.2f}"],
                ["TSB Moyen", f"{metrics_summary.get('avg_tsb', 0):.0f}"],
                ["Charge Hebdo Moy", f"{metrics_summary.get('avg_load', 0):.0f} AU"],
            ]
            
            table = Table(metrics_data, colWidths=[3*inch, 2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a6aff')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            
            story.append(table)
        
        doc.build(story)
        buffer.seek(0)
        
        logger.info(f"✅ Rapport équipe pdf généré pour {team.name}")
        return buffer
        
    except Exception as e:
        logger.error(f"❌ Erreur rapport équipe: {str(e)}")
        return None
