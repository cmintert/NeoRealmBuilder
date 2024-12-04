from typing import Optional, Dict, Any

import structlog
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QBrush
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QDoubleSpinBox,
    QComboBox,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsItem,
    QMessageBox,
)

logger = structlog.get_logger()


class MapPOIItem(QGraphicsItem):
    """Graphics item representing a POI on the map."""

    def __init__(
        self,
        x: float,
        y: float,
        name: str,
        icon: Optional[str] = None,
        parent: Optional[QGraphicsItem] = None,
    ):
        super().__init__(parent)
        self.name = name
        self.icon = icon
        self.setPos(x, y)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)

    def boundingRect(self) -> QRectF:
        """Define the clickable area of the POI."""
        return QRectF(-10, -10, 20, 20)

    def paint(
        self, painter: QPainter, option: Any, widget: Optional[QWidget] = None
    ) -> None:
        """Draw the POI marker."""
        if self.isSelected():
            painter.setPen(QPen(QColor("#83A00E"), 2))  # Using your highlight color
            painter.setBrush(QBrush(QColor("#83A00E")))
        else:
            painter.setPen(QPen(QColor("#2196F3"), 2))  # Using your standard color
            painter.setBrush(QBrush(QColor("#2196F3")))

        # Draw marker
        painter.drawEllipse(-5, -5, 10, 10)

        # Draw label
        painter.setPen(QPen(Qt.GlobalColor.white))
        painter.drawText(10, 5, self.name)


class MapView(QGraphicsView):
    """Custom graphics view for map display and interaction."""

    poi_moved = pyqtSignal(str, float, float)  # Emits when POI is moved

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)

        # Setup scene
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self._scale = 1.0
        self._is_placing_poi = False
        self._current_poi_name = None

    def wheelEvent(self, event) -> None:
        """Handle mouse wheel for zooming."""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            factor = 1.1 if event.angleDelta().y() > 0 else 0.9
            self.scale(factor, factor)
            event.accept()
        else:
            super().wheelEvent(event)


class MapTab(QWidget):
    """Tab widget for map visualization and control."""

    poi_selected = pyqtSignal(str)  # Emits selected POI name
    poi_moved = pyqtSignal(str, float, float)  # Emits when POI is moved

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("mapTab")
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Controls section
        controls = QHBoxLayout()

        # Scale controls
        scale_layout = QHBoxLayout()
        scale_label = QLabel("Scale:")
        self.scale_value = QDoubleSpinBox()
        self.scale_value.setRange(0.1, 10000.0)
        self.scale_value.setValue(1.0)
        self.scale_value.setDecimals(1)

        self.scale_unit = QComboBox()
        self.scale_unit.addItems(["m", "km", "mi", "ft"])

        scale_layout.addWidget(scale_label)
        scale_layout.addWidget(self.scale_value)
        scale_layout.addWidget(self.scale_unit)

        # Add POI button
        self.add_poi_btn = QPushButton("➕ Add POI")
        self.add_poi_btn.setObjectName("addPoiButton")
        self.add_poi_btn.setFixedWidth(100)
        self.add_poi_btn.setMinimumHeight(30)

        # Measure button
        self.measure_btn = QPushButton("📏 Measure")
        self.measure_btn.setObjectName("measureButton")
        self.measure_btn.setFixedWidth(100)
        self.measure_btn.setMinimumHeight(30)

        # Add all controls
        controls.addLayout(scale_layout)
        controls.addStretch()
        controls.addWidget(self.add_poi_btn)
        controls.addWidget(self.measure_btn)

        layout.addLayout(controls)

        # Map view
        self.map_view = MapView()
        layout.addWidget(self.map_view)

    def set_map(self, image_path: str, metadata: Dict[str, Any]) -> None:
        """Set the map image and metadata."""
        try:
            # Load and set image
            image = QImage(image_path)
            if image.isNull():
                raise ValueError("Failed to load map image")

            pixmap = QPixmap.fromImage(image)
            self.map_view.scene.clear()
            self.map_view.scene.addPixmap(pixmap)

            # Set scale controls
            self.scale_value.setValue(metadata.get("scale", 1.0))
            unit = metadata.get("unit", "m")
            index = self.scale_unit.findText(unit)
            if index >= 0:
                self.scale_unit.setCurrentIndex(index)

            # Fit view to image
            self.map_view.fitInView(
                self.map_view.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio
            )

            logger.info(
                "Map loaded in view",
                image_path=image_path,
                width=image.width(),
                height=image.height(),
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load map: {str(e)}")

    def clear_map(self) -> None:
        """Clear the map view."""
        self.map_view.scene.clear()
        self.scale_value.setValue(1.0)
        self.scale_unit.setCurrentIndex(0)

    def add_poi(
        self, name: str, x: float, y: float, icon: Optional[str] = None
    ) -> None:
        """Add a POI to the map."""
        poi = MapPOIItem(x, y, name, icon)
        self.map_view.scene.addItem(poi)

    def get_scale_settings(self) -> Dict[str, Any]:
        """Get current scale settings."""
        return {
            "scale": self.scale_value.value(),
            "unit": self.scale_unit.currentText(),
        }
