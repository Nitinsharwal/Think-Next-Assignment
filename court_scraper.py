import requests
from fpdf import FPDF
from bs4 import BeautifulSoup
import json
import argparse
import datetime
from bs4 import BeautifulSoup
import PyPDF2
from datetime import datetime, timedelta


def fetch_case_details(cnr_number=None, case_type=None, case_number=None, case_year=None):
    url = "https://services.ecourts.gov.in/ecourtindia_v6/?p=cause_list/index&app_token=412c5ecf925890c075e6fd23a9d5a5aac913b94b867bd98bc0ac699a3716ba94#" 
    headers = {"User-Agent": "Mozilla/5.0"} 
    session = requests.Session()

    if cnr_number:
        payload = {"cnrno": cnr_number}
    else:
        payload = {
            "case_type": case_type,
            "case_number": case_number,
            "case_year": case_year
        }

    response = session.post(url, data=payload, headers=headers)
    
    if response.status_code != 200:
        print("No data found")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(soup.prettify())

    print("PDF created successfully!")
    return soup



def extract_case_info_from_pdf(pdf_file, search_term=None):
    with open(pdf_file, "rb") as f:
        text = "".join([page.extract_text() + "\n" for page in PyPDF2.PdfReader(f).pages])

    court_name = text.split("Case Details")[0].strip().split("\n")[0].strip()
    results = []
    for case in text.split("Case Details")[1:]:
        lines = [line.strip() for line in case.split("\n") if line.strip()]
        case_dict = {"Court Name": court_name}
        for line in lines:
            if "Case Type" in line:
                case_dict["Case Type"] = line.split("|")[-1].strip()
            elif "CNR Number" in line:
                case_dict["CNR"] = line.split("|")[1].split("(")[0].strip()
            elif "Next Hearing Date" in line:
                date_str = line.split("|")[-1].strip()
                try:
                    case_dict["Next Hearing Date"] = datetime.strptime(date_str, "%d-%m-%Y")
                except:
                    try:
                        case_dict["Next Hearing Date"] = datetime.strptime(date_str, "%d-%B-%Y")
                    except:
                        case_dict["Next Hearing Date"] = date_str
        if not search_term or search_term.lower() in case_dict.get("CNR", "").lower() or search_term.lower() in case_dict.get("Case Type", "").lower():
            results.append(case_dict)

    today = datetime.today().date()
    tomorrow = today + timedelta(days=1)
    json.dump(results, open("case_search_results.json", "w"), default=str, indent=4)

    for idx, r in enumerate(results, 1):
        for k, v in r.items():
            print(f"{k}: {v}")

    return results


def scrape_and_save_pdf(html_content, output_file="court_cases.pdf"):
    soup = BeautifulSoup(html_content, "html.parser")
    rows = soup.find_all("tr")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for row in rows:
        if row.find("td", colspan=True):
            header_text = row.get_text(strip=True).replace('\xa0', ' ')
            if header_text:
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, header_text, ln=True)
                pdf.set_font("Arial", size=12)
            continue
        cols = row.find_all("td")
        if len(cols) >= 4:
            serial = cols[0].get_text(strip=True)
            case_info = cols[1].get_text(strip=True).replace('\xa0', ' ')
            parties = cols[2].get_text(strip=True).replace('\xa0', ' ')
            advocate = cols[3].get_text(strip=True).replace('\xa0', ' ')
            pdf.multi_cell(0, 8, f"{serial}. {case_info}\nParties: {parties}\nAdvocate: {advocate}")
            pdf.ln(2)
    pdf.output(output_file)
    print(f"PDF saved as {output_file}")


search_term = input("Enter CNR or Case Type to search : ").strip()
fetch_case_details(search_term)
with open("index.html", "r", encoding="utf-8") as f:
    html_content = f.read()
extract_case_info_from_pdf("case_list.pdf", search_term or None)