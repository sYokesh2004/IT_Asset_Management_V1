import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import date
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QStackedWidget, QGridLayout, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QMessageBox, QDialog, QFormLayout, QTextEdit, QDateEdit,
    QDoubleSpinBox, QFileDialog, QHeaderView, QAbstractItemView, QScrollArea
)
import db
from styles import APP_STYLESHEET

DEVICE_TYPES = list(db.ASSET_PREFIXES.keys())
STATUSES = ["Working", "Faulty", "Under Repair", "In Storage", "Retired"]
APP_ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "app-icon.ico")
COMPANY_LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "company-logo.png")
WINDOWS_APP_ID = "ITAssetManagement.Desktop"
APP_DIR = (
    os.path.dirname(os.path.abspath(sys.executable))
    if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.abspath(__file__))
)
LOG_DIR = os.path.join(APP_DIR, "logs")
LOG_PATH = os.path.join(LOG_DIR, "application.log")
logger = logging.getLogger("it_asset_manager")

def configure_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    handler = RotatingFileHandler(
        LOG_PATH, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.info("Application starting")

def set_windows_app_identity():
    if sys.platform != "win32":
        return
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
DEVICE_COMPONENT_FIELDS = {
    "Desktop CPU": {"processor", "ram", "storage", "operating_system"},
    "Server": {"processor", "ram", "storage", "operating_system"},
    "Laptop": {"processor", "ram", "storage", "operating_system"},
}

def show_error(parent, exc):
    logger.exception("Operation failed")
    QMessageBox.critical(parent, "Unable to complete", str(exc))

def set_table(table, headers, rows):
    table.clear()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            item = QTableWidgetItem("" if value is None else str(value))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(r, c, item)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setStretchLastSection(True)

class AssetDialog(QDialog):
    def __init__(self, parent=None, asset=None):
        super().__init__(parent)
        self.asset = asset
        self.setWindowTitle("Edit Asset" if asset else "Register New Asset")
        self.resize(650, 720)
        outer = QVBoxLayout(self)
        form_widget = QWidget()
        form = QFormLayout()
        form_widget.setLayout(form)
        self.fields = {}
        def line(key, label, value=""):
            w = QLineEdit(str(value or ""))
            self.fields[key] = w
            form.addRow(label, w)
        self.device = QComboBox()
        self.device.addItems(DEVICE_TYPES)
        self.fields["device_type"] = self.device
        form.addRow("Device type *", self.device)
        self.form = form
        self.field_labels = {}
        for key, label in [
            ("brand","Brand"),("model","Model"),("manufacturer_serial","Manufacturer serial number"),
            ("processor","Processor"),("ram","RAM"),("storage","Storage"),("operating_system","Operating system"),
            ("staff_name","Assigned staff"),("purchase_date","Purchase date (YYYY-MM-DD)"),
            ("warranty_expiry","Warranty expiry (YYYY-MM-DD)")
        ]:
            line(key, label, asset[key] if asset else "")
            self.field_labels[key] = form.labelForField(self.fields[key])
        self.device.currentTextChanged.connect(self._update_component_fields)
        self.department = QComboBox()
        self.department.addItem("(Not assigned)", None)
        for d in db.list_departments():
            self.department.addItem(f'{d["code"]} — {d["name"]}', d["id"])
        form.addRow("Department", self.department)
        self.group = QComboBox()
        self.group.addItem("(No parent group)", None)
        for g in db.list_groups():
            self.group.addItem(f'{g["parent_code"]} — {g["group_name"]}', g["id"])
        form.addRow("Parent group", self.group)
        # Existing setup links are retained in the database, but Parent Group
        # is the only connection shown to users.
        self.setup_id = asset["setup_id"] if asset else None
        self.status = QComboBox()
        self.status.addItems(STATUSES)
        form.addRow("Status", self.status)
        self.notes = QTextEdit()
        self.notes.setMaximumHeight(85)
        form.addRow("Notes", self.notes)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(form_widget)
        outer.addWidget(scroll, 1)
        buttons = QHBoxLayout()
        save = QPushButton("Save Asset")
        cancel = QPushButton("Cancel")
        cancel.setObjectName("SecondaryButton")
        save.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        outer.addLayout(buttons)
        if asset:
            self.device.setCurrentText(asset["device_type"])
            self.status.setCurrentText(asset["status"])
            self.notes.setPlainText(asset["notes"] or "")
            for key, widget in self.fields.items():
                if key == "device_type": continue
                widget.setText(str(asset[key] or ""))
            self._select_data(self.department, asset["department_id"])
            self._select_data(self.group, asset["group_id"])
        self._update_component_fields(self.device.currentText())

    def _update_component_fields(self, device_type):
        visible_fields = DEVICE_COMPONENT_FIELDS.get(device_type, set())
        for key in ("processor", "ram", "storage", "operating_system"):
            visible = key in visible_fields
            self.fields[key].setVisible(visible)
            self.field_labels[key].setVisible(visible)

    @staticmethod
    def _select_data(combo, value):
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    def get_data(self):
        result = {k: w.currentText() if isinstance(w, QComboBox) else w.text()
                  for k, w in self.fields.items()}
        result["device_type"] = self.device.currentText()
        result["department_id"] = self.department.currentData()
        result["group_id"] = self.group.currentData()
        result["setup_id"] = self.setup_id
        result["status"] = self.status.currentText()
        result["notes"] = self.notes.toPlainText()
        for key in ("processor", "ram", "storage", "operating_system"):
            if key not in DEVICE_COMPONENT_FIELDS.get(result["device_type"], set()):
                result[key] = ""
        # Location ID is optional in this first screen; room/location records can be expanded later.
        result["location_id"] = None
        return result

class GroupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Parent Group")
        self.resize(480, 390)
        form = QFormLayout(self)
        self.name = QLineEdit()
        self.type = QComboBox()
        self.type.addItems(["Department", "Room", "Staff Assignment", "Other"])
        self.department = QComboBox()
        self.department.addItem("(No department)", None)
        for d in db.list_departments():
            self.department.addItem(f'{d["code"]} — {d["name"]}', d["id"])
        self.block = QLineEdit()
        self.floor = QLineEdit()
        self.room = QLineEdit()
        self.staff = QLineEdit()
        self.notes = QTextEdit()
        self.notes.setMaximumHeight(60)
        form.addRow("Group name *", self.name)
        form.addRow("Group type", self.type)
        form.addRow("Department", self.department)
        form.addRow("Block", self.block)
        form.addRow("Floor", self.floor)
        form.addRow("Room", self.room)
        form.addRow("Staff name", self.staff)
        form.addRow("Notes", self.notes)
        btn = QPushButton("Create Group")
        btn.clicked.connect(self.accept)
        form.addRow(btn)

    def get_data(self):
        return (self.name.text(), self.type.currentText(), self.department.currentData(),
                self.block.text(), self.floor.text(), self.room.text(),
                self.staff.text(), self.notes.toPlainText())

class DepartmentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Department")
        form = QFormLayout(self)
        self.code = QLineEdit()
        self.name = QLineEdit()
        form.addRow("Department code *", self.code)
        form.addRow("Department name *", self.name)
        btn = QPushButton("Save Department")
        btn.clicked.connect(self.accept)
        form.addRow(btn)

class FaultDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Report a Fault")
        form = QFormLayout(self)
        self.asset = QLineEdit()
        self.date = QDateEdit()
        self.date.setCalendarPopup(True)
        self.date.setDate(date.today())
        self.description = QTextEdit()
        self.description.setMaximumHeight(100)
        self.reporter = QLineEdit()
        self.priority = QComboBox()
        self.priority.addItems(["Low", "Normal", "High", "Critical"])
        asset_row = QWidget()
        asset_layout = QHBoxLayout(asset_row)
        asset_layout.setContentsMargins(0, 0, 0, 0)
        asset_layout.addWidget(self.asset, 1)
        load = QPushButton("Load Details")
        load.setObjectName("SecondaryButton")
        load.clicked.connect(self.load_asset)
        asset_layout.addWidget(load)
        form.addRow("Asset ID *", asset_row)
        self.asset_info = QLabel("Enter an Asset ID to load its details.")
        self.asset_info.setObjectName("AssetLookup")
        form.addRow("Asset details", self.asset_info)
        form.addRow("Reported date", self.date)
        form.addRow("Fault description *", self.description)
        form.addRow("Reported by", self.reporter)
        form.addRow("Priority", self.priority)
        btn = QPushButton("Save Fault")
        self.save_button = btn
        self.asset.editingFinished.connect(self.load_asset)
        self.asset.returnPressed.connect(self.load_asset)
        self.description.setEnabled(False)
        self.reporter.setEnabled(False)
        self.priority.setEnabled(False)
        btn.setEnabled(False)
        btn.clicked.connect(self.accept)
        form.addRow(btn)

    def load_asset(self):
        asset = db.get_asset_details_by_code(self.asset.text())
        if not asset:
            self.asset_info.setText("Asset ID not found. Check the ID and press Tab or Enter.")
            self.asset_info.setProperty("lookupState", "error")
            self.description.setEnabled(False)
            self.reporter.setEnabled(False)
            self.priority.setEnabled(False)
            self.save_button.setEnabled(False)
            return
        self.asset_info.setText(
            f'Asset ID: {asset["asset_code"]} | '
            f'Device type: {asset["device_type"]} | '
            f'Current status: {asset["status"]}'
        )
        self.asset_info.setProperty("lookupState", "valid")
        self.description.setEnabled(True)
        self.reporter.setEnabled(True)
        self.priority.setEnabled(True)
        self.save_button.setEnabled(True)
        self.asset_info.style().unpolish(self.asset_info)
        self.asset_info.style().polish(self.asset_info)

    def get_data(self):
        return self.asset.text().strip(), self.date.date().toString("yyyy-MM-dd"), \
               self.description.toPlainText(), self.reporter.text(), self.priority.currentText()

class ResolveDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Resolve Fault / Record Repair")
        form = QFormLayout(self)
        self.resolution = QTextEdit()
        self.resolution.setMaximumHeight(90)
        self.technician = QLineEdit()
        self.date = QDateEdit()
        self.date.setCalendarPopup(True)
        self.date.setDate(date.today())
        self.cost = QDoubleSpinBox()
        self.cost.setMaximum(100000000)
        self.cost.setPrefix("₹ ")
        form.addRow("Resolution / action taken *", self.resolution)
        form.addRow("Technician", self.technician)
        form.addRow("Repair date", self.date)
        form.addRow("Repair cost", self.cost)
        btn = QPushButton("Resolve and Save Repair")
        btn.clicked.connect(self.accept)
        form.addRow(btn)

    def get_data(self):
        return self.resolution.toPlainText(), self.technician.text(), \
               self.date.date().toString("yyyy-MM-dd"), self.cost.value()

class MovementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record Asset Movement")
        form = QFormLayout(self)
        self.asset = QLineEdit()
        self.date = QDateEdit()
        self.date.setCalendarPopup(True)
        self.date.setDate(date.today())
        self.reason = QLineEdit()
        self.moved_by = QLineEdit()
        asset_row = QWidget()
        asset_layout = QHBoxLayout(asset_row)
        asset_layout.setContentsMargins(0, 0, 0, 0)
        asset_layout.addWidget(self.asset, 1)
        load = QPushButton("Load Details")
        load.setObjectName("SecondaryButton")
        load.clicked.connect(self.load_asset)
        asset_layout.addWidget(load)
        form.addRow("Asset ID *", asset_row)
        self.asset_info = QLabel("Enter an Asset ID to load its details.")
        self.asset_info.setObjectName("AssetLookup")
        form.addRow("Asset details", self.asset_info)
        form.addRow("Movement date", self.date)
        self.department = QComboBox()
        self.department.addItem("(Select destination department)", None)
        for item in db.list_departments():
            self.department.addItem(f'{item["code"]} — {item["name"]}', item["id"])
        self.group = QComboBox()
        self.group.addItem("(Select destination parent group)", None)
        self._groups = db.list_groups()
        for item in self._groups:
            self.group.addItem(f'{item["parent_code"]} — {item["group_name"]}', item["id"])
        form.addRow("Destination department *", self.department)
        form.addRow("Destination parent group *", self.group)
        form.addRow("Reason", self.reason)
        form.addRow("Moved by", self.moved_by)
        btn = QPushButton("Save Movement")
        self.save_button = btn
        self.asset.editingFinished.connect(self.load_asset)
        self.asset.returnPressed.connect(self.load_asset)
        self.department.setEnabled(False)
        self.group.setEnabled(False)
        self.reason.setEnabled(False)
        self.moved_by.setEnabled(False)
        btn.setEnabled(False)
        btn.clicked.connect(self.accept)
        form.addRow(btn)

    def load_asset(self):
        asset = db.get_asset_details_by_code(self.asset.text())
        if not asset:
            self.asset_info.setText("Asset ID not found. Check the ID and press Tab or Enter.")
            self.asset_info.setProperty("lookupState", "error")
            self.department.setEnabled(False)
            self.group.setEnabled(False)
            self.reason.setEnabled(False)
            self.moved_by.setEnabled(False)
            self.save_button.setEnabled(False)
            return
        self.asset_info.setText(
            f'Asset ID: {asset["asset_code"]} | '
            f'Device type: {asset["device_type"]} | '
            f'Current status: {asset["status"]}'
        )
        self.asset_info.setProperty("lookupState", "valid")
        self.department.setEnabled(True)
        self.group.setEnabled(True)
        self.reason.setEnabled(True)
        self.moved_by.setEnabled(True)
        self.save_button.setEnabled(True)
        self.asset_info.style().unpolish(self.asset_info)
        self.asset_info.style().polish(self.asset_info)

    def get_data(self):
        return self.asset.text().strip(), self.date.date().toString("yyyy-MM-dd"), \
               self.department.currentData(), self.group.currentData(), \
               self.reason.text(), self.moved_by.text()

class AssetHistoryDialog(QDialog):
    def __init__(self, asset, history, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'{asset["asset_code"]} — Asset History')
        self.resize(980, 560)
        layout = QVBoxLayout(self)
        title = QLabel(f'{asset["asset_code"]} — {asset["device_type"]}')
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        details = QLabel(
            f'Brand: {asset["brand"] or "—"}    |    '
            f'Model: {asset["model"] or "—"}    |    '
            f'Current status: {asset["status"]}'
        )
        details.setObjectName("Muted")
        layout.addWidget(details)
        table = QTableWidget()
        set_table(
            table,
            ["Date", "Event", "Reference", "Details", "By", "Status / Result"],
            [[row["event_date"], row["event_type"], row["reference"],
              row["details"], row["performed_by"], row["status"]] for row in history],
        )
        layout.addWidget(table, 1)
        if not history:
            empty = QLabel("No fault, repair, or movement history has been recorded for this asset yet.")
            empty.setObjectName("Muted")
            layout.insertWidget(3, empty)
        close = QPushButton("Close")
        close.setObjectName("SecondaryButton")
        close.clicked.connect(self.reject)
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(close)
        layout.addLayout(buttons)

class GroupDetailsDialog(QDialog):
    def __init__(self, group, assets, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'{group["parent_code"]} — Group Assets')
        self.resize(820, 560)
        layout = QVBoxLayout(self)

        title = QLabel(f'{group["group_name"]}  ({group["parent_code"]})')
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        location = " / ".join(
            value for value in (group["block"], group["floor"], group["room"]) if value
        ) or "Location not assigned"
        details = QLabel(
            f'Group type: {group["group_type"]}    |    '
            f'Department: {group["department_name"] or "Not assigned"}    |    '
            f'Location: {location}'
        )
        details.setObjectName("Muted")
        layout.addWidget(details)

        if assets:
            connected = QLabel(f"{len(assets)} asset(s) in this parent group")
            connected.setObjectName("CardTitle")
            layout.addWidget(connected)
            table = QTableWidget()
            set_table(
                table,
                ["Device Type", "Brand", "Model", "Asset ID", "Status"],
                [[
                    asset["device_type"],
                    asset["brand"],
                    asset["model"],
                    asset["asset_code"],
                    asset["status"],
                ] for asset in assets],
            )
            table.cellClicked.connect(self.asset_row_clicked)
            for row in range(table.rowCount()):
                table.item(row, 3).setToolTip("Click anywhere in this row to view complete asset history")
            layout.addWidget(table, 1)
        else:
            empty = QLabel("No assets are connected to this group yet.")
            empty.setObjectName("Muted")
            layout.addWidget(empty)
            layout.addStretch()

        close = QPushButton("Close")
        close.setObjectName("SecondaryButton")
        close.clicked.connect(self.reject)
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(close)
        layout.addLayout(buttons)

    def asset_row_clicked(self, row, _column):
        asset_item = self.findChildren(QTableWidget)[0].item(row, 3)
        if not asset_item:
            return
        owner = self.parent()
        if owner and hasattr(owner, "show_asset_history"):
            owner.show_asset_history(asset_item.text())

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IT Asset Management")
        self.setWindowIcon(QIcon(APP_ICON))
        self.resize(1400, 850)
        self.pages = QStackedWidget()
        self.page_names = ["Dashboard", "Assets", "Groups", "Departments", "Faults", "Movements"]
        self.nav_buttons = []
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0,0,0,0)
        root_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(14,18,14,14)
        brand = QLabel("IT ASSET MANAGER")
        brand.setObjectName("Brand")
        side.addWidget(brand)
        for i, name in enumerate(self.page_names):
            b = QPushButton(name)
            b.setObjectName("NavButton")
            b.setCheckable(True)
            b.clicked.connect(lambda checked=False, idx=i: self.go(idx))
            self.nav_buttons.append(b)
            side.addWidget(b)
        side.addStretch()
        backup = QPushButton("Backup Database")
        backup.setObjectName("NavButton")
        backup.clicked.connect(self.backup)
        side.addWidget(backup)
        clear_data = QPushButton("Clear All Data")
        clear_data.setObjectName("DangerButton")
        clear_data.clicked.connect(self.clear_all_data)
        side.addWidget(clear_data)
        root_layout.addWidget(sidebar)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(26,22,26,18)
        content_header = QHBoxLayout()
        content_header.addStretch()
        company_logo = QLabel()
        company_logo.setObjectName("CompanyLogo")
        company_logo.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        company_logo.setPixmap(QPixmap(COMPANY_LOGO).scaled(
            360, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        ))
        content_header.addWidget(company_logo)
        content_layout.addLayout(content_header)
        content_layout.addWidget(self.pages, 1)
        root_layout.addWidget(content, 1)
        self.setCentralWidget(root)

        self.pages.addWidget(self.dashboard_page())
        self.pages.addWidget(self.assets_page())
        self.pages.addWidget(self.groups_page())
        self.pages.addWidget(self.departments_page())
        self.pages.addWidget(self.faults_page())
        self.pages.addWidget(self.movements_page())
        self.go(0)
        self.refresh_all()

    def page_header(self, title, subtitle):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0,0,0,10)
        title_l = QLabel(title); title_l.setObjectName("PageTitle")
        sub = QLabel(subtitle); sub.setObjectName("Muted")
        lay.addWidget(title_l); lay.addWidget(sub)
        return w

    def dashboard_page(self):
        page = QWidget(); lay = QVBoxLayout(page)
        lay.addWidget(self.page_header("Dashboard", "Overview of your institution's IT equipment"))
        self.dashboard_cards = {}
        grid = QGridLayout()
        card_defs = [("total","Total Assets"),("working","Working"),("faulty","Faulty"),
                     ("repair","Under Repair"),("groups","Parent Groups"),("open_faults","Open Faults")]
        for idx, (key, title) in enumerate(card_defs):
            card = QFrame(); card.setObjectName("Card")
            cl = QVBoxLayout(card); cl.setContentsMargins(18,16,18,16)
            tl = QLabel(title); tl.setObjectName("CardTitle")
            vl = QLabel("0"); vl.setObjectName("CardValue")
            cl.addWidget(tl); cl.addWidget(vl)
            grid.addWidget(card, idx//3, idx%3)
            self.dashboard_cards[key] = vl
        lay.addLayout(grid)
        lay.addStretch()
        hint = QLabel("Start by adding departments, then create Parent Groups and register physical assets.")
        hint.setObjectName("Muted")
        lay.addWidget(hint)
        return page

    def assets_page(self):
        page = QWidget(); lay = QVBoxLayout(page)
        lay.addWidget(self.page_header("Asset Register", "Register and search every physical device"))
        bar = QHBoxLayout()
        self.asset_search = QLineEdit(); self.asset_search.setPlaceholderText("Search ID, device, brand, model, department or status...")
        self.asset_search.textChanged.connect(self.refresh_assets)
        bar.addWidget(self.asset_search, 1)
        add = QPushButton("＋ Register Asset"); add.clicked.connect(self.add_asset)
        bar.addWidget(add)
        edit = QPushButton("Edit Selected"); edit.setObjectName("SecondaryButton"); edit.clicked.connect(self.edit_asset)
        bar.addWidget(edit)
        qr = QPushButton("Print QR Sticker"); qr.clicked.connect(self.qr_sticker)
        bar.addWidget(qr)
        export = QPushButton("Export Excel"); export.setObjectName("SecondaryButton"); export.clicked.connect(self.export_excel)
        bar.addWidget(export)
        lay.addLayout(bar)
        self.asset_table = QTableWidget()
        lay.addWidget(self.asset_table, 1)
        return page

    def groups_page(self):
        page = QWidget(); lay = QVBoxLayout(page)
        lay.addWidget(self.page_header("Parent Groups", "Create groups for departments, rooms or staff assignments"))
        bar = QHBoxLayout()
        self.group_search = QLineEdit()
        self.group_search.setPlaceholderText("Search Parent ID, group name, department or room...")
        self.group_search.textChanged.connect(self.refresh_groups)
        bar.addWidget(self.group_search, 1)
        add = QPushButton("＋ Create Parent Group"); add.clicked.connect(self.add_group)
        bar.addWidget(add)
        view = QPushButton("View Group Assets")
        view.setObjectName("SecondaryButton")
        view.clicked.connect(self.show_group_details)
        bar.addWidget(view)
        lay.addLayout(bar)
        self.group_table = QTableWidget()
        self.group_table.cellClicked.connect(self.show_group_details)
        self.group_table.cellDoubleClicked.connect(self.show_group_details)
        lay.addWidget(self.group_table, 1)
        return page

    def departments_page(self):
        page = QWidget(); lay = QVBoxLayout(page)
        lay.addWidget(self.page_header("Departments", "Create the department master list before registering assets"))
        bar = QHBoxLayout()
        add = QPushButton("＋ Add Department"); add.clicked.connect(self.add_department)
        bar.addWidget(add); bar.addStretch()
        lay.addLayout(bar)
        self.department_table = QTableWidget(); lay.addWidget(self.department_table, 1)
        return page

    def faults_page(self):
        page = QWidget(); lay = QVBoxLayout(page)
        lay.addWidget(self.page_header("Faults & Repairs", "Record faults and preserve service history"))
        bar = QHBoxLayout()
        self.fault_search = QLineEdit(); self.fault_search.setPlaceholderText("Search fault ID, asset ID, description or status...")
        self.fault_search.textChanged.connect(self.refresh_faults)
        bar.addWidget(self.fault_search, 1)
        report = QPushButton("＋ Report Fault"); report.clicked.connect(self.add_fault)
        bar.addWidget(report)
        resolve = QPushButton("Resolve Selected"); resolve.setObjectName("SecondaryButton"); resolve.clicked.connect(self.resolve_fault)
        bar.addWidget(resolve)
        lay.addLayout(bar)
        self.fault_table = QTableWidget(); lay.addWidget(self.fault_table, 1)
        self.fault_table.cellClicked.connect(self.fault_asset_clicked)
        return page

    def movements_page(self):
        page = QWidget(); lay = QVBoxLayout(page)
        lay.addWidget(self.page_header("Asset Movements", "Record when an asset moves between rooms or departments"))
        bar = QHBoxLayout()
        add = QPushButton("＋ Record Movement"); add.clicked.connect(self.add_movement)
        bar.addWidget(add); bar.addStretch()
        lay.addLayout(bar)
        self.movement_table = QTableWidget(); lay.addWidget(self.movement_table, 1)
        self.movement_table.cellClicked.connect(self.movement_asset_clicked)
        return page

    def go(self, idx):
        self.pages.setCurrentIndex(idx)
        for i, b in enumerate(self.nav_buttons):
            b.setChecked(i == idx)

    def refresh_all(self):
        self.refresh_dashboard(); self.refresh_assets(); self.refresh_groups()
        self.refresh_departments(); self.refresh_faults(); self.refresh_movements()

    def refresh_dashboard(self):
        counts = db.dashboard_counts()
        for k, v in counts.items():
            self.dashboard_cards[k].setText(str(v))

    def refresh_assets(self, *_):
        if not hasattr(self, "asset_table"): return
        rows = db.list_assets(self.asset_search.text() if hasattr(self, "asset_search") else "")
        data = []
        self.asset_row_ids = []
        for a in rows:
            data.append([a["asset_code"],a["device_type"],a["brand"],a["model"],
                         a["department_name"] or "",a["parent_code"] or "",
                         a["setup_code"] or "",a["status"]])
            self.asset_row_ids.append(a["id"])
        set_table(self.asset_table, ["Asset ID","Device Type","Brand","Model","Department",
                                     "Parent ID","Setup ID","Status"], data)

    def refresh_groups(self):
        if not hasattr(self, "group_table"): return
        rows = db.list_groups()
        search = self.group_search.text().strip().casefold() if hasattr(self, "group_search") else ""
        if search:
            rows = [
                group for group in rows
                if search in " ".join(
                    str(group[key] or "") for key in
                    ("parent_code", "group_name", "group_type", "department_name", "block", "floor", "room", "staff_name")
                ).casefold()
            ]
        self.group_row_ids = [group["id"] for group in rows]
        set_table(self.group_table, ["Parent ID","Group Name","Type","Department","Block","Floor","Room","Staff"],
                  [[g["parent_code"],g["group_name"],g["group_type"],g["department_name"] or "",
                    g["block"] or "",g["floor"] or "",g["room"] or "",g["staff_name"] or ""] for g in rows])

    def show_group_details(self, *_):
        group_id = self.selected_id(self.group_table, self.group_row_ids)
        if group_id is None:
            return
        group = next((item for item in db.list_groups() if item["id"] == group_id), None)
        if group is None:
            show_error(self, ValueError("The selected group could not be found."))
            return
        GroupDetailsDialog(group, db.list_group_assets(group_id), self).exec()

    def refresh_departments(self):
        if not hasattr(self, "department_table"): return
        rows = db.list_departments()
        set_table(self.department_table, ["Code","Department Name","Created"],
                  [[d["code"],d["name"],d["created_at"]] for d in rows])

    def refresh_faults(self, *_):
        if not hasattr(self, "fault_table"): return
        rows = db.list_faults(self.fault_search.text() if hasattr(self, "fault_search") else "")
        self.fault_row_ids = [f["id"] for f in rows]
        set_table(self.fault_table, ["Fault ID","Asset ID","Device","Reported","Description","Priority","Status"],
                  [[f["fault_code"],f["asset_code"],f["device_type"],f["reported_date"],
                    f["description"],f["priority"],f["status"]] for f in rows])
        for row in range(self.fault_table.rowCount()):
            self.fault_table.item(row, 1).setToolTip("Click to view complete asset history")

    def refresh_movements(self):
        if not hasattr(self, "movement_table"): return
        with db.connect() as con:
            rows = con.execute("""SELECT m.*, a.asset_code FROM asset_movements m
                                  JOIN assets a ON a.id=m.asset_id ORDER BY m.id DESC""").fetchall()
        set_table(self.movement_table, ["Asset ID","Date","From","To","Reason","Moved By"],
                  [[m["asset_code"],m["movement_date"],m["from_location"],m["to_location"],
                    m["reason"],m["moved_by"]] for m in rows])
        for row in range(self.movement_table.rowCount()):
            self.movement_table.item(row, 0).setToolTip("Click to view complete asset history")

    def show_asset_history(self, asset_code):
        try:
            asset, history = db.get_asset_history(asset_code)
            AssetHistoryDialog(asset, history, self).exec()
        except Exception as exc:
            show_error(self, exc)

    def fault_asset_clicked(self, row, _column):
        asset_item = self.fault_table.item(row, 1)
        if asset_item:
            self.show_asset_history(asset_item.text())

    def movement_asset_clicked(self, row, _column):
        asset_item = self.movement_table.item(row, 0)
        if asset_item:
            self.show_asset_history(asset_item.text())

    def selected_id(self, table, ids):
        row = table.currentRow()
        if row < 0 or row >= len(ids):
            QMessageBox.information(self, "Select a row", "Please select a row first.")
            return None
        return ids[row]

    def add_asset(self):
        dlg = AssetDialog(self)
        if dlg.exec():
            try:
                code = db.save_asset(dlg.get_data())
                self.refresh_all()
                QMessageBox.information(self, "Asset registered", f"Asset created successfully.\n\nAsset ID: {code}")
            except Exception as e: show_error(self, e)

    def edit_asset(self):
        asset_id = self.selected_id(self.asset_table, self.asset_row_ids)
        if asset_id is None: return
        asset = db.get_asset(asset_id)
        dlg = AssetDialog(self, asset)
        if dlg.exec():
            try:
                code = db.save_asset(dlg.get_data(), asset_id)
                self.refresh_all()
                QMessageBox.information(self, "Asset updated", f"Updated {code}")
            except Exception as e: show_error(self, e)

    def add_department(self):
        dlg = DepartmentDialog(self)
        if dlg.exec():
            try:
                db.add_department(dlg.code.text(), dlg.name.text())
                self.refresh_all()
            except Exception as e: show_error(self, e)

    def add_group(self):
        dlg = GroupDialog(self)
        if dlg.exec():
            try:
                data = dlg.get_data()
                code = db.create_group(*data)
                self.refresh_all()
                QMessageBox.information(self, "Group created", f"Parent ID: {code}")
            except Exception as e: show_error(self, e)

    def add_fault(self):
        dlg = FaultDialog(self)
        if dlg.exec():
            try:
                code, d, desc, reporter, priority = dlg.get_data()
                if not desc.strip(): raise ValueError("Fault description is required.")
                fault = db.add_fault(code, d, desc, reporter, priority)
                self.refresh_all()
                QMessageBox.information(self, "Fault saved", f"Fault report created: {fault}")
            except Exception as e: show_error(self, e)

    def resolve_fault(self):
        fault_id = self.selected_id(self.fault_table, self.fault_row_ids)
        if fault_id is None: return
        dlg = ResolveDialog(self)
        if dlg.exec():
            try:
                resolution, tech, d, cost = dlg.get_data()
                if not resolution.strip(): raise ValueError("Resolution is required.")
                db.resolve_fault(fault_id, resolution, tech, d, cost)
                self.refresh_all()
            except Exception as e: show_error(self, e)

    def add_movement(self):
        dlg = MovementDialog(self)
        if dlg.exec():
            try:
                code, d, department_id, group_id, reason, moved_by = dlg.get_data()
                if department_id is None:
                    raise ValueError("Destination department is required.")
                if group_id is None:
                    raise ValueError("Destination parent group is required.")
                db.add_movement(code, d, department_id, group_id, reason, moved_by)
                self.refresh_all()
                QMessageBox.information(self, "Movement saved",
                                        "Movement history saved and the asset's current assignment was updated.")
            except Exception as e: show_error(self, e)

    def clear_all_data(self):
        answer = QMessageBox.warning(
            self,
            "Clear all database data",
            "This will permanently delete all departments, groups, assets, fault reports, "
            "repairs, and movement history.\n\nThe database structure will be kept, but "
            "this action cannot be undone. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            db.clear_all_data()
            self.refresh_all()
            QMessageBox.information(
                self,
                "Database cleared",
                "All data was removed. You can now add new records.",
            )
        except Exception as exc:
            show_error(self, exc)

    def qr_sticker(self):
        asset_id = self.selected_id(self.asset_table, self.asset_row_ids)
        if asset_id is None: return
        asset = db.get_asset(asset_id)
        choice = QMessageBox(self)
        choice.setWindowTitle("Choose Sticker Format")
        choice.setText(f'Choose the sticker format for {asset["asset_code"]}.')
        qr_details = choice.addButton("QR + Details", QMessageBox.ButtonRole.AcceptRole)
        serial_only = choice.addButton("Serial No. Only", QMessageBox.ButtonRole.DestructiveRole)
        choice.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        choice.exec()
        if choice.clickedButton() not in (qr_details, serial_only):
            return
        include_qr = choice.clickedButton() == qr_details
        path, _ = QFileDialog.getSaveFileName(self, "Save QR Sticker", f'{asset["asset_code"]}.png',
                                               "PNG Image (*.png)")
        if not path: return
        try:
            import qrcode
            from PIL import Image, ImageDraw, ImageFont
            qr_img = None
            if include_qr:
                qr = qrcode.QRCode(box_size=8, border=2)
                qr.add_data(asset["asset_code"])
                qr.make(fit=True)
                qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
                canvas = Image.new("RGB", (qr_img.width + 40, qr_img.height + 100), "white")
                canvas.paste(qr_img, (20, 10))
            else:
                canvas = Image.new("RGB", (620, 150), "white")
            draw = ImageDraw.Draw(canvas)
            try: font = ImageFont.truetype("arial.ttf", 20)
            except OSError: font = ImageFont.load_default()
            if include_qr:
                draw.text((20, qr_img.height + 20), asset["asset_code"], fill="black", font=font)
                draw.text((20, qr_img.height + 50), asset["device_type"], fill="black", font=font)
            else:
                draw.text((20, 50), asset["asset_code"], fill="black", font=font)
            canvas.save(path)
            QMessageBox.information(self, "Sticker created", f"Saved sticker image:\n{path}\nPrint it using your label printer or image viewer.")
        except Exception as e: show_error(self, e)

    def export_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Asset Register", "asset_register.xlsx",
                                               "Excel Workbook (*.xlsx)")
        if not path: return
        try:
            db.export_assets_xlsx(path)
            QMessageBox.information(self, "Export complete", f"Exported to:\n{path}")
        except Exception as e: show_error(self, e)

    def backup(self):
        path, _ = QFileDialog.getSaveFileName(self, "Backup Database", "asset_management_backup.db",
                                               "SQLite Database (*.db)")
        if not path: return
        try:
            db.backup_database(path)
            QMessageBox.information(self, "Backup complete", f"Backup saved to:\n{path}")
        except Exception as e: show_error(self, e)

def main():
    configure_logging()
    try:
        db.init_db()
        logger.info("Database initialized at %s", db.DB_PATH)
        set_windows_app_identity()
        app = QApplication(sys.argv)
        app.setWindowIcon(QIcon(APP_ICON))
        app.setStyle("Fusion")
        app.setStyleSheet(APP_STYLESHEET)
        window = MainWindow()
        window.show()
        logger.info("Main window displayed")
        sys.exit(app.exec())
    except Exception:
        logger.exception("Application startup failed")
        raise

if __name__ == "__main__":
    main()
