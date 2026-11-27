"""Build structured funding catalog from authored Funding DK (DE missing).md.

Generates data/funding/seed_funding_catalog.json and updates config/funding-sources.json
with reviewed official providers and domains for automated collection and verification.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT / "research/funding-de-eu/Funding DK (DE missing).md"
OUTPUT_CATALOG = ROOT / "data/funding/seed_funding_catalog.json"
SOURCES_PATH = ROOT / "config/funding-sources.json"

#: Known official domains and canonical URLs for funding providers identified in the seed.
OFFICIAL_PROVIDERS_REGISTRY = {
    "innovationsfonden-innofounder": {
        "provider": "Innovation Fund Denmark",
        "program": "Innofounder",
        "official_domains": ["innovationsfonden.dk"],
        "url": "https://innovationsfonden.dk/en/p/innofounder",
        "country": "DK",
    },
    "innovationsfonden-innobooster": {
        "provider": "Innovation Fund Denmark",
        "program": "Innobooster",
        "official_domains": ["innovationsfonden.dk"],
        "url": "https://innovationsfonden.dk/en/p/innobooster",
        "country": "DK",
    },
    "heyfunding-grant": {
        "provider": "Heyfunding",
        "program": "Heyfunding Grant",
        "official_domains": ["heyfunding.dk"],
        "url": "https://heyfunding.dk/grant",
        "country": "DK",
    },
    "danmark-mudp": {
        "provider": "MUDP",
        "program": "Miljoeteknologisk Udviklings- og Demonstrationsprogram",
        "official_domains": ["mudp.dk", "mst.dk"],
        "url": "https://mudp.dk/",
        "country": "DK",
    },
    "velliv-foreningen": {
        "provider": "Velliv Foreningen",
        "program": "Mental Health and Workplace Wellbeing Grant",
        "official_domains": ["vellivforeningen.dk"],
        "url": "https://www.vellivforeningen.dk/",
        "country": "DK",
    },
    "danmark-virksomhedsprogrammet": {
        "provider": "Virksomhedsprogrammet",
        "program": "SMV:Groen og Baeredygtig",
        "official_domains": ["virksomhedsprogrammet.dk", "erhvervshusmidtjylland.dk"],
        "url": "https://virksomhedsprogrammet.dk/",
        "country": "DK",
    },
    "ufm-euopstart": {
        "provider": "UFM",
        "program": "EUopSTART",
        "official_domains": ["ufm.dk"],
        "url": "https://ufm.dk/forskning-og-innovation/tilskud-til-forskning-og-innovation/find-danske-tilskudsprogrammer/euopstart",
        "country": "DK",
    },
    "eu-eic-accelerator": {
        "provider": "EU",
        "program": "EIC-Accelerator",
        "official_domains": ["eic.ec.europa.eu", "ec.europa.eu"],
        "url": "https://eic.ec.europa.eu/eic-funding-opportunities/eic-accelerator_en",
        "country": "EU",
    },
    "otto-moensted-bright-idea": {
        "provider": "Otto Moensted Foundation",
        "program": "The Bright Idea Award",
        "official_domains": ["omfonden.dk"],
        "url": "https://omfonden.dk/ansoegning/",
        "country": "DK",
    },
    "dinero-ivaerksaetterlegat": {
        "provider": "Dinero",
        "program": "Ivaerksaetterlegat",
        "official_domains": ["dinero.dk"],
        "url": "https://dinero.dk/legat/",
        "country": "DK",
    },
    "ffe-mikrolegat": {
        "provider": "Fonden for Entreprenoerskab",
        "program": "Mikrolegat",
        "official_domains": ["mikrolegat.dk", "ffe-ye.dk"],
        "url": "https://mikrolegat.dk/",
        "country": "DK",
    },
    "eureka-network-program": {
        "provider": "Eureka Network",
        "program": "Eureka R&D Software & Tech",
        "official_domains": ["eurekanetwork.org"],
        "url": "https://www.eurekanetwork.org/",
        "country": "EU",
    },
    "norlys-vaekstpulje": {
        "provider": "Norlys",
        "program": "Vaekstpulje",
        "official_domains": ["norlys.dk"],
        "url": "https://norlys.dk/om-norlys/vaekstpulje/",
        "country": "DK",
    },
    "danmark-gudp": {
        "provider": "GUDP",
        "program": "Groent Udviklings- og Demonstrationsprogram",
        "official_domains": ["lbst.dk", "gudp.dk"],
        "url": "https://lbst.dk/tilskud-selvbetjening/tilskudsguide/groent-udviklings-og-demonstrationsprogram-gudp/",
        "country": "DK",
    },
    "avant-now-accelerator": {
        "provider": "Avant Now",
        "program": "Avant Now Accelerator",
        "official_domains": ["avant-now.com"],
        "url": "https://www.avant-now.com/",
        "country": "DE",
    },
    "htgf-seed-investment": {
        "provider": "High-Tech Gruenderfonds",
        "program": "HTGF Seed Investment",
        "official_domains": ["htgf.de"],
        "url": "https://www.htgf.de/en/founders/pitchdeck-upload/",
        "country": "DE",
    },
    "reaktor-berlin-private": {
        "provider": "Reaktor Berlin",
        "program": "Private Accelerator Program",
        "official_domains": ["reaktor.berlin"],
        "url": "https://reaktor.berlin/private-program/",
        "country": "DE",
    },
    "bii-venture-lab": {
        "provider": "BioInnovation Institute",
        "program": "BII Venture Lab",
        "official_domains": ["bii.dk"],
        "url": "https://bii.dk/programs/venturelab/",
        "country": "DK",
    },
    "unternehmertum-xpreneurs": {
        "provider": "UnternehmerTUM",
        "program": "XPRENEURS Incubator",
        "official_domains": ["unternehmertum.de"],
        "url": "https://www.unternehmertum.de/en",
        "country": "DE",
    },
    "vision-health-pioneers": {
        "provider": "Vision Health Pioneers",
        "program": "Healthcare Incubator Fellowship",
        "official_domains": ["visionhealthpioneers.de"],
        "url": "https://visionhealthpioneers.de/",
        "country": "DE",
    },
    "spinlab-accelerator": {
        "provider": "SpinLab",
        "program": "Smart City & eHealth Accelerator",
        "official_domains": ["spinlab.co"],
        "url": "https://spinlab.co/",
        "country": "DE",
    },
    "ibb-investitionsbonus": {
        "provider": "IBB Business Team",
        "program": "Berliner InvestitionsBONUS",
        "official_domains": ["ibb-business-team.de"],
        "url": "https://www.ibb-business-team.de/en/berliner-investitionsbonus/",
        "country": "DE",
    },
    "dtcf-deeptech-climate": {
        "provider": "DeepTech & Climate Fonds",
        "program": "DTCF Growth Investment",
        "official_domains": ["dtcf.de"],
        "url": "https://dtcf.de/",
        "country": "DE",
    },
    "exist-gruenderstipendium": {
        "provider": "BMWK",
        "program": "EXIST-Gruenderstipendium",
        "official_domains": ["exist.de"],
        "url": "https://www.exist.de/",
        "country": "DE",
    },
    "mikromezzanin-deutschland": {
        "provider": "Mikromezzaninfonds Deutschland",
        "program": "Mikromezzaninfonds",
        "official_domains": ["mikromezzaninfonds-deutschland.de"],
        "url": "https://www.mikromezzaninfonds-deutschland.de/start.html#programm",
        "country": "DE",
    },
    "ilb-gruendung-innovativ": {
        "provider": "ILB",
        "program": "Gruendung Innovativ",
        "official_domains": ["ilb.de"],
        "url": "https://www.ilb.de/de/wirtschaft/zuschuesse/gruendung-innovativ-2022/",
        "country": "DE",
    },
    "ibb-gruendungsbonus-plus": {
        "provider": "IBB",
        "program": "GruendungsBONUS Plus",
        "official_domains": ["ibb.de", "ibb-business-team.de"],
        "url": "https://www.ibb.de/de/foerderprogramme/gruendungsbonus-plus.html",
        "country": "DE",
    },
    "ibb-pro-fit-fruehphase": {
        "provider": "IBB",
        "program": "Pro FIT Fruehphasenfinanzierung",
        "official_domains": ["ibb.de"],
        "url": "https://www.ibb.de/de/foerderprogramme/pro-fit-fruehphasenfinanzierung.html",
        "country": "DE",
    },
    "kfw-erp-startgeld": {
        "provider": "KfW",
        "program": "ERP-StartGeld",
        "official_domains": ["kfw.de"],
        "url": "https://www.kfw.de/inlandsfoerderung/Unternehmen/Gr%C3%BCnden-Nachfolgen/F%C3%B6rderprodukte/ERP-Gr%C3%BCnderkredit-Startgeld-(067)/",
        "country": "DE",
    },
    "dbu-green-start-up": {
        "provider": "DBU",
        "program": "Green Start-up",
        "official_domains": ["dbu.de"],
        "url": "https://www.dbu.de/foerderung/green-start-up/",
        "country": "DE",
    },
    "berliner-startup-stipendium": {
        "provider": "IBB",
        "program": "Berliner Startup-Stipendium",
        "official_domains": ["ibb.de", "berlin.de"],
        "url": "https://www.ibb.de/de/foerderprogramme/berliner-startup-stipendium.html",
        "country": "DE",
    },
    "ibb-pronti": {
        "provider": "IBB Business Team",
        "program": "ProNTI Nichttechnische Innovationen",
        "official_domains": ["ibb-business-team.de"],
        "url": "https://www.ibb-business-team.de/pronti/",
        "country": "DE",
    },
    "kmu-innovativ-bmbf": {
        "provider": "BMBF",
        "program": "KMU-innovativ",
        "official_domains": ["kmu-innovativ.de", "bmbf.de"],
        "url": "https://www.kmu-innovativ.de/",
        "country": "DE",
    },
    "bpw-berlin-brandenburg": {
        "provider": "BPW",
        "program": "Businessplan-Wettbewerb Berlin-Brandenburg",
        "official_domains": ["b-p-w.de"],
        "url": "https://www.b-p-w.de/",
        "country": "DE",
    },
}


def build_catalog() -> list[dict]:
    content = SEED_PATH.read_text(encoding="utf-8")
    lines = content.splitlines()

    url_re = re.compile(r"https?://[^\s\)\]\"\'\<\>]+")
    items = []
    current_section = "DK Soft Funding"

    for idx, raw_line in enumerate(lines, 1):
        stripped = raw_line.strip()
        if "Soft Funding DK" in stripped:
            current_section = "DK Soft Funding"
        elif "Incubators" in stripped:
            current_section = "Incubators"
        elif "Soft-Funding EU" in stripped:
            current_section = "EU/DE Soft Funding"
        elif "Hard Fund" in stripped:
            current_section = "DE Hard Funding"
        elif "VC" in stripped and "#" in stripped:
            current_section = "VC & Angel"

        if (
            "|" in stripped
            and not stripped.startswith("| :--")
            and not stripped.startswith("| VC")
            and not stripped.startswith("| Name")
            and not stripped.startswith("| VC Fonds")
        ):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if not cells or not any(cells):
                continue

            raw_name = cells[0]
            clean_name = re.sub(r"\*+", "", raw_name).strip()
            clean_name = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean_name).strip()
            clean_name = (
                clean_name.replace(r"https\://", "https://")
                .replace(r"http\://", "http://")
                .replace(r"\+", "+")
                .replace(r"\!", "!")
            )
            if not clean_name or len(clean_name) < 2 or clean_name.startswith("---"):
                continue

            norm_text = (
                " ".join(cells)
                .replace(r"https\://", "https://")
                .replace(r"http\://", "http://")
                .replace(r"\_", "_")
                .replace(r"\-", "-")
            )
            urls = url_re.findall(norm_text)
            cleaned_urls = []
            for u in urls:
                c = u.rstrip(".,;:)").split("?utm_source")[0].split("?etcc")[0]
                if c not in cleaned_urls:
                    cleaned_urls.append(c)

            deadline = cells[1] if len(cells) > 1 else ""
            fields = cells[2] if len(cells) > 2 else ""
            requirements = cells[3] if len(cells) > 3 else ""
            output_desc = cells[4] if len(cells) > 4 else ""

            # Attempt matching to approved registry entry
            matched_key = None
            clean_lower = clean_name.casefold()
            for key, meta in OFFICIAL_PROVIDERS_REGISTRY.items():
                prog_lower = meta["program"].casefold()
                prov_lower = meta["provider"].casefold()
                if prog_lower in clean_lower or clean_lower in prog_lower or (key in clean_lower):
                    matched_key = key
                    break

            reg_meta = OFFICIAL_PROVIDERS_REGISTRY.get(matched_key, {})
            primary_url = reg_meta.get("url") or (cleaned_urls[0] if cleaned_urls else None)
            official_domains = reg_meta.get("official_domains") or (
                [urlsplit(primary_url).netloc.replace("www.", "")] if primary_url else []
            )

            slug = matched_key or re.sub(r"[^a-z0-9]+", "-", clean_name.lower()).strip("-")[:40]

            item = {
                "opportunity_id": slug,
                "seed_line": idx,
                "section": current_section,
                "raw_name": clean_name,
                "provider": reg_meta.get("provider", clean_name.split()[0] if clean_name else "Unknown"),
                "program": reg_meta.get("program", clean_name),
                "official_domains": official_domains,
                "url": primary_url,
                "extracted_urls": cleaned_urls,
                "deadline_hint": deadline[:200],
                "fields_hint": fields[:200],
                "requirements_hint": requirements[:300],
                "output_hint": output_desc[:300],
                "country": reg_meta.get("country", "DK" if "DK" in current_section else "DE"),
            }
            items.append(item)

    return items


def main():
    catalog = build_catalog()
    OUTPUT_CATALOG.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_CATALOG.write_text(json.dumps({"schema_version": "1.0", "items": catalog}, indent=2, ensure_ascii=False))
    print(f"Wrote {len(catalog)} structured funding records to {OUTPUT_CATALOG}")

    # Build updated config/funding-sources.json
    existing_data = json.loads(SOURCES_PATH.read_text(encoding="utf-8")) if SOURCES_PATH.exists() else {"schema_version": "1.0", "sources": []}
    sources_by_id = {s["opportunity_id"]: s for s in existing_data.get("sources", [])}

    for item in catalog:
        opp_id = item["opportunity_id"]
        url = item.get("url")
        domains = item.get("official_domains", [])
        if opp_id and url and domains and url.startswith("https://"):
            sources_by_id[opp_id] = {
                "opportunity_id": opp_id,
                "provider": item["provider"],
                "program": item["program"],
                "official_domains": domains,
                "url": url,
            }

    updated_sources = list(sources_by_id.values())
    updated_sources.sort(key=lambda s: s["opportunity_id"])
    updated_data = {"schema_version": "1.0", "sources": updated_sources}
    SOURCES_PATH.write_text(json.dumps(updated_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Updated {SOURCES_PATH} with {len(updated_sources)} reviewed sources (was {len(existing_data.get('sources', []))}).")


if __name__ == "__main__":
    main()
