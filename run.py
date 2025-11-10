# run.py

from rich.console import Console
console = Console()

from screener import get_dividend_harvest
from datetime import datetime
import os
import sys
from pathlib import Path

# Constants
EXPORTS_DIR = "exports"
TOP_N_DISPLAY = 10
DISPLAY_COLS = ['code', 'name', 'dividend_yield', 'days_until_exdiv', 'close']


def main() -> int:
    """Main execution - returns exit code (0 = success, 1 = error)"""
    try:
        # Fetch data
        console.print("[bold green]🚀 Starting dividend harvest...[/bold green]")
        df = get_dividend_harvest()
        
        # Validate we got data
        if df.empty:
            console.print("[bold yellow]⚠️  No stocks found matching criteria[/bold yellow]")
            return 1
        
        # Create exports directory
        exports_path = Path(EXPORTS_DIR)
        exports_path.mkdir(exist_ok=True)
        
        # Generate filename
        filename = exports_path / f"DIVIDEND_HARVEST_{datetime.now():%Y-%m-%d}.csv"
        
        # Save to CSV
        df.to_csv(filename, index=False)
        
        # Also save latest data for Hugging Face app (JSON format)
        data_path = Path("data")
        data_path.mkdir(exist_ok=True)
        latest_file = data_path / "latest.json"
        df.to_json(latest_file, orient="records", date_format="iso")
        
        # Verify file was created
        if not filename.exists():
            console.print(f"[bold red]❌ Error: File was not created: {filename}[/bold red]")
            return 1
        
        # Success message
        file_size = filename.stat().st_size / 1024  # KB
        console.print(f"\n[bold cyan]🎯 SAVED {len(df)} stocks → {filename}[/bold cyan]")
        console.print(f"   File size: {file_size:.1f} KB")
        
        # Display top stocks (with column validation)
        available_cols = [col for col in DISPLAY_COLS if col in df.columns]
        if available_cols:
            console.print(f"\n[bold blue]📊 Top {TOP_N_DISPLAY} bangers:[/bold blue]")
            console.print("[bold red]═[/bold red]" * 80)
            console.print(df.head(TOP_N_DISPLAY)[available_cols].to_string(index=False))
        else:
            console.print(f"\n[bold blue]📊 Top {TOP_N_DISPLAY} stocks (all columns):[/bold blue]")
            console.print("[bold red]═[/bold red]" * 80)
            console.print(df.head(TOP_N_DISPLAY).to_string(index=False))
        
        return 0
        
    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠️  Interrupted by user[/bold yellow]")
        return 130
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {e}[/bold red]")
        console.print(f"   Type: {type(e).__name__}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
