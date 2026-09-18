"""
NovaFlow Transport — Technical Architecture PDF Generator
=========================================================
Generates an executive-grade, presentation-ready PDF document outlining
the technical approach, system architecture, edge vision engines,
offline resilience, and municipal workflow for NovaFlow Transport.
"""

import os
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (on pages after cover)
        if self._pageNumber > 1:
            self.drawString(54, 800, "NovaFlow Transport — Technical Architecture & Implementation Blueprint")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(54, 794, 558, 794)

        # Footer
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 45, 558, 45)
        self.drawString(54, 32, "Confidential • Smart India Hackathon Prototype • Urban Fleet Intelligence")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_str)
        self.restoreState()


def build_pdf(filename: str):
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=50,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()
    
    # Custom Palette
    C_PRIMARY = colors.HexColor("#0f172a")     # Deep slate
    C_SECONDARY = colors.HexColor("#2563eb")   # Vibrant Blue
    C_ACCENT = colors.HexColor("#0284c7")      # Cyan
    C_TEXT = colors.HexColor("#334155")        # Body text
    C_LIGHT_BG = colors.HexColor("#f8fafc")    # Card background
    C_BORDER = colors.HexColor("#cbd5e1")      # Border grey
    C_EMERALD = colors.HexColor("#059669")
    C_AMBER = colors.HexColor("#d97706")
    C_ROSE = colors.HexColor("#dc2626")

    # Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.white,
        spaceAfter=4,
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#cbd5e1"),
        spaceAfter=8,
    )
    
    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=C_PRIMARY,
        spaceBefore=12,
        spaceAfter=6,
    )
    
    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=C_SECONDARY,
        spaceBefore=8,
        spaceAfter=4,
    )
    
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=C_TEXT,
        spaceAfter=6,
    )
    
    body_bold = ParagraphStyle(
        'BodyDarkBold',
        parent=body_style,
        fontName='Helvetica-Bold',
        textColor=C_PRIMARY,
    )

    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor("#0f172a"),
    )

    badge_style = ParagraphStyle(
        'Badge',
        fontName='Helvetica-Bold',
        fontSize=7.5,
        textColor=colors.HexColor("#38bdf8"),
        spaceAfter=4,
    )

    story = []

    # ── HEADER BANNER TABLE ──
    header_data = [
        [
            Paragraph("SIH SMART URBAN MOBILITY & FLEET SENSING", badge_style),
        ],
        [
            Paragraph("NovaFlow Transport — Technical Architecture & Blueprint", title_style),
        ],
        [
            Paragraph("AI-Driven Urban Fleet Edge Sensing, Automated Road Infrastructure Inspection & Spatial Intelligence Platform", subtitle_style),
        ],
        [
            Paragraph("<b>Platform:</b> Edge AI + Cloud GIS &nbsp;&nbsp;|&nbsp;&nbsp; <b>Engine:</b> TensorRT / FastAPI / React 18 &nbsp;&nbsp;|&nbsp;&nbsp; <b>Version:</b> 1.0 Production", ParagraphStyle('Meta', fontName='Helvetica', fontSize=7.5, textColor=colors.HexColor("#94a3b8"))),
        ]
    ]
    
    header_table = Table(header_data, colWidths=[515])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#0f172a")),
        ('LEFTPADDING', (0, 0), (-1, -1), 16),
        ('RIGHTPADDING', (0, 0), (-1, -1), 16),
        ('TOPPADDING', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
        ('LINEBELOW', (0, 2), (-1, 2), 0.5, colors.HexColor("#334155")),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 12))

    # ── 1. EXECUTIVE SUMMARY & PHILOSOPHY ──
    story.append(Paragraph("1. Executive Summary & Core Philosophy", h1_style))
    story.append(Paragraph(
        "Municipalities struggle with deteriorating roads, unchecked traffic bottlenecks, and unrecorded road safety hazards. Traditional inspection techniques rely on sporadic citizen complaint portals or specialized Laser Profiler Survey Vehicles that cost upwards of ₹1.5 Crore ($180,000) per vehicle. As a result, municipal road repairs remain purely <i>reactive</i> rather than <i>proactive</i>.",
        body_style
    ))
    
    callout_text = Paragraph(
        "<b>The NovaFlow Technical Paradigm:</b> Instead of deploying dedicated survey assets or streaming terabytes of video to costly cloud infrastructure, NovaFlow converts <b>existing city transit buses</b> into autonomous mobile sensing agents. Every bus silently inspects pavement quality, monitors traffic density, and flags safety hazards while performing regular scheduled passenger trips.",
        body_style
    )
    callout_table = Table([[callout_text]], colWidths=[515])
    callout_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LINELEFT', (0, 0), (-1, -1), 3, C_SECONDARY),
    ]))
    story.append(callout_table)
    story.append(Spacer(1, 10))

    # ── 3 CORE PILLARS TABLE ──
    pillars_data = [
        [
            Paragraph("<b>⚡ Edge-First AI Inference</b>", body_bold),
            Paragraph("<b>📡 Store-and-Forward Buffer</b>", body_bold),
            Paragraph("<b>🔒 Privacy by Design</b>", body_bold),
        ],
        [
            Paragraph("Inference runs on-vehicle (Jetson / Coral TPU). Transmits only 1–2 KB JSON event telemetry and compressed 5-sec proof clips, saving 99.8% cellular bandwidth.", body_style),
            Paragraph("Transactional SQLite queues store events when crossing cellular dead zones (tunnels, flyovers, peripheries). Auto-drains on network recovery.", body_style),
            Paragraph("Automated facial and non-violating plate blurring at source. Raw video held in volatile 30s RAM ring buffer and immediately erased unless triggered.", body_style),
        ]
    ]
    pillars_table = Table(pillars_data, colWidths=[171, 171, 173])
    pillars_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), C_LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(pillars_table)
    story.append(Spacer(1, 12))

    # ── 2. THE 3-TIER ARCHITECTURE ──
    story.append(Paragraph("2. End-to-End 3-Tier Architecture", h1_style))
    story.append(Paragraph(
        "NovaFlow adopts a strictly decoupled, micro-service architecture divided into three discrete tiers:",
        body_style
    ))

    arch_steps = [
        ["TIER 1: ON-VEHICLE EDGE NODE (BUS)", "4x Multi-Angle Cameras (Front, Rear, Left, Right) + High-Precision GPS Telemetry\n• Dynamic frame sampling calibrated to bus speed (saves compute at stops)\n• 4 Multi-Task Vision Detectors (YOLOv8 / TensorRT & ONNX)\n• Temporal Consistency Validator: N-frame defect confirmation\n• Local Store-and-Forward SQLite Spool Buffer with transactional locks\n• Network Manager with exponential retry backoff (MQTT & HTTPS)"],
        ["TIER 2: INGESTION & CENTRAL BACKEND", "FastAPI Ingestion Gateway (Async HTTP 202 Accepted)\n• Redis Streams Async Ingestion Queue (High throughput, zero dropped events)\n• Background Event Processor Worker Pool\n• Haversine Spatial Clustering & Multi-Bus Deduplication (<15m consensus)\n• PostgreSQL 16 + PostGIS Relational Database & GeoJSON services\n• Tamper-Evident SHA-256 Audit Ledger & Evidence Vault\n• Urban Analytics Engine (Congestion, Heatmaps, Route Delay Calibrator)"],
        ["TIER 3: COMMAND & DISPATCH FRONTEND", "Full-Screen React 18 & Vite 5 GIS Command Center (12 Map Layers)\n• Leaflet & Google Maps Cartographic Tile Layers with Zoom Clustering\n• 5-Stage Lifecycle State Machine (Unverified → Confirmed → Repair → Resolved)\n• Multi-Stakeholder Consoles: Traffic Police, Road Engineering, Public Portal\n• Automated Work Order Generation (WO-2026-XXXX) dispatched to field crews"]
    ]

    arch_table_data = []
    for tier, desc in arch_steps:
        arch_table_data.append([
            Paragraph(f"<b>{tier}</b>", ParagraphStyle('THead', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor("#0f172a"))),
            Paragraph(desc.replace('\n', '<br/>'), body_style)
        ])

    arch_table = Table(arch_table_data, colWidths=[150, 365])
    arch_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ('BACKGROUND', (1, 0), (1, -1), colors.white),
        ('BOX', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(arch_table)

    story.append(PageBreak())

    # ── 3. THE 4 EDGE AI VISION ENGINES ──
    story.append(Paragraph("3. The 4 Specialized Edge AI Vision Engines", h1_style))
    story.append(Paragraph(
        "Each bus hosts four analytical computer vision pipelines operating in real time on quantized neural nets:",
        body_style
    ))

    engines_data = [
        [
            Paragraph("<b>🕳️ 1. Road Surface & Infrastructure Defect Engine</b>", body_bold),
            Paragraph("<b>🚗 2. Traffic Density & Flow Intelligence Engine</b>", body_bold),
        ],
        [
            Paragraph(
                "• <b>Targets:</b> Potholes, alligator cracking, waterlogging, obscured signs, broken medians, worn zebra crossings.<br/>"
                "• <b>Telemetry:</b> Surface area, estimated depth (cm), and bump accelerometer cross-check.<br/>"
                "• <b>Verification:</b> Requires multi-frame temporal persistence to suppress false positives.",
                body_style
            ),
            Paragraph(
                "• <b>Targets:</b> Vehicle classification (buses, cars, 2-wheelers, auto-rickshaws), volume tracking.<br/>"
                "• <b>Telemetry:</b> ByteTrack/DeepSORT trajectories, velocity estimation, corridor queue lengths.<br/>"
                "• <b>Analysis:</b> Automated Level-of-Service (LOS A–F) bottleneck detection.",
                body_style
            ),
        ],
        [
            Paragraph("<b>🚨 3. Safety & Incident Anomaly Engine</b>", body_bold),
            Paragraph("<b>📸 4. ANPR & Dedicated BRT Lane Enforcement</b>", body_bold),
        ],
        [
            Paragraph(
                "• <b>Targets:</b> Sudden heavy deceleration spikes (>0.6g), trajectory deflection, near-misses.<br/>"
                "• <b>Safety:</b> Pedestrian presence in active road lanes, vulnerable school/market zones.<br/>"
                "• <b>Action:</b> Dispatches high-priority critical alerts to Traffic Police quick-response units.",
                body_style
            ),
            Paragraph(
                "• <b>Targets:</b> Unauthorized private vehicle intrusion into designated public bus lanes.<br/>"
                "• <b>OCR Pipeline:</b> Fast plate localization + CRNN text recognition.<br/>"
                "• <b>Privacy:</b> Automatic blurring of compliant vehicles; non-violator plates never stored.",
                body_style
            ),
        ]
    ]

    engines_table = Table(engines_data, colWidths=[255, 260])
    engines_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(engines_table)
    story.append(Spacer(1, 10))

    # ── 4. RESILIENCE, OFFLINE & PRIVACY ──
    story.append(Paragraph("4. Resilience, Offline Operation & Privacy Framework", h1_style))
    
    sec4_data = [
        [
            Paragraph("<b>Offline Store-and-Forward Spooling</b>", body_bold),
            Paragraph("Transit buses traverse underpasses, tunnels, and network blindspots. When cellular data drops, the edge pipeline automatically switches to local spool mode. Detections are serialized into SQLite with atomic transactions. Once connectivity returns, the NetworkManager executes batch uploads with exponential retry backoff, ensuring <b>zero data loss</b>.", body_style)
        ],
        [
            Paragraph("<b>Data Minimization by Design</b>", body_bold),
            Paragraph("Compliant with India's Digital Personal Data Protection (DPDP) Act. NovaFlow implements edge-side anonymization: faces of passengers/pedestrians and license plates of non-violating vehicles are blurred on-chip before any data leaves the vehicle.", body_style)
        ],
        [
            Paragraph("<b>Cryptographic Evidence Vault</b>", body_bold),
            Paragraph("For critical traffic incidents, 10-second compressed video clips are generated alongside a <b>SHA-256 cryptographic hash</b>, UTC timestamp, and bus hardware ID. This immutable record is stored in an audit log, guaranteeing an unbroken, tamper-evident chain of custody for legal and insurance admissibility.", body_style)
        ],
        [
            Paragraph("<b>Role-Based Access Control (RBAC)</b>", body_bold),
            Paragraph("Enforces the principle of least privilege across 4 municipal user roles: <code>ADMIN</code> (full governance), <code>TRAFFIC POLICE</code> (incidents, ANPR, congestion), <code>ROAD ENGINEER</code> (defects, potholes, work orders), and <code>ANALYST</code> (heatmaps, route delay modeling).", body_style)
        ]
    ]

    sec4_table = Table(sec4_data, colWidths=[150, 365])
    sec4_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(sec4_table)

    story.append(PageBreak())

    # ── 5. SPATIAL DEDUPLICATION & MULTI-BUS CONSENSUS ──
    story.append(Paragraph("5. Spatial Deduplication & Multi-Bus Consensus", h1_style))
    story.append(Paragraph(
        "If 20 buses traverse an arterial road with a pothole over 3 hours, displaying 20 duplicate pins would paralyze municipal dispatchers. NovaFlow uses an automated spatial-temporal consensus pipeline:",
        body_style
    ))

    dedup_box = Paragraph(
        "<b>Multi-Bus Consensus Pipeline:</b><br/>"
        "• <b>Haversine Distance Clustering:</b> Groups detections occurring within a 15-meter radial threshold.<br/>"
        "• <b>Confidence Scoring:</b> Initial detection (Bus 101) = 84% confidence. As Bus 205 and Bus 311 report the same defect coordinates, confidence is boosted to <b>98% (Multi-Bus Confirmed)</b>.<br/>"
        "• <b>Single GIS Pin:</b> Merges duplicate reports into a single consolidated hazard pin with observation counters, eliminating dispatcher clutter.",
        body_style
    )
    dedup_table = Table([[dedup_box]], colWidths=[515])
    dedup_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.5, C_BORDER),
    ]))
    story.append(dedup_table)
    story.append(Spacer(1, 10))

    # ── 6. CLOSED-LOOP AUTHORITY LIFECYCLE ──
    story.append(Paragraph("6. Closed-Loop Authority & Maintenance Lifecycle", h1_style))
    story.append(Paragraph(
        "NovaFlow bridges the gap between digital AI detection and physical road maintenance through a deterministic 5-stage lifecycle state machine:",
        body_style
    ))

    lifecycle_data = [
        [
            Paragraph("<b>1. UNVERIFIED</b>", body_bold),
            Paragraph("<b>2. CONFIRMED</b>", body_bold),
            Paragraph("<b>3. UNDER REPAIR</b>", body_bold),
            Paragraph("<b>4. RESOLVED</b>", body_bold),
        ],
        [
            Paragraph("Raw AI detection from single bus. Held in queue pending review or second bus consensus.", body_style),
            Paragraph("Verified by municipal operator or automatically validated by multi-bus consensus (>95%).", body_style),
            Paragraph("Dispatched to Public Works Dept. Work order generated (e.g., <code>WO-2026-8192</code>).", body_style),
            Paragraph("Road paved. Subsequent buses passing over the patch confirm smooth surface via AI vision.", body_style),
        ]
    ]
    lifecycle_table = Table(lifecycle_data, colWidths=[128, 128, 129, 130])
    lifecycle_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#fef3c7")),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor("#dbeafe")),
        ('BACKGROUND', (2, 0), (2, 0), colors.HexColor("#f3e8ff")),
        ('BACKGROUND', (3, 0), (3, 0), colors.HexColor("#d1fae5")),
        ('BOX', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(lifecycle_table)
    story.append(Spacer(1, 10))

    # ── 7. TECHNOLOGY STACK TABLE ──
    story.append(Paragraph("7. Technology Stack Summary", h1_style))
    tech_data = [
        [Paragraph("<b>Layer</b>", body_bold), Paragraph("<b>Components & Libraries</b>", body_bold), Paragraph("<b>Functionality</b>", body_bold)],
        [Paragraph("Edge Node", body_style), Paragraph("Python 3.11, OpenCV, TensorRT, SQLite, Paho-MQTT", body_style), Paragraph("Real-time video capture, inference, temporal tracking, offline spooling.", body_style)],
        [Paragraph("Backend API", body_style), Paragraph("FastAPI, Uvicorn, SQLModel / SQLAlchemy, Pydantic v2", body_style), Paragraph("High-throughput REST gateway, JWT auth, GeoJSON Feature collections.", body_style)],
        [Paragraph("Queue & Workers", body_style), Paragraph("Redis Streams + Background Event Processor Worker", body_style), Paragraph("Asynchronous ingestion buffer and spatial clustering pipeline.", body_style)],
        [Paragraph("Database", body_style), Paragraph("PostgreSQL 16 + PostGIS (with SQLite fallback)", body_style), Paragraph("Spatial querying, telemetry records, evidence logs, and audit trails.", body_style)],
        [Paragraph("Frontend UI", body_style), Paragraph("React 18, Vite 5, TypeScript, TailwindCSS, Leaflet", body_style), Paragraph("GIS Command Center, 12 map layers, clustering, work orders.", body_style)],
    ]
    tech_table = Table(tech_data, colWidths=[90, 200, 225])
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ('BOX', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(tech_table)
    story.append(Spacer(1, 10))

    # ── 8. MUNICIPAL ROI & SMART CITY VALUE ──
    story.append(Paragraph("8. Municipal Impact & Return on Investment (ROI)", h1_style))
    roi_data = [
        [
            Paragraph("<b>📉 85%+ Cost Reduction:</b> Replaces dedicated laser survey vans by turning everyday buses into inspection tools.", body_style),
            Paragraph("<b>⏱️ Proactive Maintenance:</b> Fixes road fissures and waterlogging before monsoons trigger major road sinkholes.", body_style),
        ],
        [
            Paragraph("<b>🚌 Transit Schedule Optimization:</b> Uses actual bus delay analytics (Route 12 baseline 38m vs 51m real) to resolve bottlenecks.", body_style),
            Paragraph("<b>⚖️ Court-Admissible Proof:</b> SHA-256 hashed video clips provide indisputable evidence for traffic safety disputes.", body_style),
        ]
    ]
    roi_table = Table(roi_data, colWidths=[255, 260])
    roi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#bfdbfe")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#bfdbfe")),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(roi_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated PDF: {filename}")

if __name__ == "__main__":
    output_path = os.path.join(os.getcwd(), "NovaFlow_Technical_Architecture.pdf")
    build_pdf(output_path)
