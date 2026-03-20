import sys
import logging
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QTableWidget, QTableWidgetItem, QLabel, QHeaderView,
    QMessageBox, QFileDialog, QFrame, QProgressBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QIcon, QFont
from pathlib import Path

import config
import database
import parser
import web_fetcher

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KovaaksTracker")
        self.resize(1100, 650)
        
        # Local memory for filtering/sorting
        self.all_scenarios_data = []
        
        self.stats_folder, self.stats_folder_status = config.find_stats_folder()
        
        self.init_ui()
        self.refresh_data()
        
    def init_ui(self):
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        
        # Top Dashboard Bar
        top_bar = QHBoxLayout()
        
        status_text = f"Stats Folder ({self.stats_folder_status}): {self.stats_folder}" if self.stats_folder else "Stats Folder: Not Found"
        self.status_label = QLabel(status_text)
        self.status_label.setStyleSheet("font-weight: bold; color: #333;")
        
        btn_select_folder = QPushButton("📁 Select Stats Folder")
        btn_select_folder.clicked.connect(self.select_folder)
        
        btn_refresh = QPushButton("🔄 Refresh Local Data")
        btn_refresh.clicked.connect(self.refresh_data)
        
        btn_sync_selected = QPushButton("🎯 Sync Selected Scenario")
        btn_sync_selected.setToolTip("Fetches data for the selected row only")
        btn_sync_selected.clicked.connect(self.sync_selected_data)
        
        btn_web_sync = QPushButton("🌐 Sync All (Slow)")
        btn_web_sync.setToolTip("Fetches missing data from kovaaks.com for all rows")
        btn_web_sync.clicked.connect(self.sync_web_data)
        
        btn_show_graph = QPushButton("📈 Show Graph")
        btn_show_graph.setToolTip("Shows historical performance for the selected scenario")
        btn_show_graph.clicked.connect(self.show_performance_graph)
        
        top_bar.addWidget(self.status_label)
        top_bar.addStretch()
        top_bar.addWidget(btn_show_graph)
        top_bar.addWidget(btn_sync_selected)
        top_bar.addWidget(btn_web_sync)
        top_bar.addWidget(btn_select_folder)
        top_bar.addWidget(btn_refresh)
        
        layout.addLayout(top_bar)
        
        # ---------------------------------------------------------
        # Search & Sort Bar
        # ---------------------------------------------------------
        from PySide6.QtWidgets import QLineEdit, QComboBox
        
        search_sort_bar = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search Scenarios...")
        self.search_input.textChanged.connect(self.render_table)
        
        sort_label = QLabel("Sort By:")
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "Default (Last Played)",
            "Plays (High to Low)",
            "Plays (Low to High)",
            "Rank (High to Low)",
            "Rank (Low to High)",
            "Tier (High to Low)",
            "Tier (Low to High)"
        ])
        self.sort_combo.currentIndexChanged.connect(self.render_table)
        
        search_sort_bar.addWidget(self.search_input, stretch=1)
        search_sort_bar.addWidget(sort_label)
        search_sort_bar.addWidget(self.sort_combo)
        
        layout.addLayout(search_sort_bar)
        
        # ---------------------------------------------------------
        # Premium Overall Stats Card
        # ---------------------------------------------------------
        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet("""
            QFrame {
                background: linear-gradient(to right, #2a2a3e, #1f1f2e);
                background-color: #2a2a3e;
                border-radius: 8px;
                border: 1px solid #3a3a5e;
            }
            QLabel {
                color: #e0e0ff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        stats_layout = QHBoxLayout(self.stats_frame)
        stats_layout.setContentsMargins(20, 15, 20, 15)
        stats_layout.setSpacing(30)
        
        self.lbl_overall_lvl = QLabel("Overall Lv. 1")
        self.lbl_overall_lvl.setStyleSheet("font-size: 24px; font-weight: 900; color: #ffd700;") # Gold
        
        self.lbl_total_plays = QLabel("Total Plays\n0")
        self.lbl_total_plays.setStyleSheet("font-size: 14px; font-weight: bold; text-align: center;")
        self.lbl_total_plays.setAlignment(Qt.AlignCenter)
        
        self.lbl_next_lvl = QLabel("Next Lvl In\n100 Plays")
        self.lbl_next_lvl.setStyleSheet("font-size: 14px; font-weight: bold; text-align: center; color: #ff9999;")
        self.lbl_next_lvl.setAlignment(Qt.AlignCenter)
        
        stats_layout.addWidget(self.lbl_overall_lvl)
        stats_layout.addStretch()
        stats_layout.addWidget(self.lbl_total_plays)
        stats_layout.addWidget(self.lbl_next_lvl)
        
        layout.addWidget(self.stats_frame)
        
        # ---------------------------------------------------------
        # Main Table
        # ---------------------------------------------------------
        self.table = QTableWidget()
        # Updated Headers for Web Fetcher Data
        headers = [
            "Scenario Name", "Plays", "Lvl", "Next Lvl", 
            "Best Score", "Rank", "Total Entries", "Top %", "Tier"
        ]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        
        # Adjust column sizing
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, len(headers)):
            header_view.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        # Double click to sync
        self.table.doubleClicked.connect(self.sync_selected_data)
        
        layout.addWidget(self.table)
        
        self.setCentralWidget(main_widget)
        
    def select_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Select KovaaK's stats folder")
        if directory:
            self.stats_folder = Path(directory)
            self.stats_folder_status = "Saved"
            
            # Save to config
            settings = config.load_settings()
            settings['stats_folder'] = str(self.stats_folder)
            config.save_settings(settings)
            
            self.status_label.setText(f"Stats Folder (Saved): {self.stats_folder}")
            self.refresh_data()
            
    def refresh_data(self):
        if not self.stats_folder or not self.stats_folder.exists():
            return
            
        self.status_label.setText(f"Loading from {self.stats_folder}...")
        QApplication.processEvents()
        
        results = parser.parse_stats_folder(self.stats_folder)
        
        for name, data in results.items():
            database.update_scenario_local_stats(
                scenario_name=data['scenario_name'],
                play_count=data['play_count'],
                best_score=data['best_score'],
                last_played=data['last_played'],
                level=data['level'],
                remaining=data['next_level_remaining'],
                history=data.get('history', [])
            )
            
        self.status_label.setText(f"Stats Folder ({self.stats_folder_status}): {self.stats_folder}")
        self.load_table_from_db()

    def sync_selected_data(self):
        """Fetches web data only for the currently selected scenario."""
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Info", "Please select a scenario row first.")
            return
            
        # The first column is Scenario Name, 5th column (idx 4) is Best Score
        row = selected_items[0].row()
        scenario_item = self.table.item(row, 0)
        scenario_name = scenario_item.text()
        
        score_item = self.table.item(row, 4)
        local_best_score = float(score_item.text()) if score_item and score_item.text() != "0.00" else None
        
        self.status_label.setText(f"Fetching data for {scenario_name}...")
        QApplication.processEvents()
        
        web_data = web_fetcher.fetch_scenario_data(scenario_name, local_best_score)
        logging.info(f"Received web_data in UI sync_selected_data: {web_data}")
        
        if web_data is None:
            logging.warning(f"web_fetcher returned None for '{scenario_name}'.")
            QMessageBox.warning(self, "Warning", f"Failed to retrieve data for '{scenario_name}'. Please check the console logs.")
            self.status_label.setText("Web sync failed.")
            return
            
        database.update_scenario_web_stats(scenario_name, web_data)
        
        self.status_label.setText("Web sync complete.")
        self.load_table_from_db()

    def sync_web_data(self):
        """Iterates through scenarios and fetches web data."""
        records = database.get_all_scenarios()
        if not records:
            QMessageBox.information(self, "Info", "No scenarios found to sync.")
            return
            
        self.status_label.setText("Fetching data from web...")
        
        for i, rec in enumerate(records):
            scenario_name = rec['scenario_name']
            best_score = rec['best_score'] if rec['best_score'] > 0 else None
            
            self.status_label.setText(f"Fetching mapping list ({i+1}/{len(records)}): {scenario_name}")
            QApplication.processEvents()
            
            # Fetch and update
            web_data = web_fetcher.fetch_scenario_data(scenario_name, best_score)
            logging.info(f"Received web_data in UI sync_web_data for '{scenario_name}': {web_data}")
            
            if web_data is not None:
                database.update_scenario_web_stats(scenario_name, web_data)
            else:
                logging.warning(f"Skipping DB update for '{scenario_name}' as web_fetcher returned None.")
            
        self.status_label.setText("Web sync complete.")
        self.load_table_from_db()
        QMessageBox.information(self, "Success", "Web Sync completed. (Check console logs for details)")
        
    def show_performance_graph(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Info", "Please select a scenario row to view its graph.")
            return
            
        row = selected_items[0].row()
        scenario_item = self.table.item(row, 0)
        scenario_name = scenario_item.text()
        
        history = database.get_play_history(scenario_name)
        if not history:
            QMessageBox.information(self, "Info", f"No historical data found for '{scenario_name}'. Try refreshing local data.")
            return
            
        # Convert to pandas DataFrame
        df = pd.DataFrame(history, columns=['timestamp', 'score'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['Date'] = df['timestamp'].dt.date
        
        # Calculate aggregations
        daily_max = df.groupby('Date')['score'].max()
        daily_avg = df.groupby('Date')['score'].mean()
        
        # Calculate 7-day moving average on the daily average.
        # We need to reindex to fill missing days to make the rolling window accurate over actual time, 
        # but for simplicity and robustness with sparse data, we'll roll over the available data points.
        moving_avg = daily_avg.rolling(window=7, min_periods=1).mean()
        
        # Create Plot Dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Performance Graph: {scenario_name}")
        dialog.resize(800, 500)
        
        layout = QVBoxLayout(dialog)
        
        fig = Figure(figsize=(8, 5))
        canvas = FigureCanvasQTAgg(fig)
        layout.addWidget(canvas)
        
        ax = fig.add_subplot(111)
        
        # Plot lines
        ax.plot(daily_max.index, daily_max.values, marker='o', linestyle='-', color='#4CAF50', label='Daily Max Score', linewidth=2, markersize=4)
        ax.plot(daily_avg.index, daily_avg.values, marker='x', linestyle='--', color='#2196F3', label='Daily Avg Score', alpha=0.7)
        ax.plot(moving_avg.index, moving_avg.values, linestyle='-', color='#FF9800', label='7-Day Moving Avg', linewidth=3, alpha=0.9)
        
        # Styling
        total_plays = len(df)
        ax.set_title(f"{scenario_name}\nTotal Plays: {total_plays}", fontsize=14, fontweight='bold', pad=15)
        ax.set_xlabel("Date", fontsize=10)
        ax.set_ylabel("Score", fontsize=10)
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.legend(loc='best')
        
        fig.autofmt_xdate() # Rotate dates
        fig.tight_layout()
        
        dialog.exec()
        
    def get_tier_color(self, tier: str) -> QColor:
        color_map = {
            "Legend": QColor(255, 0, 0, 50),     # Red
            "Mythic": QColor(255, 105, 180, 50), # Pink
            "Celestial": QColor(255, 165, 0, 50),# Orange
            "Grandmaster": QColor(138, 43, 226, 50), # Purple
            "Master": QColor(0, 0, 255, 40),     # Blue
            "Diamond": QColor(0, 255, 255, 40),  # Cyan
            "Platinum": QColor(0, 250, 154, 40), # Green/Aqua
            "Gold": QColor(255, 215, 0, 40),     # Gold
            "Silver": QColor(192, 192, 192, 40), # Silver
            "Bronze": QColor(205, 127, 50, 40)   # Bronze
        }
        return color_map.get(tier, QColor(255, 255, 255, 0)) # default transparent

    def load_table_from_db(self):
        self.all_scenarios_data = database.get_all_scenarios()
        
        # Compute Overall Stats
        total_plays = sum(rec['local_play_count'] for rec in self.all_scenarios_data)
        overall_level = (total_plays // config.PLAYS_PER_LEVEL) + 1
        next_level_in = config.PLAYS_PER_LEVEL - (total_plays % config.PLAYS_PER_LEVEL)
        
        self.lbl_overall_lvl.setText(f"🏆 Overall Lv. {overall_level}")
        self.lbl_total_plays.setText(f"Total Plays\n{total_plays}")
        self.lbl_next_lvl.setText(f"Next Lvl In\n{next_level_in} Plays")
        
        self.render_table()
        
    def _calculate_search_score(self, scenario_name, query_lower):
        """Returns a sort score for fuzzy/priority matching. Higher is better."""
        name_lower = scenario_name.lower()
        if not query_lower:
            return 0
        if name_lower == query_lower:
            return 100 # Exact
        if name_lower.startswith(query_lower):
            return 50  # Prefix
        if query_lower in name_lower:
            return 10  # Partial
        
        # Poor-man's fuzzy sequence matching (check if chars appear in order)
        idx = 0
        for char in query_lower:
            idx = name_lower.find(char, idx)
            if idx == -1:
                return -1 # Fails fuzzy
            idx += 1
        return 1 # Passed fuzzy sequential check
        
    def render_table(self):
        """Filters, sorts, and renders the data from memory."""
        query = self.search_input.text().strip().lower()
        sort_mode = self.sort_combo.currentText()
        
        filtered_records = []
        
        for rec in self.all_scenarios_data:
            score = self._calculate_search_score(rec['scenario_name'], query)
            if query and score < 0:
                continue # Skip if it doesn't match search
            filtered_records.append((score, rec))
            
        # Sorting logic combining search score and selected sort mode
        def sort_key(item):
            search_score, rec = item
            
            # Extract sort values, handling Nones safely
            plays = rec['local_play_count']
            rank_raw = rec.get('web_rank')
            
            # Rank sorting trick: to make None/'-' appear at the bottom during asc AND desc sorts,
            # we assign them a very high or very low value depending on the sort direction.
            # Best rank is 1. Worst rank is +Infinity.
            valid_rank = rank_raw if rank_raw is not None and isinstance(rank_raw, (int, float)) else float('inf')
            
            tier_val = rec.get('tier_rank', '-')
            if not tier_val: tier_val = '-'
            
            tier_order = {
                "Legend": 1,
                "Mythic": 2,
                "Celestial": 3,
                "Grandmaster": 4,
                "Master": 5,
                "Diamond": 6,
                "Platinum": 7,
                "Gold": 8,
                "Silver": 9,
                "Bronze": 10
            }
            tier_rank_num = tier_order.get(tier_val, float('inf'))
            
            if "Plays (High to Low)" in sort_mode:
                return (-search_score, -plays)
            elif "Plays (Low to High)" in sort_mode:
                return (-search_score, plays)
            elif "Rank (High to Low)" in sort_mode:
                # Rank 1 is "High" conceptually, so we sort numerical rank ascending. Nones fallback to inf.
                return (-search_score, valid_rank)
            elif "Rank (Low to High)" in sort_mode:
                # Rank 1,000,000 is "Low" conceptually. We sort descending. Let's make Nones absolute lowest (sorted first inverted, so we multiply by -1)
                inverted_rank = -valid_rank if valid_rank != float('inf') else float('-inf')
                return (-search_score, inverted_rank)
            elif "Tier (High to Low)" in sort_mode:
                # Legend (1) is High, so ascending order
                return (-search_score, tier_rank_num)
            elif "Tier (Low to High)" in sort_mode:
                inverted_tier = -tier_rank_num if tier_rank_num != float('inf') else float('-inf')
                return (-search_score, inverted_tier)
            else:
                # Default behavior: Search Score first, then roughly maintain DB order (which is last_played desc implicitly)
                return (-search_score, 0)
                
        filtered_records.sort(key=sort_key)
        
        # Populate table
        self.table.setRowCount(len(filtered_records))
        
        for row, (_, rec) in enumerate(filtered_records):
            rank_val = rec.get('web_rank')
            entries_val = rec.get('web_total_entries')
            top_pct_val = rec.get('top_percent')
            tier_val = rec.get('tier_rank')
            
            rank_str = str(rank_val) if rank_val is not None else '-'
            entries_str = str(entries_val) if entries_val is not None else '-'
            top_pct_str = f"{top_pct_val:.2f}%" if top_pct_val is not None else '-'
            tier_str = str(tier_val) if tier_val else '-'
            
            items = [
                QTableWidgetItem(str(rec['scenario_name'])),
                QTableWidgetItem(str(rec['local_play_count'])),
                QTableWidgetItem(), # Placeholder for styled Level
                QTableWidgetItem(), # Placeholder for Progress Bar
                QTableWidgetItem(f"{rec['best_score']:.2f}"),
                QTableWidgetItem(rank_str),
                QTableWidgetItem(entries_str),
                QTableWidgetItem(top_pct_str),
                QTableWidgetItem(tier_str)
            ]
            
            for col_idx in range(1, len(items)):
                if col_idx not in (2, 3): # Skip custom widgets
                    items[col_idx].setTextAlignment(Qt.AlignCenter)
                    
            # -------------------------------------------------------------
            # Premium Lvl Styling
            # -------------------------------------------------------------
            lvl_val = rec['level']
            lvl_item = items[2]
            lvl_item.setTextAlignment(Qt.AlignCenter)
            lvl_item.setText(f"Lv.{lvl_val}")
            
            # Simple color bucketing for level prestige
            if lvl_val >= 50:
                lvl_item.setBackground(QBrush(QColor(255, 215, 0, 80)))  # Gold
                lvl_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            elif lvl_val >= 25:
                lvl_item.setBackground(QBrush(QColor(192, 192, 192, 80))) # Silver
                lvl_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            elif lvl_val >= 10:
                lvl_item.setBackground(QBrush(QColor(205, 127, 50, 80)))  # Bronze
                lvl_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            else:
                lvl_item.setFont(QFont("Segoe UI", 10))
                
            # -------------------------------------------------------------
            # Premium Progress Bar - Next Lvl In
            # -------------------------------------------------------------
            remaining = rec['next_level_remaining']
            progress_val = config.PLAYS_PER_LEVEL - remaining
            
            pbar = QProgressBar()
            pbar.setRange(0, config.PLAYS_PER_LEVEL)
            pbar.setValue(progress_val)
            pbar.setTextVisible(True)
            pbar.setFormat(f"{remaining} left")
            pbar.setAlignment(Qt.AlignCenter)
            pbar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #bbbbbb;
                    border-radius: 4px;
                    background-color: #f3f3f3;
                    text-align: center;
                    color: black;
                }
                QProgressBar::chunk {
                    background-color: #4CAF50;
                    border-radius: 3px;
                }
            """)
                
            items[-1].setBackground(QBrush(self.get_tier_color(tier_str)))
                
            for col, item in enumerate(items):
                self.table.setItem(row, col, item)
                if col == 3:
                    self.table.setCellWidget(row, col, pbar)

def run():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Load and apply window icon if exists
    icon_path = Path("KovaaksTrackerLogo.ico")
    if not icon_path.exists():
        icon_path = Path("assets/KovaaksTrackerLogo.ico")
        
    if icon_path.exists():
        app_icon = QIcon(str(icon_path))
        app.setWindowIcon(app_icon)
    else:
        logging.info("Logo image not found. Expected 'KovaaksTrackerLogo.ico' in root or 'assets' folder.")
    
    database.init_db()
    window = MainWindow()
    if icon_path.exists():
        window.setWindowIcon(app_icon)
        
    window.show()
    sys.exit(app.exec())
