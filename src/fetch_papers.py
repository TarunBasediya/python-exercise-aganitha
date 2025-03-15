import requests
import pandas as pd
from typing import List, Dict, Optional
from rich.console import Console

console = Console()

# PubMed API URLs
PUBMED_API_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

# Keywords for affiliation classification
ACADEMIC_KEYWORDS = ["university", "college", "institute", "hospital", "school", "research center"]
COMPANY_KEYWORDS = ["Pharma", "Biotech", "Therapeutics", "Inc", "Ltd", "Corporation", "GmbH"]

def is_academic_affiliation(affiliation: str) -> bool:
    """Check if the affiliation belongs to an academic institution."""
    return any(keyword in affiliation.lower() for keyword in ACADEMIC_KEYWORDS)

def is_non_academic_affiliation(affiliation: str) -> bool:
    """Check if the affiliation belongs to a pharmaceutical or biotech company."""
    return any(keyword in affiliation for keyword in COMPANY_KEYWORDS)

def fetch_paper_ids(query: str, max_results: int = 10) -> List[str]:
    """Fetches PubMed paper IDs based on a search query."""
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
    """Fetches details of a PubMed paper, including full author affiliations."""
    url = f"{PUBMED_API_BASE}efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": paper_id,
        "retmode": "xml"
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        console.print(f"[bold red]Failed to fetch details for PubMed ID {paper_id}[/bold red]")
        return None

    xml_data = response.text

    # Extract relevant fields (Title, Date, Authors, Affiliations)
    from xml.etree import ElementTree as ET
    root = ET.fromstring(xml_data)

    title = root.find(".//ArticleTitle")
    title = title.text if title is not None else "N/A"

    pub_date = root.find(".//PubDate/Year")
    pub_date = pub_date.text if pub_date is not None else "Unknown Date"

    authors = []
    affiliations = []

    for author in root.findall(".//Author"):
        last_name = author.find("LastName")
        fore_name = author.find("ForeName")
        full_name = f"{fore_name.text} {last_name.text}" if last_name is not None and fore_name is not None else "Unknown Author"

        affiliation_tag = author.find(".//Affiliation")
        affiliation = affiliation_tag.text if affiliation_tag is not None else "N/A"

        authors.append({"name": full_name, "affiliation": affiliation})
        affiliations.append(affiliation)

    return {
        "title": title,
        "pub_date": pub_date,
        "authors": authors,
        "affiliations": affiliations
    }

def identify_non_academic_authors(authors: List[Dict]) -> List[Dict]:
    """Filters authors who are affiliated with pharmaceutical or biotech companies."""
    non_academic_authors = []

    for author in authors:
        affiliation = author.get("affiliation", "")

        if is_non_academic_affiliation(affiliation):
            non_academic_authors.append(author)

    return non_academic_authors

def get_research_papers(query: str, max_results: int = 10) -> pd.DataFrame:
    """
    Fetches research papers from PubMed based on the given query.

    Returns a DataFrame with:
    - PubmedID
    - Title
    - Publication Date
    - Non-academic Author(s)
    - Company Affiliation(s)
    - Corresponding Author Email (if available)
    """
    try:
        console.print(f"[bold yellow]Querying PubMed API for:[/bold yellow] {query}")

        # Fetch paper IDs
        pubmed_ids = fetch_paper_ids(query, max_results)
        if not pubmed_ids:
            console.print("[bold red]No papers found for this query.[/bold red]")
            return pd.DataFrame()

        # Fetch details for each paper
        papers = []
        for pubmed_id in pubmed_ids:
            paper_data = fetch_paper_details(pubmed_id)
            if not paper_data:
                continue

            title = paper_data["title"]
            pub_date = paper_data["pub_date"]
            authors = paper_data["authors"]
            
            # Identify non-academic authors
            non_academic_authors = identify_non_academic_authors(authors)

            # Extract company names from affiliations
            company_affiliations = [author["affiliation"] for author in non_academic_authors]

            # Filter out academic-only papers
            if not non_academic_authors:
                continue

            papers.append([
                pubmed_id, 
                title, 
                pub_date, 
                ", ".join([author["name"] for author in non_academic_authors]),
                ", ".join(company_affiliations),
                "Not Available"  # Placeholder for Corresponding Author Email
            ])

        # Create DataFrame
        df = pd.DataFrame(papers, columns=["PubmedID", "Title", "Publication Date", "Non-academic Author(s)", "Company Affiliation(s)", "Corresponding Author Email"])

        if df.empty:
            console.print("[bold red]No papers with non-academic authors found.[/bold red]")
        else:
            console.print("[bold green]✅ Papers with pharmaceutical company affiliations are included.[/bold green]")
            console.print("[bold red]❌ Papers with only academic affiliations are excluded.[/bold red]")

        return df

    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Network error:[/bold red] {e}")
        return pd.DataFrame()

    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        return pd.DataFrame()
