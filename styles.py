# Edit this file to customise the application's appearance.
APP_STYLESHEET = """
QWidget {
    background: #f7f9fc;
    color: #1f2937;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QLabel {
    background: transparent;
}
QMainWindow { background: #f7f9fc; }
QFrame#Sidebar {
    background: #1f2937;
    border: none;
}
QFrame#Sidebar QWidget {
    background: transparent;
}
QLabel#Brand {
    color: #ffffff;
    background: transparent;
    font-size: 12pt;
    font-weight: 700;
    padding: 8px 6px 18px 6px;
    qproperty-alignment: AlignCenter;
}
QLabel#CompanyLogo {
    background: white;
    border-radius: 8px;
    padding: 8px;
}
QPushButton#NavButton {
    color: #dbe5e7;
    background: transparent;
    text-align: left;
    padding: 12px 14px;
    border: none;
    border-radius: 8px;
    font-weight: 600;
}
QPushButton#NavButton:hover { background: #334155; }
QPushButton#NavButton:checked {
    background: #0f766e;
    color: white;
}
QLabel#PageTitle {
    font-size: 21pt;
    font-weight: 700;
    color: #1f2937;
}
QLabel#Muted { color: #64748b; }
QLabel#AssetLookup {
    background: #eef4f7;
    color: #334155;
    border: 1px solid #d5e0e8;
    border-radius: 6px;
    padding: 7px;
}
QLabel#AssetLookup[lookupState="valid"] {
    background: #ecfdf5;
    color: #166534;
    border-color: #b7e4c7;
}
QLabel#AssetLookup[lookupState="error"] {
    background: #fff1f2;
    color: #b42335;
    border-color: #fecdd3;
}
QFrame#Card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
}
QFrame#Card QLabel {
    background: transparent;
}
QLabel#CardTitle { color: #64748b; font-weight: 600; }
QLabel#CardValue { color: #1f2937; font-size: 24pt; font-weight: 700; }
QLineEdit, QComboBox, QDateEdit, QTextEdit {
    background: white;
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    padding: 7px;
    min-height: 18px;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border: 1px solid #0f766e;
}
QPushButton {
    background: #0f766e;
    color: white;
    border: none;
    border-radius: 7px;
    padding: 8px 13px;
    font-weight: 600;
}
QPushButton:hover { background: #0d5f59; }
QPushButton:disabled { background: #94a3b8; }
QPushButton#SecondaryButton {
    background: #e2e8f0;
    color: #334155;
}
QPushButton#DangerButton { background: #b42335; }
QTableWidget {
    background: white;
    alternate-background-color: #f8fafc;
    gridline-color: #e2e8f0;
    border: 1px solid #dbe3ec;
    border-radius: 8px;
    selection-background-color: #ccebe7;
    selection-color: #134e4a;
}
QHeaderView::section {
    background: #e8eef5;
    color: #334155;
    border: none;
    padding: 9px;
    font-weight: 700;
}
QStatusBar { background: white; color: #64748b; }
QScrollArea { border: none; }
"""
