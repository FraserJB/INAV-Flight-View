# Copyright (C) 2026 Fraser Boyd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QHeaderView, QCheckBox, QWidget, QLineEdit, QLabel, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)
    
    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(checked)
        self.checkbox.stateChanged.connect(lambda s: self.toggled.emit(s == 2))
        layout.addWidget(self.checkbox)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def isChecked(self):
        return self.checkbox.isChecked()

    def setChecked(self, checked):
        self.checkbox.setChecked(checked)

class ParameterSelector(QDialog):
    config_changed = pyqtSignal(list)
    
    def __init__(self, current_config, all_available_params, parent=None, available_cols=None, default_order=None):
        super().__init__(parent)
        self.setWindowTitle("Select Parameters")
        self.resize(800, 600)
        
        # current_config: list of dicts [{'param': 'pos_z', 'plot': True, ...}]
        # all_available_params: dict of param -> {'name': ..., 'desc': ..., 'unit': ..., 'color': ...}
        self.config = current_config
        self.all_params = all_available_params
        self.available_cols = available_cols # Set of column names actually in the log
        self.default_order = default_order # List of param IDs in default order
        
        self.init_ui()
        self.apply_dark_theme()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter by name, parameter or description...")
        self.search_input.textChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.search_input)
        layout.addLayout(filter_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Name", "Parameter", "Description", "Plot", "Trail"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        self.table.setSortingEnabled(True)
        self.table.setWordWrap(True)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
        layout.addWidget(self.table)
        
        # Move Buttons
        btn_layout = QHBoxLayout()
        self.btn_up = QPushButton("Move Up ^")
        self.btn_down = QPushButton("Move Down v")
        self.btn_up.clicked.connect(self.move_up)
        self.btn_down.clicked.connect(self.move_down)
        
        btn_layout.addWidget(self.btn_up)
        btn_layout.addWidget(self.btn_down)
        
        self.btn_reset = QPushButton("Reset")
        self.btn_reset.clicked.connect(self.reset_order)
        btn_layout.addWidget(self.btn_reset)
        
        btn_layout.addStretch()
        
        self.btn_ok = QPushButton("Apply")
        self.btn_ok.clicked.connect(self.apply_and_close)
        btn_layout.addWidget(self.btn_ok)
        
        layout.addLayout(btn_layout)
        
        self.is_sorted = False
        self.populate_table()

    def populate_table(self):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.config))
        for i, item in enumerate(self.config):
            p_id = item['param']
            p_info = self.all_params.get(p_id, {'name': p_id, 'desc': 'No description', 'unit': '', 'color': '#ffffff'})
            
            # Name
            name_text = p_info['name']
            is_missing = self.available_cols is not None and p_id not in self.available_cols
            if is_missing:
                name_text += " [Not in Log]"
                
            name_item = QTableWidgetItem(name_text)
            name_item.setToolTip(p_info['name'])
            if is_missing:
                name_item.setForeground(QColor("#ff5555"))
            self.table.setItem(i, 0, name_item)
            
            # Parameter
            param_item = QTableWidgetItem(p_id)
            param_item.setToolTip(p_id)
            if is_missing:
                param_item.setForeground(QColor("#ff5555"))
            self.table.setItem(i, 1, param_item)
            
            # Description
            desc_text = p_info['desc']
            if is_missing:
                desc_text = "ERROR: This parameter was not recorded in the loaded flight log. Check your Blackbox settings or hardware."
                
            desc_item = QTableWidgetItem(desc_text)
            desc_item.setToolTip(p_info['desc'])
            if is_missing:
                desc_item.setForeground(QColor("#ff5555"))
            self.table.setItem(i, 2, desc_item)
            
            # Plot Toggle
            plot_val = item.get('plot', True)
            
            plot_item = QTableWidgetItem("A" if plot_val else "B")
            plot_item.setForeground(QColor(0,0,0,0)) # Hide text behind widget
            self.table.setItem(i, 3, plot_item)
            
            plot_toggle = ToggleSwitch(plot_val)
            plot_toggle.toggled.connect(self.on_plot_toggle)
            self.table.setCellWidget(i, 3, plot_toggle)
            
            # Trail Toggle
            trail_val = item.get('trail', False)
            
            trail_item = QTableWidgetItem("A" if trail_val else "B")
            trail_item.setForeground(QColor(0,0,0,0)) # Hide text behind widget
            self.table.setItem(i, 4, trail_item)
            
            trail_toggle = ToggleSwitch(trail_val)
            trail_toggle.toggled.connect(self.on_trail_toggle)
            self.table.setCellWidget(i, 4, trail_toggle)
            
            # Read-only items
            for j in range(3):
                self.table.item(i, j).setFlags(self.table.item(i, j).flags() ^ Qt.ItemFlag.ItemIsEditable)
        
        self.table.setSortingEnabled(True)

    def on_plot_toggle(self, checked):
        # We need to find which row this toggle belongs to
        for i in range(self.table.rowCount()):
            if self.table.cellWidget(i, 3) == self.sender():
                # Update item text so sorting works ("A" < "B")
                self.table.item(i, 3).setText("A" if checked else "B")
                # Update internal config
                p_id = self.table.item(i, 1).text()
                for item in self.config:
                    if item['param'] == p_id:
                        item['plot'] = checked
                        break
                break

    def on_trail_toggle(self, checked):
        for i in range(self.table.rowCount()):
            if self.table.cellWidget(i, 4) == self.sender():
                self.table.item(i, 4).setText("A" if checked else "B")
                p_id = self.table.item(i, 1).text()
                for item in self.config:
                    if item['param'] == p_id:
                        item['trail'] = checked
                        break
                break

    def apply_filter(self, text):
        text = text.lower()
        for i in range(self.table.rowCount()):
            match = False
            for j in range(3): # Name, Parameter, Description
                item = self.table.item(i, j)
                if item and text in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(i, not match)
        self.update_button_states()

    def on_header_clicked(self):
        self.is_sorted = True
        self.update_button_states()

    def update_button_states(self):
        # Disable move buttons if filtered or sorted
        is_filtered = len(self.search_input.text()) > 0
        disabled = is_filtered or self.is_sorted
        self.btn_up.setEnabled(not disabled)
        self.btn_down.setEnabled(not disabled)
        
        if disabled:
            msg = "Move disabled when filtered or sorted" if is_filtered or self.is_sorted else ""
            self.btn_up.setToolTip(msg)
            self.btn_down.setToolTip(msg)
        else:
            self.btn_up.setToolTip("")
            self.btn_down.setToolTip("")

    def move_up(self):
        row = self.table.currentRow()
        if row > 0:
            self.config[row], self.config[row-1] = self.config[row-1], self.config[row]
            self.populate_table()
            self.table.selectRow(row-1)

    def move_down(self):
        row = self.table.currentRow()
        if row < len(self.config) - 1:
            self.config[row], self.config[row+1] = self.config[row+1], self.config[row]
            self.populate_table()
            self.table.selectRow(row+1)

    def reset_order(self):
        msg = "This will reset the parameter list to the factory default order. Are you sure?"
        if not self.default_order:
            msg = "This will reset the parameter list to alphabetical order. Are you sure?"
            
        reply = QMessageBox.question(self, 'Confirm Reset', msg,
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                   QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.default_order:
                # Sort by the index in default_order. If not in default_order, put at the end.
                def get_sort_key(x):
                    p_id = x['param']
                    try:
                        return self.default_order.index(p_id)
                    except ValueError:
                        return 9999
                self.config.sort(key=get_sort_key)
            else:
                # Fallback to alphabetical if no default_order provided
                self.config.sort(key=lambda x: self.all_params.get(x['param'], {}).get('name', x['param']).lower())
            
            # Clear any visual sort on the table to avoid confusion
            self.table.setSortingEnabled(False)
            self.is_sorted = False
            
            self.populate_table()
            self.update_button_states()

    def apply_and_close(self):
        # Rebuild config based on current visual order in table
        new_config = []
        for i in range(self.table.rowCount()):
            # Find the original item in self.config by parameter name (column 1)
            param_id = self.table.item(i, 1).text()
            # Find the item in our internal list
            for item in self.config:
                if item['param'] == param_id:
                    # Update plot/trail from visual widgets
                    plot_widget = self.table.cellWidget(i, 3)
                    trail_widget = self.table.cellWidget(i, 4)
                    if plot_widget: item['plot'] = plot_widget.isChecked()
                    if trail_widget: item['trail'] = trail_widget.isChecked()
                    new_config.append(item)
                    break
        
        # Update the original list in-place so the caller's reference is updated
        self.config.clear()
        self.config.extend(new_config)
        
        self.config_changed.emit(new_config)
        self.accept()

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: white; }
            QTableWidget { 
                background-color: #252525; 
                color: #e0e0e0; 
                gridline-color: #444;
                border: none;
            }
            QHeaderView::section {
                background-color: #333;
                color: white;
                padding: 4pt;
                border: 1px solid #444;
            }
            QTableWidget::item:selected {
                background-color: #0078d7;
            }
            QPushButton {
                background-color: #1b5e20;
                border: 1px solid #2e7d32;
                color: #ffffff;
                padding: 5pt 15pt;
                min-height: 25pt;
                border-radius: 20pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2e7d32;
                border: 1px solid #4caf50;
            }
            QPushButton:pressed {
                background-color: #0d3b0f;
            }
            QPushButton:disabled {
                color: #999999;
                background-color: #2a2a2a;
                border: 1px solid #444444;
            }
        """)
