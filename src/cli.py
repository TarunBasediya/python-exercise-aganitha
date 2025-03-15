import typer
import pandas as pd
from rich.console import Console
from rich.table import Table
from src.fetch_papers import get_research_papers

app = typer.Typer()
console = Console()


@app.command()
def fetch(
    query: str,
    max_results: int = 10,
    save_csv: str = None
):
    """
    Fetches research papers from PubMed and displays them in the terminal.

    Args:
        query (str): Search term for PubMed.
        max_results (int): Number of papers to retrieve.
        save_csv (str, optional): Filename to save the results in CSV format.
    """
    console.print(f"\n[bold green]Fetching research papers for:[/bold green] {query}")
    
    df = get_research_papers(query, max_results)

    if df.empty:
        console.print("[bold red]No results found.[/bold red]")
        return

    # Display results in a rich table
    table = Table(title="Research Papers with Non-Academic Authors")

    for col in df.columns:
        table.add_column(col, justify="left")

    for _, row in df.iterrows():
        table.add_row(*row.astype(str).tolist())

    console.print(table)

    # Save to CSV if requested
    if save_csv:
        df.to_csv(save_csv, index=False)
        console.print(f"\n[bold blue]Results saved to {save_csv}[/bold blue]")


if __name__ == "__main__":
    app()
