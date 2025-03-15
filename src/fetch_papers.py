import requests
import pandas as pd
from typing import List, Dict, Optional
from rich.console import Console

console = Console()

# PubMed API Base URL
PUBMED_API_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
DETAILS_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

def fetch_paper_ids(query: str, max_results: int = 10) -> List[str]:
    """
    Fetches PubMed paper IDs based on a search query.

    Args:
        query (str): The search query string.
        max_results (int): Maximum number of results to retrieve.

    Returns:
        List[str]: List of PubMed IDs.
    """
    url = f"{PUBMED_API_BASE}esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json"
    }

    response = requests.get(url, params=params)
    data = response.json()

    return data.get("esearchresult", {}).get("idlist", [])


def fetch_paper_details(paper_id: str) -> Optional[Dict]:
    """
    Fetches details of a PubMed paper using its ID.

    Args:
        paper_id (str): The PubMed ID of the paper.

    Returns:
        Dict: Paper details (Title, Authors, Affiliations, etc.), or None if error.
    """
    url = f"{PUBMED_API_BASE}esummary.fcgi"
    params = {
        "db": "pubmed",
        "id": paper_id,
        "retmode": "json"
    }

    response = requests.get(url, params=params)
    data = response.json()

    if "result" in data and paper_id in data["result"]:
        return data["result"][paper_id]
    
    return None


def identify_non_academic_authors(authors: List[Dict]) -> List[Dict]:
    """
    Filters authors who are affiliated with pharmaceutical or biotech companies.

    Args:
        authors (List[Dict]): List of authors with their affiliations.

    Returns:
        List[Dict]: Authors with non-academic affiliations.
    """
    company_keywords = ["Pharma", "Biotech", "Therapeutics", "Inc", "Ltd", "Corporation", "GmbH"]
    
    non_academic_authors = []

    for author in authors:
        affiliation = author.get("affiliation", "")
        
        if any(keyword in affiliation for keyword in company_keywords):
            non_academic_authors.append(author)

    return non_academic_authors


def get_research_papers(query: str, max_results: int = 10) -> pd.DataFrame:
    """
    Fetches research papers from PubMed based on the given query.

    Args:
        query (str): The search term.
        max_results (int): Maximum number of results to fetch.

    Returns:
        pd.DataFrame: A DataFrame containing research paper details.
    """
    try:
        console.print(f"[bold yellow]Querying PubMed API for:[/bold yellow] {query}")

        # Fetch paper IDs
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json"
        }
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()  # Raise an error for HTTP issues
        data = response.json()

        if "esearchresult" not in data or "idlist" not in data["esearchresult"]:
            console.print("[bold red]Error: No results found![/bold red]")
            return pd.DataFrame()

        pubmed_ids = data["esearchresult"]["idlist"]

        if not pubmed_ids:
            console.print("[bold red]No papers found for this query.[/bold red]")
            return pd.DataFrame()

        # Fetch details for each paper
        params = {
            "db": "pubmed",
            "id": ",".join(pubmed_ids),
            "retmode": "json"
        }
        details_response = requests.get(DETAILS_URL, params=params)
        details_response.raise_for_status()
        details_data = details_response.json()

        if "result" not in details_data:
            console.print("[bold red]API Error: No paper details found.[/bold red]")
            return pd.DataFrame()

        results = details_data["result"]

        # Process results
        papers = []
        for pubmed_id in pubmed_ids:
            paper_data = results.get(pubmed_id, {})
            title = paper_data.get("title", "N/A")
            pub_date = paper_data.get("pubdate", "Unknown Date")

            # Placeholder company identification logic
            company_name = "ABC Pharma Inc" if "cancer" in title.lower() else "N/A"
            author_name = paper_data.get("sortfirstauthor", "Unknown Author")

            papers.append([pubmed_id, title, pub_date, author_name, company_name, "Not Available"])

        # Create DataFrame
        df = pd.DataFrame(papers, columns=["PubmedID", "Title", "Publication Date", "Non-academic Author(s)", "Company Affiliation(s)", "Corresponding Author Email"])
        return df

    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Network error:[/bold red] {e}")
        return pd.DataFrame()

    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        return pd.DataFrame()
