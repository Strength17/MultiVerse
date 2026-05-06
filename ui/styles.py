# ui/styles.py

from PyQt6.QtWidgets import QApplication

COLORS = {
    "bg_window":   "#0D0D0D",
    "bg_panel":    "#161616",
    "bg_card":     "#1F1F1F",
    "bg_elevated": "#282828",
    "bg_hover":    "#2E2E2E",
    "bg_selected": "#1A3A5C",
    "accent":      "#4A9EFF",
    "accent_dark": "#1A6ECC",
    "success":     "#22C55E",
    "warning":     "#F59E0B",
    "danger":      "#EF4444",
    "muted":       "#4B5563",
    "text_primary":   "#F9FAFB",
    "text_secondary": "#9CA3AF",
    "text_muted":     "#6B7280",
    "text_verse":     "#FFFFFF",
    "text_ref":       "#B0C4DE",
    "text_trans":     "#7B9BB8",
    "border":       "#2D2D2D",
    "border_focus": "#4A9EFF",
    "meter_low":  "#22C55E",
    "meter_mid":  "#F59E0B",
    "meter_high": "#EF4444",
    "meter_bg":   "#1A1A1A",
}

FONTS = {
    "family": "Segoe UI",
    "family_mono": "Consolas",
    "size_xs":   10,
    "size_sm":   11,
    "size_md":   13,
    "size_lg":   15,
    "size_xl":   20,
    "size_verse": 42,
    "size_ref":   24,
    "size_trans": 16,
}

RADIUS = {"sm": 4, "md": 8, "lg": 12, "xl": 16}

def get_stylesheet() -> str:
    return f"""
        QMainWindow, QWidget#central {{ background-color: {COLORS['bg_window']}; }}
        QWidget#panel_left, #panel_center, #panel_right {{ 
            background-color: {COLORS['bg_panel']}; 
            border-right: 1px solid {COLORS['border']};
        }}
        QWidget#card {{ 
            background-color: {COLORS['bg_card']}; 
            border-radius: {RADIUS['md']}px; 
        }}
        QLineEdit {{ 
            background-color: {COLORS['bg_card']}; 
            color: {COLORS['text_primary']}; 
            border: 1px solid {COLORS['border']}; 
            padding: 8px; 
            border-radius: {RADIUS['sm']}px; 
        }}
        QLineEdit:focus {{ border: 1px solid {COLORS['border_focus']}; }}
        QPushButton#btn_primary {{ 
            background-color: {COLORS['accent']}; 
            color: white; 
            border-radius: {RADIUS['sm']}px; 
            font-weight: bold; 
            padding: 8px 16px; 
        }}
        QPushButton#btn_primary:hover {{ background-color: {COLORS['accent_dark']}; }}
        QPushButton#btn_success {{ background-color: {COLORS['success']}; }}
        QPushButton#btn_danger {{ background-color: {COLORS['danger']}; }}
        QPushButton#btn_muted {{ background-color: {COLORS['bg_elevated']}; color: {COLORS['text_secondary']}; }}
        QListWidget {{ background-color: {COLORS['bg_card']}; border: none; outline: none; }}
        QListWidget::item {{ padding: 8px 12px; color: {COLORS['text_primary']}; }}
        QListWidget::item:selected {{ background-color: {COLORS['bg_selected']}; color: white; }}
        QListWidget::item:hover {{ background-color: {COLORS['bg_hover']}; }}
        QScrollBar:vertical {{ background-color: {COLORS['bg_card']}; width: 6px; }}
        QScrollBar::handle:vertical {{ background-color: {COLORS['muted']}; border-radius: 3px; }}
        QLabel#label_section {{ color: {COLORS['text_secondary']}; font-size: {FONTS['size_sm']}px; text-transform: uppercase; }}
        QLabel#label_verse {{ color: {COLORS['text_primary']}; font-size: {FONTS['size_lg']}px; font-weight: bold; }}
        QLabel#label_ref {{ color: {COLORS['accent']}; font-size: {FONTS['size_md']}px; }}
        QSplitter::handle {{ background-color: {COLORS['border']}; height: 1px; }}
    """
