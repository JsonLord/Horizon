---
layout: default
title: "Funding Opportunities: Denmark, Germany & EU (83 Programs & 27 Official Registers)"
date: 2026-11-27
lang: en
branch: feature/funding-dk-de-opportunities
category: funding
tags: [funding, grants, eu, denmark, germany, startups]
---

# Funding Opportunities: Denmark, Germany & EU

*Branch source: `feature/funding-dk-de-opportunities` · Monitored via Horizon Funding Pipeline*

## Executive Summary

Horizon has parsed, structured, and validated **83 discrete funding programs** from the primary starting document (`research/funding-de-eu/Funding DK (DE missing).md`), creating a clean machine-readable catalog at `data/funding/seed_funding_catalog.json` and registering **27 confirmed official HTTPS entrypoints** with verified ownership in `config/funding-sources.json`.

All program terms obey strict evidentiary verification rules: applicant eligibility is tracked independently of open/closed status, and facts require primary citation from official domains (`innovationsfonden.dk`, `bmbf.de`, `kfw.de`, `ibb.de`, `eic.ec.europa.eu`).

---

## Key Active Programs & Funding Streams

### 1. Denmark Soft Funding (`DK`)
- **Innovation Fund Denmark — Innofounder**:
  - *Focus*: Early-stage innovative software, health tech, bio-agriculture, and consumer solutions.
  - *Support*: Monthly salary financing (~DKK 30,000/month) + development grant up to 12 months.
  - *Hard Condition*: Danish CVR registration required; market validation data needed before application.
  - *URL*: [innovationsfonden.dk/en/p/innofounder](https://innovationsfonden.dk/en/p/innofounder)
- **Innovation Fund Denmark — Innobooster**:
  - *Focus*: Market-maturing products, processes, or services with substantial economic/societal upside.
  - *Support*: Co-funding grants between DKK 50,000 and DKK 5,000,000 (up to 2-year project duration).
  - *URL*: [innovationsfonden.dk/en/p/innobooster](https://innovationsfonden.dk/en/p/innobooster)
- **Fonden for Entreprenørskab — Mikrolegat**:
  - *Focus*: Higher-education student founders and early spin-outs.
  - *Support*: Non-dilutive micro-grants up to DKK 50,000.
  - *URL*: [mikrolegat.dk](https://mikrolegat.dk/)
- **BioInnovation Institute — BII Venture Lab**:
  - *Focus*: Deep-tech life sciences, bio-industrial, and health innovations.
  - *Support*: Up to €500,000 convertible loan + incubation at Copenhagen labs.
  - *URL*: [bii.dk/programs/venturelab/](https://bii.dk/programs/venturelab/)

### 2. Germany & Berlin Programs (`DE` / `Berlin`)
- **IBB GründungsBONUS Plus (Berlin)**:
  - *Focus*: Innovative, technology-driven or sustainability-oriented Berlin startups within first 12 months.
  - *Support*: 50% non-repayable grant up to €50,000 for operating and capital expenditures.
  - *Status*: UNKNOWN / rolling intake; requires registered operating premise (*Betriebsstätte*) in Berlin.
  - *URL*: [ibb.de/de/foerderprogramme/gruendungsbonus-plus.html](https://www.ibb.de/de/foerderprogramme/gruendungsbonus-plus.html)
- **KfW ERP-StartGeld (Federal Germany)**:
  - *Focus*: Full-time or secondary founders, freelancers, and small enterprises up to 5 years after inception.
  - *Support*: Low-interest loans up to €125,000 with 80% KfW indemnity (*Haftungsfreistellung*) for house banks.
  - *URL*: [kfw.de ERP-Gründerkredit](https://www.kfw.de/inlandsfoerderung/Unternehmen/Gr%C3%BCnden-Nachfolgen/F%C3%B6rderprodukte/ERP-Gr%C3%BCnderkredit-Startgeld-(067)/)
- **BMBF KMU-innovativ**:
  - *Focus*: Cutting-edge industrial research and experimental development for SMEs in software, AI, and electronics.
  - *Support*: High non-repayable grant share (up to 50% for commercial partners, 100% for participating universities).
  - *URL*: [kmu-innovativ.de](https://www.kmu-innovativ.de/)
- **Mikromezzaninfonds Deutschland**:
  - *Focus*: Small and micro-enterprises with sound business models but insufficient bank collateral.
  - *Support*: Dormant equity capital (*stille Beteiligung*) up to €50,000 without tangible asset collateral.
  - *URL*: [mikromezzaninfonds-deutschland.de](https://www.mikromezzaninfonds-deutschland.de/start.html)

### 3. European Union Level (`EU`)
- **EIC Accelerator (European Innovation Council)**:
  - *Focus*: Breakthrough deep-tech scale-ups with high-risk, high-impact technologies.
  - *Support*: Blended finance combining non-dilutive grant up to €2,500,000 and direct equity up to €15,000,000.
  - *Cut-offs*: Short proposal evaluation runs continuously on a rolling basis; full proposals evaluated at scheduled 2026/2027 deadlines.
  - *URL*: [eic.ec.europa.eu](https://eic.ec.europa.eu/eic-funding-opportunities/eic-accelerator_en)
- **Eureka Network**:
  - *Focus*: Market-driven international R&D partnerships across 45+ member countries.
  - *URL*: [eurekanetwork.org](https://www.eurekanetwork.org/)

---

## Seed Queue Status

- **Structured catalog programs:** 83
- **Registered official HTTPS URLs:** 27
- **Candidate queue:** 100 entries (`index --check` valid, 0 queue drift)
- **Baseline qualification slice:** Verified deterministic preservation of `ibb-gruendungsbonus-plus`, `kfw-erp-startgeld`, and `eu-eic-accelerator`.
