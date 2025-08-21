from rich.console import Console
from rich.table import Table
from datetime import datetime
from rich.columns import Columns
from rich.panel import Panel
from rich.align import Align
from rich import box
from core.logger import logger
from core.config_loader import scanner_config

console = Console()

class DisplayManager:
    def display_results(self, assets_config, asset_data, current_prices={}):
        if not assets_config:
            logger.info("No assets to display.")
            return

        #console.clear()

        desired_column_order = [col["name"] for col in scanner_config["columns"]]
        num_tables = scanner_config.get("screen", {}).get("table", 1)
        asset_names = assets_config
        num_assets = len(asset_names)
        assets_per_table = (num_assets + num_tables - 1) // num_tables

        tables = []

        for i in range(num_tables):
            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column("Asset", style="bold")
            for col_name in desired_column_order:
                table.add_column(col_name, justify="center")
            tables.append(table)

        for i, asset in enumerate(asset_names):
            table_index = i % num_tables
            row = [asset.removesuffix('USDT')]
            for col_name in desired_column_order:
                if asset in asset_data and col_name in asset_data[asset]:
                    data = asset_data[asset][col_name]
                    percentage = data.get("percentage")
                    if percentage is not None:
                        percentage_display = float(percentage) * -1 if percentage < '0' else percentage #remove the sign as its coloured now
                        cell_content = f"{percentage_display}%"
                    else:
                        percentage_display = percentage
                        cell_content = "-"

                    styled_content = cell_content
                    try:
                        if percentage is not None:
                            percentage_float = float(percentage)
                            threshold = next((col["threshold"] for col in scanner_config["columns"] if col["name"] == col_name), None)
                            threshold2 = next((col["threshold2"] for col in scanner_config["columns"] if col["name"] == col_name), None)
                            if threshold is not None:
                                if percentage_float > 0:
                                    styled_content = f"[green]{styled_content}[/green]"
                                elif percentage_float < 0:
                                    styled_content = f"[red]{styled_content}[/red]"
                                if threshold2 is not None and abs(percentage_float) >= threshold2 and abs(percentage_float) < threshold:
                                    styled_content = f"[on honeydew2]{styled_content}[/on honeydew2]" if percentage_float > 0 else f"[on cornsilk1]{styled_content}[/on cornsilk1]"
                                if abs(percentage_float) >= threshold:
                                    styled_content = f"[on dark_sea_green3]{styled_content}[/on dark_sea_green3]" if percentage_float > 0 else f"[on light_pink1]{styled_content}[/on light_pink1]"
                    except (ValueError, TypeError):  # Correctly indented
                        pass  # Correctly indented
                    aligned_content = Align(styled_content, align="center")
                    row.append(aligned_content)
                else:
                    row.append("-")
            tables[table_index].add_row(*row)

        columns = Columns([Panel(table, padding=(0, 0), box=box.SIMPLE_HEAD) for table in tables], equal=True, expand=True, padding=(0, 0))
        console.print(columns)