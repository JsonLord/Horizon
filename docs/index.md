---
layout: default
title: Home | Horizon Daily
---

# Horizon Daily Intelligence

Welcome to [Horizon](https://github.com/JsonLord/Horizon), an AI-driven multi-stream intelligence aggregation system monitoring European state conflicts, founder grant programs, and structured funding opportunities with strict evidentiary quality gates.

---

## 📡 Active Multi-Branch Intelligence (7-Day Rolling Digest)

*Data published across specialized research branches, updated weekly and aggregated additively.*

<div class="intelligence-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin: 20px 0;">

  <div style="border: 1px solid #e1e4e8; border-radius: 8px; padding: 16px; background: #fafbfc;">
    <h3 style="margin-top: 0;">🇪🇺 European Conflicts & AA</h3>
    <p style="font-size: 0.9em; color: #586069;"><strong>Branch:</strong> <code>feature/news-european-conflicts-auswaertiges-amt</code></p>
    <p>Monitoring European state-level geopolitical tensions, Baltic/North Sea critical undersea infrastructure alerts, Eastern European border deterrence, and official <strong>Auswärtiges Amt</strong> statements.</p>
    <p><a href="{{ '/news/2026/11/27/european-conflicts-and-auswaertiges-amt.html' | relative_url }}" style="font-weight: bold;">Read Foreign Policy Briefing &rarr;</a></p>
  </div>

  <div style="border: 1px solid #e1e4e8; border-radius: 8px; padding: 16px; background: #fafbfc;">
    <h3 style="margin-top: 0;">🚀 EXIST & BPW Berlin</h3>
    <p style="font-size: 0.9em; color: #586069;"><strong>Branch:</strong> <code>feature/programs-exist-bpw</code></p>
    <p>Founder intelligence tracking <strong>EXIST-Gründerstipendium</strong> (€1k–€3k/mo + €30k material), EXIST-Forschungstransfer Phase I/II, and <strong>BPW Berlin-Brandenburg</strong> 3-phase competition milestones and winning cases.</p>
    <p><a href="{{ '/programs/2026/11/27/exist-and-bpw-founder-intelligence.html' | relative_url }}" style="font-weight: bold;">Read Founder Intelligence &rarr;</a></p>
  </div>

  <div style="border: 1px solid #e1e4e8; border-radius: 8px; padding: 16px; background: #fafbfc;">
    <h3 style="margin-top: 0;">💰 Denmark / Germany / EU Funding</h3>
    <p style="font-size: 0.9em; color: #586069;"><strong>Branch:</strong> <code>feature/funding-dk-de-opportunities</code></p>
    <p>Structured funding catalog of <strong>83 discrete initiatives</strong> and 27 registered official HTTPS sources across Denmark (Innofounder, BII), Germany (IBB GründungsBONUS, KfW StartGeld), and EU (EIC Accelerator).</p>
    <p><a href="{{ '/funding/2026/11/27/funding-opportunities-dk-de-eu.html' | relative_url }}" style="font-weight: bold;">Read Funding Directory &rarr;</a></p>
  </div>

  <div style="border: 1px solid #e1e4e8; border-radius: 8px; padding: 16px; background: #fafbfc;">
    <h3 style="margin-top: 0;">🧠 Two-Stage Benchmark & Gates</h3>
    <p style="font-size: 0.9em; color: #586069;"><strong>Branch:</strong> <code>feat/anti-headline-gate</code></p>
    <p>Evaluation of Horizon's two-stage relevance filtering on 33 held-out benchmark cases: <strong>6/6 gates passed</strong> (100% recall, 100% noise rejection) with Phase 3 anti-headline evidentiary depth enforcement.</p>
    <p><a href="{{ '/research/2026/11/27/two-stage-benchmark-and-anti-headline.html' | relative_url }}" style="font-weight: bold;">Read Benchmark Evaluation &rarr;</a></p>
  </div>

</div>

---

## 📰 Intelligence Feed & Weekly Archive

*All reports from active research branches are retained additively. Items remain active on the rolling weekly roster before archiving.*

<ul>
  {% for post in site.posts limit:30 %}
    <li style="margin-bottom: 8px;">
      <a href="{{ post.url | relative_url }}"><strong>{{ post.title }}</strong></a>
      <span style="font-size: 0.85em; color: #586069;">
        ({{ post.date | date: "%Y-%m-%d" }})
        {% if post.category %} · <code>{{ post.category }}</code>{% endif %}
        {% if post.lang %} · <em>{{ post.lang | upcase }}</em>{% endif %}
      </span>
    </li>
  {% else %}
    <li><em>No posts available</em></li>
  {% endfor %}
</ul>

---

## 📚 Documentation & Technical Specifications

<div id="lang-en" class="lang-section" markdown="1">

- [Configuration Guide](configuration) — AI providers, information sources, filtering, and environment variable substitution
- [Source Scrapers](scrapers) — How Horizon collects content from official government portals, news aggregators, and primary feeds
- [Scoring System](scoring) — Grounded heuristic and model-assisted quality gating scale
- [Agent Research Architecture](agent-research) — Full contract for independent topic branch qualification and reproducible verification

</div>

<div id="lang-zh" class="lang-section" markdown="1" style="margin-top: 20px;">

### 中文文档

- [配置指南](configuration) — AI 提供商、信息源采集器、过滤规则与环境变量配置
- [信息源采集器](scrapers) — Horizon 采集机制与官方信源审计规则
- [评分系统](scoring) — 基于官方证据与两阶段过滤的评分体系

</div>
