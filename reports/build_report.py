"""Build the concise application case-study PDF from the observed run log."""
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
                                Table, TableStyle, PageBreak, KeepTogether)
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import HorizontalBarChart

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "xcel_associate_data_scientist_case_study.pdf"
DATA = json.loads((ROOT / "reports" / "observed_run.json").read_text())
NAVY = colors.HexColor("#12253F")
BLUE = colors.HexColor("#2864DC")
TEAL = colors.HexColor("#20A694")
PALE = colors.HexColor("#F1F5FA")
INK = colors.HexColor("#243447")
MUTED = colors.HexColor("#63748A")


def page(canvas, doc):
    canvas.saveState()
    w, h = letter
    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 0.16 * inch, w, 0.16 * inch, fill=1, stroke=0)
    canvas.setStrokeColor(colors.HexColor("#DCE4EE"))
    canvas.line(0.62 * inch, 0.53 * inch, w - 0.62 * inch, 0.53 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(0.64 * inch, 0.35 * inch, "Independent EIA-930 portfolio case study | Not affiliated with Xcel Energy")
    canvas.drawRightString(w - 0.64 * inch, 0.35 * inch, f"{doc.page}")
    canvas.restoreState()


def make_styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="Eyebrow", parent=s["Normal"], fontName="Helvetica-Bold", fontSize=8,
                         leading=11, textColor=TEAL, spaceAfter=5, uppercase=True))
    s.add(ParagraphStyle(name="Title2", parent=s["Title"], fontName="Helvetica-Bold", fontSize=25,
                         leading=29, textColor=NAVY, alignment=TA_LEFT, spaceAfter=8))
    s.add(ParagraphStyle(name="Deck", parent=s["BodyText"], fontSize=10.5, leading=15,
                         textColor=MUTED, spaceAfter=12))
    s.add(ParagraphStyle(name="H2x", parent=s["Heading2"], fontName="Helvetica-Bold", fontSize=14,
                         leading=17, textColor=NAVY, spaceBefore=7, spaceAfter=7))
    s.add(ParagraphStyle(name="Bodyx", parent=s["BodyText"], fontSize=9.2, leading=13.4,
                         textColor=INK, spaceAfter=6))
    s.add(ParagraphStyle(name="Smallx", parent=s["BodyText"], fontSize=7.6, leading=10,
                         textColor=MUTED))
    s.add(ParagraphStyle(name="CardLabel", parent=s["Normal"], fontName="Helvetica-Bold", fontSize=7.5,
                         leading=10, textColor=MUTED))
    s.add(ParagraphStyle(name="CardValue", parent=s["Normal"], fontName="Helvetica-Bold", fontSize=17,
                         leading=20, textColor=NAVY))
    return s


def cards(styles):
    values = [("SOURCE ROWS SCANNED", "3.85M"), ("PUBLIC SOURCE FILES", "14 / 616 MB"),
              ("PSCO HOURLY ROWS", "61,368"), ("ONE-HOUR MODEL MAE", "103.72 MW")]
    cells = [[Paragraph(values[i][0], styles["CardLabel"]) for i in range(4)],
             [Paragraph(values[i][1], styles["CardValue"]) for i in range(4)]]
    t = Table(cells, colWidths=[1.73 * inch] * 4, rowHeights=[0.25 * inch, 0.40 * inch])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE),
                           ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#DFE7F0")),
                           ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    return t


def metric_chart():
    labels = ["Previous day, same hour (1h target)", "Previous hour persistence (1h)",
              "Gradient boosting (1h)", "EIA reported day-ahead"]
    vals = [343.59, 181.26, 103.72, 383.39]
    d = Drawing(470, 152)
    chart = HorizontalBarChart()
    chart.x, chart.y, chart.width, chart.height = 184, 12, 250, 120
    chart.data = [vals]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 7.3
    chart.categoryAxis.labels.fillColor = INK
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 450
    chart.valueAxis.valueStep = 100
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labels.fillColor = MUTED
    chart.valueAxis.strokeColor = colors.HexColor("#CCD7E4")
    chart.categoryAxis.strokeColor = colors.white
    chart.bars[0].fillColor = BLUE
    chart.bars[0].strokeColor = BLUE
    chart.barWidth = 15
    chart.groupSpacing = 8
    chart.valueAxis.visibleGrid = True
    chart.valueAxis.gridStrokeColor = colors.HexColor("#E6ECF3")
    chart.valueAxis.gridStrokeWidth = 0.6
    d.add(chart)
    d.add(String(438, 116, "MAE (MW)", fontName="Helvetica-Bold", fontSize=8, fillColor=MUTED))
    return d


def build():
    styles = make_styles()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(str(OUT), pagesize=letter, leftMargin=0.67 * inch,
                          rightMargin=0.67 * inch, topMargin=0.55 * inch,
                          bottomMargin=0.72 * inch, title="PSCo Hourly Demand Analysis",
                          author="Vignesh Kumar Karthikeyan")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="standard", frames=frame, onPage=page)])
    story = []
    story += [Spacer(1, 0.12 * inch), Paragraph("DATA SCIENCE WORK SAMPLE  /  ENERGY", styles["Eyebrow"]),
              Paragraph("PSCo Hourly Demand<br/>Analysis", styles["Title2"]),
              Paragraph("A focused Python and SQL case study using public EIA-930 balancing-authority data to assess hourly demand quality, operating patterns, and forecast error.", styles["Deck"]),
              cards(styles), Spacer(1, 0.14 * inch), Paragraph("Business question", styles["H2x"]),
              Paragraph("How can reported hourly demand data be validated and analyzed to surface useful operating patterns and evaluate short-term forecast baselines?", styles["Bodyx"]),
              Paragraph("What I built", styles["H2x"])]
    arch = Table([[Paragraph("EIA-930 bulk CSV", styles["Bodyx"]), Paragraph("Python chunked ingest", styles["Bodyx"]),
                   Paragraph("SQLite + SQL", styles["Bodyx"]), Paragraph("Analysis + dashboard", styles["Bodyx"])]],
                 colWidths=[1.73 * inch] * 4, rowHeights=[0.48 * inch])
    arch.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE),
                              ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#DFE7F0")),
                              ("INNERGRID", (0, 0), (-1, -1), 2, colors.white),
                              ("LEFTPADDING", (0, 0), (-1, -1), 8),
                              ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story += [arch, Spacer(1, 0.1 * inch),
              Paragraph("Across 14 public EIA files for 2019-2025, the pipeline scanned 3,848,038 multi-authority rows (616 MB) in 50,000-row chunks and retained 61,368 PSCo hourly records. It stores the selected table in SQLite, records quality checks, and runs SQL for peak hours, demand profiles, and forecast error.", styles["Bodyx"]),
              Paragraph("Skills demonstrated", styles["H2x"])]
    skills = [["Python / data engineering", "Chunked CSV ingestion, type parsing, timestamp checks, invalid-value handling"],
              ["SQL / database", "SQLite table, time index, documented aggregation and quality queries"],
              ["Statistics / ML", "Chronological holdout, persistence baselines, MAE and RMSE"],
              ["Communication", "Demand dashboard and concise operational interpretation"]]
    table = Table([[Paragraph(f"<b>{a}</b>", styles["Bodyx"]), Paragraph(b, styles["Bodyx"])] for a, b in skills],
                  colWidths=[1.65 * inch, 5.25 * inch])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), PALE),
                               ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#DFE7F0")),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 7),
                               ("TOPPADDING", (0, 0), (-1, -1), 4),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    story += [table, Spacer(1, 0.1 * inch),
              Paragraph("Scale note: the measured workload is the multi-authority source scan; the analysis table is the PSCo-only extract. The raw CSVs are public and are downloaded by the reproducible pipeline.", styles["Smallx"]),
              PageBreak(), Spacer(1, 0.12 * inch), Paragraph("MEASURED RESULTS", styles["Eyebrow"]),
              Paragraph("Forecasts, checked honestly", styles["Title2"]),
              Paragraph("Results below are transcribed from the candidate's successful 2019-2025 PSCo pipeline run. The 80/20 split is chronological; the held-out period contains 12,233 hourly observations. The repo includes commands to reproduce the analysis from EIA's public bulk files.", styles["Deck"]),
              metric_chart(), Paragraph("On this rolling one-hour-ahead holdout, gradient boosting's MAE is 42.8% lower than previous-hour persistence and 69.8% lower than the previous-day baseline. Results are encouraging for this evaluation window, not proof of operational performance.", styles["Bodyx"])]
    metric_rows = [["Evaluation", "MAE (MW)", "RMSE (MW)", "Forecast horizon"],
                   ["Previous-hour persistence", "181.26", "230.17", "1 hour"],
                   ["Gradient boosting", "103.72", "146.03", "1 hour"],
                   ["Previous-day same hour", "343.59", "455.42", "1 hour target"],
                   ["EIA reported forecast", "383.39", "481.10", "Day-ahead"]]
    mt = Table(metric_rows, colWidths=[2.15 * inch, 1.12 * inch, 1.12 * inch, 2.5 * inch], repeatRows=1)
    mt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                            ("FONTSIZE", (0, 0), (-1, -1), 8),
                            ("TEXTCOLOR", (0, 1), (-1, -1), INK),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
                            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D7E0EA")),
                            ("ALIGN", (1, 1), (2, -1), "RIGHT"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("TOPPADDING", (0, 0), (-1, -1), 6),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [mt, Spacer(1, 0.08 * inch),
              Paragraph("Forecast horizons differ: the EIA metric is day-ahead; the model and persistence baselines are rolling one-hour-ahead. The EIA number is shown for context and is not an apples-to-apples ranking.", styles["Smallx"]),
              Paragraph("Data quality", styles["H2x"]),
              Paragraph("The run had 61,368 PSCo rows, zero duplicate timestamps, and zero missing hourly slots. It flagged 24 missing demand values and 13 nonpositive values; all 37 were excluded from demand analysis while preserving the raw observations.", styles["Bodyx"]),
              Paragraph("Scope and limits", styles["H2x"]),
              Paragraph("EIA-930 is balancing-authority data, not customer-level consumption. Timestamps are UTC end-of-hour. This project analyzes demand and forecasts only; it does not assess generation mix, weather effects, causation, or grid dispatch. Findings support exploratory analysis, not operational decisions.", styles["Bodyx"]),
              Paragraph("Source: U.S. Energy Information Administration, Form EIA-930 public bulk CSVs, eia.gov/electricity/gridmonitor. Portfolio: portfolio-website-vignesh--kvk1011.replit.app. Source code, SQL queries, tests, and dashboard are in the accompanying project archive.", styles["Smallx"])]
    doc.build(story)
    return OUT


if __name__ == "__main__":
    print(build())
