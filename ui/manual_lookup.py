# ui/manual_lookup.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QStyledItemDelegate
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QPainter, QColor
from ui.styles import COLORS, FONTS
import numpy as np

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
        text = data.get("verse", "")[:100] + "..."
        painter.drawText(rect.adjusted(8, 20, -8, 0), Qt.AlignmentFlag.AlignTop, text)
        painter.restore()

class ManualLookup(QWidget):
    send_to_display = pyqtSignal(dict)
    
    def __init__(self, bible_db, parent=None):
        super().__init__(parent)
        self._db = bible_db
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._run_search)
        
        self._model = None
        self._embeddings = None
        self._refs = None
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("🔍 Search scriptures (FTS5 active)...")
        self._search_input.setFixedHeight(40)
        self._search_input.textChanged.connect(lambda: self._debounce.start(120))
        layout.addWidget(self._search_input)
        
        self._results_list = QListWidget()
        self._results_list.setItemDelegate(SearchResultDelegate())
        self._results_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._results_list)
        
    def enable_semantic_mode(self, model, matrix, refs):
        """Enables semantic search capabilities once AI model is loaded."""
        self._model = model
        self._embeddings = matrix
        self._refs = refs
        self._search_input.setPlaceholderText("🔍 Search scriptures (Semantic AI active)...")

    def _run_search(self) -> None:
        query = self._search_input.text().strip()
        if len(query) < 2:
            self._results_list.clear()
            return
        
        # Step 1: Always try Fast SQL Search first
        if len(query) <= 3:
            results = self._db.search_like(query, limit=50)
        else:
            results = self._db.search_fts(query, limit=100)
            
        # Step 2: If AI is ready and results are sparse, add semantic matches
        if self._model and len(results) < 5:
            # We don't want to block the UI, but a single encode is usually < 50ms
            query_emb = self._model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
            scores = np.dot(self._embeddings, query_emb[0])
            top_indices = np.argsort(scores)[-10:][::-1]
            
            seen_refs = {r["reference"] for r in results}
            for idx in top_indices:
                ref = self._refs[idx]
                if ref not in seen_refs and scores[idx] > 0.4:
                    text = self._db.lookup_verse(*self._parse_ref(ref))
                    results.append({"reference": ref, "verse": text, "confidence": float(scores[idx]), "method": "semantic"})

        self._results_list.clear()
        for r in results:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, r)
            self._results_list.addItem(item)
    
    def _parse_ref(self, ref: str):
        # Helper to convert "Book Chapter:Verse" to (Book, Chapter, Verse)
        # Note: In our DB Book is INT. We should map Book Name to INT.
        # For simplicity in lookup_verse which we updated to take (book_num, chap, verse)
        # but the refs we stored in cache are strings like "Genesis 1:1".
        # We need a name-to-num map.
        from data.book_names import BIBLE_BOOKS
        parts = ref.replace(":", " ").split()
        # This is a bit brittle, but handles "1 John 1:1"
        book_name = " ".join(parts[:-2])
        chap = int(parts[-2])
        verse = int(parts[-1])
        
        # Map name to index (1-based)
        # Assuming BIBLE_BOOKS keys are ordered correctly
        book_list = list(BIBLE_BOOKS.keys())
        try:
            book_num = book_list.index(book_name) + 1
        except ValueError:
            book_num = 1
            
        return book_num, chap, verse

    def _on_item_double_clicked(self, item) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        self.send_to_display.emit({
            "verse_text": data["verse"],
            "reference": data["reference"],
            "translation": "KJV",
        })
