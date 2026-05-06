# ui/manual_lookup.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QStyledItemDelegate
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QPainter, QColor
from ui.styles import COLORS, FONTS

class SearchResultDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 48)

    def paint(self, painter, option, index):
        data = index.data(Qt.ItemDataRole.UserRole)
        rect = option.rect
        
        painter.save()
        if option.state & QStyledItemDelegate.State_Selected:
            painter.fillRect(rect, QColor(COLORS["bg_selected"]))
        
        # Draw reference
        painter.setPen(QColor(COLORS["accent"]))
        painter.setFont(FONTS["family"], FONTS["size_sm"], weight=700)
        painter.drawText(rect.adjusted(8, 4, 0, 0), Qt.AlignmentFlag.AlignTop, data["reference"])
        
        # Draw snippet
        painter.setPen(QColor(COLORS["text_secondary"]))
        painter.setFont(FONTS["family"], FONTS["size_xs"])
        painter.drawText(rect.adjusted(8, 20, -8, 0), Qt.AlignmentFlag.AlignTop, data["verse"][:100] + "...")
        painter.restore()

class ManualLookup(QWidget):
    send_to_display = pyqtSignal(dict)
    
    def __init__(self, bible_db, parent=None):
        super().__init__(parent)
        self._db = bible_db
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._run_search)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("🔍 Search scriptures... e.g. 'John 3:16' or 'love'")
        self._search_input.setFixedHeight(40)
        self._search_input.textChanged.connect(lambda: self._debounce.start(120))
        layout.addWidget(self._search_input)
        
        self._results_list = QListWidget()
        self._results_list.setItemDelegate(SearchResultDelegate())
        self._results_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._results_list)
        
    def _run_search(self) -> None:
        query = self._search_input.text().strip()
        if len(query) < 2:
            self._results_list.clear()
            return
        
        if len(query) <= 3:
            results = self._db.search_like(query, limit=100)
        else:
            results = self._db.search_fts(query, limit=200)
        
        self._results_list.clear()
        for r in results:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, r)
            self._results_list.addItem(item)
    
    def _on_item_double_clicked(self, item) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        self.send_to_display.emit({
            "verse_text": data["verse"],
            "reference": data["reference"],
            "translation": "KJV",
        })
