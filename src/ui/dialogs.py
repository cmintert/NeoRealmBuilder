import json
from typing import Dict, List, Tuple, Any, Set, Union, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTabWidget,
    QDialogButtonBox,
    QWidget,
    QCheckBox,
    QLabel,
    QHBoxLayout,
    QGroupBox,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QRadioButton,
    QTableWidgetItem,
    QHeaderView,
    QTableWidget,
    QScrollArea,
    QListWidget,
    QInputDialog,
    QButtonGroup,
)

from utils.crypto import SecurityUtility


class StyleSettingsDialog(QDialog):
    """
    Dialog for managing application styles and themes.
    Allows users to choose and preview different styles in real-time.
    """

    def __init__(self, config, app_instance, parent=None):
        super().__init__(parent)
        self.config = config
        self.app_instance = app_instance

        # Get the controller from app_instance.components
        if not hasattr(app_instance, "components") or not app_instance.components:
            raise RuntimeError("Application components not initialized")

        self.controller = app_instance.components.controller

        self.setWindowTitle("Style Settings")
        self.setModal(True)
        self.init_ui()

    def init_ui(self):
        """Initialize the dialog UI components."""
        layout = QVBoxLayout(self)

        # Create style selection group
        style_group = QGroupBox("Available Styles")
        style_layout = QVBoxLayout()

        # Get available styles from the registry
        self.style_buttons = {}
        current_style = self.controller.style_manager.current_style or "default"

        root_styles = {
            name: config
            for name, config in self.controller.style_manager.registry.styles.items()
            if not hasattr(config, "parent") or not config.parent
        }

        for (
            style_name,
            style_config,
        ) in root_styles.items():
            radio = QRadioButton(f"{style_name.title()} - {style_config.description}")
            radio.setObjectName(f"style_radio_{style_name}")
            radio.setChecked(style_name == current_style)
            radio.clicked.connect(
                lambda checked, name=style_name: self.on_style_selected(name)
            )
            self.style_buttons[style_name] = radio
            style_layout.addWidget(radio)

        style_group.setLayout(style_layout)
        layout.addWidget(style_group)

        # Add reload button
        reload_button = QPushButton("Reload Current Style")
        reload_button.setObjectName("reload_style_button")
        reload_button.clicked.connect(self.reload_current_style)
        layout.addWidget(reload_button)

        # Add dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def on_style_selected(self, style_name: str):
        """
        Handle style selection and apply it immediately.

        Args:
            style_name: The name of the selected style
        """
        try:
            self.controller.change_application_style(style_name)
        except Exception as e:
            QMessageBox.critical(
                self, "Style Error", f"Failed to apply style '{style_name}': {str(e)}"
            )

    def reload_current_style(self):
        """Reload the currently selected style."""
        try:
            self.controller.refresh_styles()
            QMessageBox.information(self, "Success", "Style reloaded successfully")
        except Exception as e:
            QMessageBox.critical(
                self, "Reload Error", f"Failed to reload style: {str(e)}"
            )

    def accept(self):
        """Handle dialog acceptance."""
        super().accept()


class SuggestionDialog(QDialog):
    def __init__(self, suggestions: Dict[str, Any], parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Suggested Node Information")
        self.setModal(True)
        self.suggestions = suggestions
        self.selected_suggestions: Dict[str, Any] = {
            "tags": [],
            "properties": {},
            "relationships": [],
        }
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Tabs for Tags, Properties, Relationships
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_tags_tab(), "Tags")
        self.tabs.addTab(self._create_properties_tab(), "Properties")
        self.tabs.addTab(self._create_relationships_tab(), "Relationships")

        # Action buttons
        button_box = button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(self.tabs)
        layout.addWidget(button_box)

    def _create_tags_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.tags_checkboxes: List[Tuple[QCheckBox, str]] = []
        for tag, confidence in self.suggestions.get("tags", []):
            checkbox = QCheckBox(f"{tag}")
            confidence_label = QLabel(f"Confidence: {confidence:.2f}%")
            h_layout = QHBoxLayout()
            h_layout.addWidget(checkbox)
            h_layout.addWidget(confidence_label)
            self.tags_checkboxes.append((checkbox, tag))
            layout.addLayout(h_layout)

        return widget

    def _create_properties_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.properties_checkboxes: List[Tuple[QCheckBox, str, QLineEdit]] = []
        for key, values in self.suggestions.get("properties", {}).items():
            group_box = QGroupBox(f"Property: {key}")
            v_layout = QVBoxLayout()
            for value, confidence in values:
                checkbox = QCheckBox("Value:")
                value_edit = QLineEdit(str(value))
                confidence_label = QLabel(f"Confidence: {confidence:.2f}%")
                h_layout = QHBoxLayout()
                h_layout.addWidget(checkbox)
                h_layout.addWidget(value_edit)
                h_layout.addWidget(confidence_label)
                v_layout.addLayout(h_layout)
                # Store the QLineEdit widget instead of its value
                self.properties_checkboxes.append((checkbox, key, value_edit))
            group_box.setLayout(v_layout)
            layout.addWidget(group_box)

        return widget

    def _create_relationships_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.relationships_checkboxes: List[
            Tuple[QCheckBox, str, str, str, Dict[str, Any]]
        ] = []
        for rel_type, target, direction, props, confidence in self.suggestions.get(
            "relationships", []
        ):
            checkbox = QCheckBox(f"{direction} {rel_type} -> {target}")
            confidence_label = QLabel(f"Confidence: {confidence:.2f}%")
            h_layout = QHBoxLayout()
            h_layout.addWidget(checkbox)
            h_layout.addWidget(confidence_label)
            self.relationships_checkboxes.append(
                (checkbox, rel_type, target, direction, props)
            )
            layout.addLayout(h_layout)

        return widget

    def accept(self) -> None:
        # Collect selected tags
        for checkbox, tag in self.tags_checkboxes:
            if checkbox.isChecked():
                self.selected_suggestions["tags"].append(tag)

        # Collect selected properties
        for checkbox, key, value_edit in self.properties_checkboxes:
            if checkbox.isChecked():
                # Get the current text from the QLineEdit when accepting
                self.selected_suggestions["properties"][key] = value_edit.text()

        # Collect selected relationships
        for (
            checkbox,
            rel_type,
            target,
            direction,
            props,
        ) in self.relationships_checkboxes:
            if checkbox.isChecked():
                self.selected_suggestions["relationships"].append(
                    (rel_type, target, direction, props)
                )

        super().accept()


class ConnectionSettingsDialog(QDialog):
    def __init__(self, config, app_instance, parent=None):
        super().__init__(parent)

        self.config = config
        self.app_instance = app_instance

        self.setWindowTitle("Manage Connection Settings")
        self.layout = QVBoxLayout()

        self.uri_label = QLabel("URI:", self)
        self.uri_input = QLineEdit(config.URI, self)
        self.uri_label.setBuddy(self.uri_input)
        self.layout.addWidget(self.uri_label)
        self.layout.addWidget(self.uri_input)

        self.username_label = QLabel("Username:", self)
        self.username_input = QLineEdit(config.USERNAME, self)
        self.username_label.setBuddy(self.username_input)
        self.layout.addWidget(self.username_label)
        self.layout.addWidget(self.username_input)

        self.password_label = QLabel("Password:", self)
        self.password_input = QLineEdit(config.PASSWORD, self)
        self.password_label.setBuddy(self.password_input)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout.addWidget(self.password_label)
        self.layout.addWidget(self.password_input)

        self.test_button = QPushButton("Establish Connection", self)
        self.test_button.setObjectName("establish_connect_button")

        self.save_button = QPushButton("Save", self)
        self.save_button.setObjectName("save_button")

        self.layout.addWidget(self.test_button)
        self.layout.addWidget(self.save_button)
        self.setLayout(self.layout)

        self.test_button.clicked.connect(self.establish_connection)
        self.save_button.clicked.connect(self.save_settings)

    def establish_connection(self):
        # Logic to test database connection
        try:
            # Attempt to initialize the database connection using the main application instance
            self.app_instance._initialize_database(self.config)
            QMessageBox.information(self, "Success", "Connection successful.")
        except RuntimeError as e:
            QMessageBox.critical(
                self, "Error", f"Failed to connect to the database: {e}"
            )

    def save_settings(self):
        # Retrieve the input values
        uri = self.uri_input.text()
        username = self.username_input.text()
        password = self.password_input.text()

        # Encrypt the password
        encryption_key = self.config.KEY
        security_utility = SecurityUtility(encryption_key)
        encrypted_password = security_utility.encrypt(password)

        # Prepare the new settings dictionary
        new_settings = {
            "URI": uri,
            "USERNAME": username,
            "PASSWORD": encrypted_password,
        }

        # Load existing settings from the JSON file
        try:
            with open("src/config/database.json", "r") as config_file:
                existing_settings = json.load(config_file)
        except FileNotFoundError:
            existing_settings = {}

        # Update the existing settings with the new settings
        existing_settings |= new_settings

        # Save the updated settings back to the JSON file
        with open("src/config/database.json", "w") as config_file:
            json.dump(existing_settings, config_file, indent=4)

        QMessageBox.information(self, "Success", "Settings saved successfully.")


class FastInjectDialog(QDialog):
    """Dialog for previewing Fast Inject template contents with selective application."""

    def __init__(self, template: Dict[str, Any], parent=None) -> None:
        super().__init__(parent)
        self.template = template
        self.setWindowTitle(f"Fast Inject Preview - {template['name']}")
        self.setModal(True)
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)

        # Track selected items
        self.selected_labels: Set[str] = set(template["content"]["labels"])
        self.selected_tags: Set[str] = set(template["content"]["tags"])
        self.selected_properties: Set[str] = set(
            template["content"]["properties"].keys()
        )
        self.modified_property_values: Dict[str, str] = {}
        self.property_checkboxes: Dict[str, QCheckBox] = {}

        self.init_ui()

    def init_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        # Header section with template info
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setSpacing(5)

        name_label = QLabel(f"<b>{self.template['name']}</b>")
        name_label.setStyleSheet("font-size: 14px;")

        desc_label = QLabel(self.template["description"])
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666;")

        header_layout.addWidget(name_label)
        header_layout.addWidget(desc_label)
        main_layout.addWidget(header_widget)

        # Create horizontal layout for labels and tags
        top_section = QWidget()
        top_layout = QHBoxLayout(top_section)
        top_layout.setSpacing(10)

        # Labels section (left side)
        labels_group = self._create_labels_group()
        labels_group.setMaximumHeight(150)
        top_layout.addWidget(labels_group)

        # Tags section (right side)
        tags_group = self._create_tags_group()
        tags_group.setMaximumHeight(150)
        top_layout.addWidget(tags_group)

        main_layout.addWidget(top_section)

        # Properties section (expanded)
        props_group = self._create_properties_group()
        main_layout.addWidget(props_group, stretch=1)  # Give properties more space

        # Note about existing properties
        note_label = QLabel("<i>Note: Existing properties will not be overwritten</i>")
        note_label.setStyleSheet("color: #666; padding: 5px;")
        main_layout.addWidget(note_label)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def _create_labels_group(self) -> QGroupBox:
        """Create compact labels group."""
        group = QGroupBox("Labels")
        layout = QVBoxLayout()
        layout.setSpacing(2)

        # Select All checkbox
        select_all = QCheckBox("Select All")
        select_all.setChecked(True)
        layout.addWidget(select_all)

        # Create scrollable area for labels
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        labels_widget = QWidget()
        labels_layout = QVBoxLayout(labels_widget)
        labels_layout.setSpacing(1)
        labels_layout.setContentsMargins(0, 0, 0, 0)

        # Individual label checkboxes
        label_checkboxes: List[QCheckBox] = []
        for label in self.template["content"]["labels"]:
            checkbox = QCheckBox(label)
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(
                lambda state, l=label: self._update_label_selection(l, state)
            )
            labels_layout.addWidget(checkbox)
            label_checkboxes.append(checkbox)

        labels_layout.addStretch()
        scroll.setWidget(labels_widget)

        # Connect select all functionality
        select_all.stateChanged.connect(
            lambda state: self._toggle_all_labels(state, label_checkboxes)
        )

        layout.addWidget(scroll)
        group.setLayout(layout)
        return group

    def _create_tags_group(self) -> QGroupBox:
        """Create compact tags group."""
        group = QGroupBox("Tags")
        layout = QVBoxLayout()
        layout.setSpacing(2)

        # Select All checkbox
        select_all = QCheckBox("Select All")
        select_all.setChecked(True)
        layout.addWidget(select_all)

        # Create scrollable area for tags
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        tags_widget = QWidget()
        tags_layout = QVBoxLayout(tags_widget)
        tags_layout.setSpacing(1)
        tags_layout.setContentsMargins(0, 0, 0, 0)

        # Individual tag checkboxes
        tag_checkboxes: List[QCheckBox] = []
        for tag in self.template["content"]["tags"]:
            checkbox = QCheckBox(tag)
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(
                lambda state, t=tag: self._update_tag_selection(t, state)
            )
            tags_layout.addWidget(checkbox)
            tag_checkboxes.append(checkbox)

        tags_layout.addStretch()
        scroll.setWidget(tags_widget)

        # Connect select all functionality
        select_all.stateChanged.connect(
            lambda state: self._toggle_all_tags(state, tag_checkboxes)
        )

        layout.addWidget(scroll)
        group.setLayout(layout)
        return group

    def _create_properties_group(self) -> QGroupBox:
        """Create expanded properties group with enhanced table."""
        group = QGroupBox("Properties")
        layout = QVBoxLayout()
        layout.setSpacing(5)

        # Header controls
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 5)

        select_all = QCheckBox("Select All Properties")
        select_all.setChecked(True)
        header_layout.addWidget(select_all)

        filter_input = QLineEdit()
        filter_input.setPlaceholderText("Filter properties...")
        filter_input.textChanged.connect(self._filter_properties)
        header_layout.addWidget(filter_input)

        layout.addWidget(header_widget)

        # Create table
        props = self.template["content"]["properties"]
        self.props_table = QTableWidget(len(props), 3)
        self.props_table.setHorizontalHeaderLabels(["Select", "Property", "Value"])

        self.props_table.verticalHeader().setVisible(False)
        header = self.props_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.props_table.setColumnWidth(0, 50)
        self.props_table.setColumnWidth(1, 300)

        # Track value widgets for properties
        self.property_value_widgets: Dict[str, PropertyValueWidget] = {}

        for i, (key, value) in enumerate(props.items()):
            # Checkbox column
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(
                lambda state, k=key: self._update_property_selection(k, state)
            )
            self.property_checkboxes[key] = checkbox
            self.props_table.setCellWidget(i, 0, checkbox)

            # Property name column
            name_item = QTableWidgetItem(key)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.props_table.setItem(i, 1, name_item)

            # Value column with PropertyValueWidget
            value_widget = PropertyValueWidget(value)
            self.property_value_widgets[key] = value_widget
            self.props_table.setCellWidget(i, 2, value_widget)

        # Connect select all functionality
        select_all.stateChanged.connect(
            lambda state: self._toggle_all_properties(state)
        )

        layout.addWidget(self.props_table)
        group.setLayout(layout)
        return group

    def _filter_properties(self, text: str) -> None:
        """Filter properties table based on search text."""
        search_text = text.lower()
        for row in range(self.props_table.rowCount()):
            property_name = self.props_table.item(row, 1).text().lower()
            property_value = self.props_table.item(row, 2).text().lower()
            matches = search_text in property_name or search_text in property_value
            self.props_table.setRowHidden(row, not matches)

    def _on_property_value_changed(self, item: QTableWidgetItem) -> None:
        """Handle property value changes in the table."""
        if item.column() == 2:  # Value column
            prop_name = self.props_table.item(item.row(), 1).text()
            self.modified_property_values[prop_name] = item.text()

    def get_selected_properties_with_values(self) -> Dict[str, str]:
        """Get selected properties with their potentially modified values."""
        result = {}
        for prop_name in self.selected_properties:
            if widget := self.property_value_widgets.get(prop_name):
                result[prop_name] = widget.get_value()
        return result

    def _update_label_selection(self, label: str, state: int) -> None:
        """Update the selected labels set based on checkbox state."""
        if state == Qt.CheckState.Checked.value:
            self.selected_labels.add(label)
        else:
            self.selected_labels.discard(label)

    def _update_tag_selection(self, tag: str, state: int) -> None:
        """Update the selected tags set based on checkbox state."""
        if state == Qt.CheckState.Checked.value:
            self.selected_tags.add(tag)
        else:
            self.selected_tags.discard(tag)

    def _update_property_selection(self, prop: str, state: int) -> None:
        """Update the selected properties set based on checkbox state."""
        if state == Qt.CheckState.Checked.value:
            self.selected_properties.add(prop)
        else:
            self.selected_properties.discard(prop)

    def _toggle_all_labels(self, state: int, checkboxes: List[QCheckBox]) -> None:
        """Toggle all label checkboxes."""
        for checkbox in checkboxes:
            checkbox.setChecked(state == Qt.CheckState.Checked.value)

    def _toggle_all_tags(self, state: int, checkboxes: List[QCheckBox]) -> None:
        """Toggle all tag checkboxes."""
        for checkbox in checkboxes:
            checkbox.setChecked(state == Qt.CheckState.Checked.value)

    def _toggle_all_properties(self, state: int) -> None:
        """Toggle all property checkboxes."""
        checked = state == Qt.CheckState.Checked.value
        for checkbox in self.property_checkboxes.values():
            checkbox.setChecked(checked)


class ValueEditorDialog(QDialog):
    """Dialog for editing a list of predefined values."""

    def __init__(self, current_values: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Property Values")
        self.setModal(True)
        self.values = current_values.copy()
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the dialog UI."""
        layout = QVBoxLayout(self)

        # Create list widget for values
        self.list_widget = QListWidget()
        for value in self.values:
            self.list_widget.addItem(value)
        layout.addWidget(self.list_widget)

        # Buttons for manipulating values
        button_layout = QHBoxLayout()

        add_button = QPushButton("Add Value")
        add_button.clicked.connect(self.add_value)
        button_layout.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self.edit_value)
        button_layout.addWidget(edit_button)

        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self.remove_value)
        button_layout.addWidget(remove_button)

        layout.addLayout(button_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def add_value(self) -> None:
        """Add a new value to the list."""
        text, ok = QInputDialog.getText(self, "Add Value", "Enter new value:")
        if ok and text:
            self.list_widget.addItem(text)

    def edit_value(self) -> None:
        """Edit the currently selected value."""
        if current := self.list_widget.currentItem():
            text, ok = QInputDialog.getText(
                self, "Edit Value", "Edit value:", text=current.text()
            )
            if ok and text:
                current.setText(text)

    def remove_value(self) -> None:
        """Remove the currently selected value."""
        if current := self.list_widget.currentRow():
            self.list_widget.takeItem(current)

    def get_values(self) -> List[str]:
        """Get the current list of values."""
        return [
            self.list_widget.item(i).text() for i in range(self.list_widget.count())
        ]


class PropertyValueWidget(QWidget):
    """Widget for displaying property values either as line edit or radio buttons."""

    def __init__(self, value: Union[str, List[str]], parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)

        # Parse values
        if isinstance(value, str) and "," in value:
            self.values = [v.strip() for v in value.split(",")]
        elif isinstance(value, list):
            self.values = value
        else:
            self.values = [str(value)]

        # Create container for input widgets
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)

        # Create value input widget
        self.value_container = QWidget()
        self.value_layout = QHBoxLayout(self.value_container)
        self.value_layout.setContentsMargins(0, 0, 0, 0)
        self.value_layout.setSpacing(2)

        self.setup_input_widget(input_layout)
        self.layout.addWidget(input_container)

    def setup_input_widget(self, input_layout: QHBoxLayout) -> None:
        """Setup the appropriate input widget based on number of values."""
        if len(self.values) > 1:
            # Create radio buttons for multiple values
            self.button_group = QButtonGroup()
            for i, val in enumerate(self.values):
                radio = QRadioButton(str(val))
                self.button_group.addButton(radio, i)
                self.value_layout.addWidget(radio)
                if i == 0:  # Select first option by default
                    radio.setChecked(True)

            # Add edit button
            edit_button = QPushButton("✏️")
            edit_button.setMaximumWidth(30)
            edit_button.setMinimumWidth(30)
            edit_button.clicked.connect(self.edit_values)
            input_layout.addWidget(self.value_container)
            input_layout.addWidget(edit_button)
        else:
            # Use line edit for single value
            self.line_edit = QLineEdit(str(self.values[0]))
            self.value_layout.addWidget(self.line_edit)
            input_layout.addWidget(self.value_container)

    def edit_values(self) -> None:
        """Open dialog to edit selectable values."""
        current_values = [b.text() for b in self.button_group.buttons()]
        dialog = ValueEditorDialog(current_values, self)

        if dialog.exec():
            new_values = dialog.get_values()
            if new_values:
                # Store current selection
                current_value = self.get_value()

                # Clear existing radio buttons
                for button in self.button_group.buttons():
                    self.button_group.removeButton(button)
                    self.value_layout.removeWidget(button)
                    button.deleteLater()

                # Create new radio buttons
                self.values = new_values
                for i, val in enumerate(new_values):
                    radio = QRadioButton(str(val))
                    self.button_group.addButton(radio, i)
                    self.value_layout.addWidget(radio)
                    # Try to maintain the previous selection
                    if val == current_value:
                        radio.setChecked(True)

                # Select first option if previous value no longer exists
                if not self.button_group.checkedButton():
                    first = self.button_group.button(0)
                    if first:
                        first.setChecked(True)

    def get_value(self) -> str:
        """Get the currently selected/entered value."""
        if hasattr(self, "button_group"):
            selected = self.button_group.checkedButton()
            return selected.text() if selected else ""
        else:
            return self.line_edit.text()


class PinPlacementDialog(QDialog):
    """Dialog for configuring a new map pin."""

    def __init__(self, x: int, y: int, parent=None, controller=None):
        """Initialize the dialog.

        Args:
            x: X coordinate of pin placement
            y: Y coordinate of pin placement
            parent: Parent widget
        """
        super().__init__(parent)
        self.x = x
        self.y = y
        self.controller = controller
        self.target_node: Optional[str] = None
        self.setup_ui()

    def setup_ui(self) -> None:
        """Initialize dialog UI components."""
        self.setWindowTitle("Place Pin")
        layout = QVBoxLayout(self)

        # Coordinates display
        coords_layout = QHBoxLayout()
        coords_layout.addWidget(QLabel(f"X: {self.x}"))
        coords_layout.addWidget(QLabel(f"Y: {self.y}"))
        layout.addLayout(coords_layout)

        # Target node input
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("Target Node:"))
        self.target_input = QLineEdit()
        if self.controller:
            self.controller.auto_completion_service.initialize_target_completer(
                self.target_input
            )
        target_layout.addWidget(self.target_input)
        layout.addLayout(target_layout)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setMinimumWidth(300)

    def get_target_node(self) -> Optional[str]:
        """Get the entered target node name."""
        return self.target_input.text().strip() or None
