"""Dialog components for POI selection and distance measurement."""

from typing import List, Optional, Tuple

import structlog
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QDialogButtonBox,
    QComboBox,
    QPushButton,
    QMessageBox,
)

from services.autocompletion_service import AutoCompletionService

logger = structlog.get_logger()


class POISelectionDialog(QDialog):
    """Dialog for selecting or creating a POI node."""

    def __init__(
        self,
        parent=None,
        existing_nodes: list = None,
        auto_completion_service: Optional["AutoCompletionService"] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Add Point of Interest")
        self.setModal(True)
        self.setMinimumWidth(400)

        self.existing_nodes = existing_nodes or []
        self.auto_completion_service = auto_completion_service

        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Instructions
        instructions = QLabel(
            "Enter a node name. You can select an existing node or create a new one."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Node name input
        name_layout = QHBoxLayout()
        name_label = QLabel("Node name:")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter node name...")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)

        # Setup auto-completion if available
        if self.auto_completion_service:
            self.auto_completion_service.initialize_node_completer(self.name_input)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._validate_and_accept)
        button_box.rejected.connect(self.reject)

        # Add widgets to layout
        layout.addLayout(name_layout)
        layout.addWidget(button_box)

    def _validate_and_accept(self) -> None:
        """Validate input before accepting."""
        name = self.get_node_name()
        if not name:
            QMessageBox.warning(self, "Invalid Input", "Please enter a node name.")
            return

        self.accept()

    def get_node_name(self) -> str:
        """Get the entered node name."""
        return self.name_input.text().strip()


class DistanceDialog(QDialog):
    """Dialog for measuring distance between POIs."""

    def __init__(self, poi_names: List[str], calculate_callback: callable, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Measure Distance")
        self.setModal(True)
        self.setMinimumWidth(300)

        self.poi_names = poi_names
        self.calculate_callback = calculate_callback

        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # From POI selector
        from_layout = QHBoxLayout()
        from_label = QLabel("From:")
        self.from_combo = QComboBox()
        self.from_combo.addItems(self.poi_names)
        from_layout.addWidget(from_label)
        from_layout.addWidget(self.from_combo)

        # To POI selector
        to_layout = QHBoxLayout()
        to_label = QLabel("To:")
        self.to_combo = QComboBox()
        self.to_combo.addItems(self.poi_names)
        to_layout.addWidget(to_label)
        to_layout.addWidget(self.to_combo)

        # Result label
        self.result_label = QLabel()
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setStyleSheet(
            "QLabel { padding: 10px; background-color: #f0f0f0; }"
        )

        # Calculate button
        self.calc_button = QPushButton("Calculate Distance")
        self.calc_button.clicked.connect(self._calculate_distance)

        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)

        # Add all widgets to layout
        layout.addLayout(from_layout)
        layout.addLayout(to_layout)
        layout.addWidget(self.calc_button)
        layout.addWidget(self.result_label)
        layout.addWidget(button_box)

    def _calculate_distance(self) -> None:
        """Calculate and display distance between selected POIs."""
        from_poi = self.from_combo.currentText()
        to_poi = self.to_combo.currentText()

        if from_poi == to_poi:
            self.result_label.setText("Please select different POIs")
            return

        try:
            distance = self.calculate_callback(from_poi, to_poi)
            if distance is not None:
                self.result_label.setText(f"Distance: {distance:.1f}")
            else:
                self.result_label.setText("Could not calculate distance")

        except Exception as e:
            self.result_label.setText(f"Error: {str(e)}")

    def get_selected_pois(self) -> Tuple[str, str]:
        """Get the selected POI names."""
        return (self.from_combo.currentText(), self.to_combo.currentText())
