---
layout: default
title: "Horizon Summary: 2026-07-04 (EN)"
date: 2026-07-04
lang: en
---

> From 174 items, 19 important content pieces were selected

---

1. [Josh W. Comeau reports AI-driven decline in developer course sales](#item-1) ⭐️ 9.0/10
2. [Free Summer Program Helps Students Build Real-World Projects Amid Internship Shortage](#item-2) ⭐️ 9.0/10
3. [Recovering Verbatim Finetuning Data from LLMs via Contrastive Decoding Diffing (CDD)](#item-3) ⭐️ 9.0/10
4. [Huawei Launches Atlas 350 AI Card with Ascend 950PR Processor](#item-4) ⭐️ 9.0/10
5. [China to End Vehicle Tax Exemptions for Certain Electric and Hybrid Vehicles in 2027](#item-5) ⭐️ 9.0/10
6. [GitHub Projects highlighted in tweet encouraging community exploration](#item-6) ⭐️ 9.0/10
7. [SearXNG: Free Open‑Source Metasearch Engine Emphasizing Privacy](#item-7) ⭐️ 8.0/10
8. [Espionage Against the European Parliament](#item-8) ⭐️ 8.0/10
9. [Using TLA+ to Verify dqlite Is Free of a 16‑Year‑Old SQLite WAL Bug](#item-9) ⭐️ 8.0/10
10. [Google Releases Gemini 3.1 Flash Lite Image Model (Nano Banana 2 Lite)](#item-10) ⭐️ 8.0/10
11. [Ornith-1.0 released as MIT-licensed self-scaffolding LLMs for agentic coding.](#item-11) ⭐️ 8.0/10
12. [Meta Pushes to Build Its Own Neocloud and Scale Recommendation Systems](#item-12) ⭐️ 8.0/10
13. [ECTC 2026 Highlights EMIB‑T, Custom HBM, HBM4, Microfluidic Cooling, Photonic Interconnects](#item-13) ⭐️ 8.0/10
14. [NASA Launches Private LINK Spacecraft to Boost Swift Telescope Orbit](#item-14) ⭐️ 8.0/10
15. [Tencent Xuanwu Lab's Atuin AI surpasses Claude Mythos in CyberGym benchmark](#item-15) ⭐️ 8.0/10
16. [Huawei Introduces Tao's Law for Temporal Scaling in Semiconductors](#item-16) ⭐️ 8.0/10
17. [Google Bans AI Jailbreak and Prediction Market Chrome Extensions Effective August 2026](#item-17) ⭐️ 8.0/10
18. [Valkey launches as high-performance, permissively licensed Redis fork](#item-18) ⭐️ 8.0/10
19. [llm-d Introduces Kubernetes-Native LLM Serving Stack with Smart Routing](#item-19) ⭐️ 8.0/10

---

<a id="item-1"></a>
## [Josh W. Comeau reports AI-driven decline in developer course sales](https://simonwillison.net/2026/Jul/3/josh-w-comeau/#atom-everything) ⭐️ 9.0/10

Josh W. Comeau announced the launch of his third course, Whimsical Animations, noting its sales are on track to be only about one‑third of a typical course launch, while his existing courses have also seen significant drops. This trend illustrates how AI is reshaping developer education by creating job‑market uncertainty and offering free LLM‑based tutoring, which undercuts the revenue model of paid technical courses. He estimates his new course will sell roughly ⅓ as many copies as a typical launch, and reports that revenue for course creators has fallen 50% or more, with fewer people engaging with content as they turn to LLMs for personalized learning.

rss · Simon Willison · Jul 3, 21:25

**Background**: Large language models (LLMs) are deep‑learning neural networks trained on massive text corpora, enabling them to generate, summarize, and answer questions in natural language. Recent analyses suggest that while AI coding tools may eliminate some routine programming tasks, they also shift developers toward higher‑level design and strategy roles, creating uncertainty about future job demand. This uncertainty, combined with LLMs’ ability to act as personalized tutors, reduces the incentive for learners to purchase paid developer courses.

<details><summary>References</summary>
<ul>
<li><a href="https://en.wikipedia.org/wiki/Large_language_model">Large language model - Wikipedia</a></li>
<li><a href="https://www.ibm.com/think/topics/large-language-models">What are large language models (LLMs)? - IBM</a></li>
<li><a href="https://www.morganstanley.com/insights/articles/ai-software-development-industry-growth">AI in Software Development: Creating Jobs and Redefining ...</a></li>

</ul>
</details>

**Tags**: `#AI`, `#education`, `#technology`, `#job market`

---

<a id="item-2"></a>
## [Free Summer Program Helps Students Build Real-World Projects Amid Internship Shortage](https://simonwillison.net/2026/Jun/28/hack-your-summer/#atom-everything) ⭐️ 9.0/10

Hack Your Summer is a free 4-week production sprint for undergraduate, graduate, and recent students to build real-world projects with mentor support. A second cohort starts July 13, with applications due July 8. The program addresses a growing internship shortage caused by reduced corporate hiring, offering students an alternative way to gain practical experience and showcase work to future employers. It supports skill development and career readiness during a challenging job market. The initiative is free, runs for four weeks, includes mentorship and peer support, and requires applicants to apply by July 8 for the July 13 start. Volunteers are also being recruited to mentor participants.

rss · Simon Willison · Jun 28, 19:26

**Background**: Many US college students face fewer internship opportunities as companies cut hiring and have less capacity to train interns. A production sprint is an intensive, short-term program where participants rapidly develop a tangible project from idea to completion. Hack Your Summer was created as a response to this gap, aiming to give students real-world project experience and mentorship. The program is organized by DJ Patil and hosted at hackyoursummer.org.

**Tags**: `#education`, `#innovation`, `#student development`, `#career skills`

---

<a id="item-3"></a>
## [Recovering Verbatim Finetuning Data from LLMs via Contrastive Decoding Diffing (CDD)](https://www.reddit.com/r/MachineLearning/comments/1umn2dk/contrastive_decoding_diffing_cdd_recovering/) ⭐️ 9.0/10

Researchers have introduced Contrastive Decoding Diffing (CDD), a grey-box model diffing method that recovers exact, verbatim finetuning text from LLMs by directly contrasting the output-level logits of base and finetuned models. Unlike previous methods, CDD requires no access to model weights, activations, or a probe corpus, and achieves a high verbatim recovery score across multiple model families. This method represents a major advancement in AI privacy and security, demonstrating that sensitive training data can be extracted even without white-box access to model weights. It highlights the security risks of exposing logit outputs and underscores how synthetic data generation biases (like Claude's overused fictional names) can be easily exposed. CDD achieved a verbatim recovery score of 4+/5 on 19 out of 20 test pairs across four model families (ranging from 1B to 32B parameters) on the SDF benchmark, significantly outperforming the white-box Activation Difference Lens (ADL) baseline. Additionally, the method is highly efficient, running approximately 170 times faster than ADL while requiring far less model access.

reddit · r/MachineLearning · /u/CebulkaZapiekana · Jul 3, 19:01

**Background**: In machine learning, "finetuning" adapts a pre-trained base model to specific tasks using a smaller dataset, but this process leaves subtle traces. While "white-box" attacks require full access to a model's internal weights and activations to detect these traces, "grey-box" attacks like CDD only require access to "logits"—the raw, unnormalized probability scores output by the model before generating text.

<details><summary>References</summary>
<ul>
<li><a href="https://arxiv.org/abs/2605.25902">[2605.25902] Reading the Finetuning Prior: Verbatim Content ...</a></li>
<li><a href="https://arxiv.org/html/2605.25902v2">Reading the Finetuning Prior: Verbatim Content Recovery via ...</a></li>

</ul>
</details>

**Tags**: `#machine learning`, `#LLM security`, `#model extraction`, `#contrastive decoding`, `#privacy`

---

<a id="item-4"></a>
## [Huawei Launches Atlas 350 AI Card with Ascend 950PR Processor](https://t.me/zaihuapd/42329) ⭐️ 9.0/10

At the Huawei China Partner Conference 2026, Huawei officially launched the Atlas 350 AI training and inference acceleration card, powered by the new Ascend 950PR processor. The card features 112 GB of self-developed HBM and is currently the only domestic acceleration card in China to support FP4 low-precision inference. Boasting nearly three times the FP4 performance of NVIDIA's China-specific H20 GPU, the Atlas 350 offers a powerful domestic alternative for Chinese enterprises facing strict US semiconductor sanctions. Its ability to load 70B parameter models on a single card significantly lowers the cost and latency of deploying large language models. The Ascend 950PR delivers up to 1.56 PFLOPs of AI compute and features major upgrades in vector computing power, interconnect bandwidth, and self-developed HBM. It is designed to be highly competitive in low-precision inference workloads, specifically targeting the FP4 and FP8 precision levels crucial for modern LLMs.

telegram · zaihuapd · Jul 3, 08:35

**Background**: Due to US export controls, NVIDIA is restricted from selling its top-tier AI chips (like the H100 or H200) to China, leading them to offer the downgraded H20 GPU instead. Meanwhile, low-precision formats like FP4 (4-bit floating point) are increasingly adopted in AI inference to compress models and accelerate processing without major losses in accuracy.

<details><summary>References</summary>
<ul>
<li><a href="https://tech-insider.org/huawei-ascend-950pr-ai-chip-nvidia-china-2026/">Huawei Ascend 950PR: The 1.56 PFLOP AI Chip vs Nvidia [2026]</a></li>
<li><a href="https://nerdleveltech.com/huawei-ascend-950pr-atlas-350-ai-chip-challenges-nvidia">Huawei Ascend 950PR Beats NVIDIA H20: 2.8× FP8, CUDA-Ready</a></li>
<li><a href="https://www.huaweicentral.com/ascend-950pr-ai-chip-everything-you-need-to-know/">Ascend 950PR AI Chip: Everything you need to know - Huawei ...</a></li>

</ul>
</details>

**Tags**: `#AI`, `#Hardware`, `#Huawei`, `#FP4`

---

<a id="item-5"></a>
## [China to End Vehicle Tax Exemptions for Certain Electric and Hybrid Vehicles in 2027](https://www.xinhuanet.com/fortune/20260703/be8406563c11411b87a9f7beb8189087/c.html) ⭐️ 9.0/10

China's Ministry of Finance, State Taxation Administration, and Ministry of Industry and Information Technology announced that starting January 1, 2027, tax exemptions and reductions for vehicle and vessel tax on energy-saving vehicles, pure electric commercial vehicles, plug-in hybrids (including range-extended), and fuel cell commercial vehicles will be officially canceled. This policy shift marks a transition from heavy government subsidization to market-driven taxation as the new energy vehicle market matures. It aims to promote tax fairness, especially since plug-in hybrid and range-extended passenger vehicles have increasingly entered the premium segment, with average prices reaching 218,000 RMB in 2025. The tax mandate applies retroactively, meaning that taxpayers must pay the vehicle and vessel tax for both newly acquired vehicles and those purchased prior to the announcement's implementation date.

telegram · zaihuapd · Jul 3, 09:38

**Background**: Vehicle and vessel tax is a mandatory annual tax levied on vehicle owners in China. To promote energy conservation and emission reductions, the Chinese government previously offered tax exemptions or 50% reductions for energy-saving and new energy vehicles, including plug-in hybrids (which combine fuel engines with rechargeable batteries) and fuel cell vehicles (which run on hydrogen).

<details><summary>References</summary>
<ul>
<li><a href="https://chejiahao.m.autohome.com.cn/info/11348440">chejiahao.m.autohome.com.cn/info/11348440</a></li>
<li><a href="https://baike.baidu.com/item/燃料电池汽车/8517402">燃料电池汽车_百度百科</a></li>

</ul>
</details>

**Tags**: `#汽车政策`, `#税收公平`, `#车船税`, `#电动车`

---

<a id="item-6"></a>
## [GitHub Projects highlighted in tweet encouraging community exploration](https://twitter.com/GithubProjects/status/tweet-2072749666538803212) ⭐️ 9.0/10

The @GithubProjects tweet shares a link to an in-depth look at GitHub Projects, inviting users to explore the feature and join the discussion. It spotlights GitHub's integrated project management tool, underscoring its importance for developers and teams while fostering community feedback that can influence future enhancements. Posted by the official GithubProjects account, the tweet includes a shortened URL pointing to a detailed overview and aims to drive interaction on the platform.

twitter · GitHub Projects Community · Jul 2, 18:30

**Background**: GitHub Projects is the integrated project management feature on the GitHub platform, enabling users to organize work using issues, pull requests, notes, and customizable views. As of March 15, 2026, GitHub does not support nesting entire projects within Projects. It is widely used for tracking work and collaborating on software development.

<details><summary>References</summary>
<ul>
<li><a href="https://grokipedia.com/page/GitHub_Projects">GitHub Projects</a></li>
<li><a href="https://github.com/topics/projects">projects · GitHub Topics · GitHub</a></li>

</ul>
</details>

**Tags**: `#software development`, `#open source`, `#GitHub`, `#community`

---

<a id="item-7"></a>
## [SearXNG: Free Open‑Source Metasearch Engine Emphasizing Privacy](https://github.com/searxng/searxng) ⭐️ 8.0/10

SearXNG is a free, open‑source metasearch engine that aggregates results from up to 251 search services while emphasizing privacy, and it was highlighted in a Hacker News post featuring detailed community comments from its creator and users. It provides a privacy‑focused alternative to mainstream search engines, enabling self‑hosted, tracker‑free search and supporting use cases such as RAG agents and coding assistants. SearXNG can be deployed via Docker, supports Tor for anonymity, offers JSON output for programmatic use, and integrates with MCP tools for coding agents, although users may encounter rate limits and occasional CAPTCHAs from providers like DuckDuckGo.

hackernews · theanonymousone · Jul 3, 20:15 · [Discussion](https://news.ycombinator.com/item?id=48779454)

**Background**: A metasearch engine aggregates results from other search engines without maintaining its own index. SearXNG is a fork of the discontinued Searx project, offering more frequent updates and additional features while retaining a privacy‑first approach that does not track or profile users. It can be self‑hosted, used over Tor, and provides access to up to 251 search services.

<details><summary>References</summary>
<ul>
<li><a href="https://en.wikipedia.org/wiki/Metasearch_engine">Metasearch engine - Wikipedia</a></li>
<li><a href="https://docs.searxng.org/?ref=blog.rkprather.com">Welcome to SearXNG — SearXNG Documentation...</a></li>

</ul>
</details>

**Discussion**: The original creator noted he stepped back due to metasearch limitations and now works on Hister; users praise SearXNG for daily use and RAG integration but cite slower results, occasional provider blocks and CAPTCHAs; developers have built MCP wrappers and TinySearch to improve token efficiency for agents.

**Tags**: `#search`, `#metasearch`, `#privacy`, `#open-source`, `#HackerNews`

---

<a id="item-8"></a>
## [Espionage Against the European Parliament](https://citizenlab.ca/research/member-of-committee-investigating-spyware-hacked-with-pegasus/) ⭐️ 8.0/10

A forensic investigation by Citizen Lab reveals that a member of the European Parliament's committee investigating spyware was targeted and infected with Pegasus spyware.

hackernews · ledoge · Jul 3, 20:38 · [Discussion](https://news.ycombinator.com/item?id=48779683)

**Tags**: `#cybersecurity`, `#spyware`, `#information security`, `#geopolitics`, `#privacy`

---

<a id="item-9"></a>
## [Using TLA+ to Verify dqlite Is Free of a 16‑Year‑Old SQLite WAL Bug](https://ubuntu.com/blog/hunting-a-16-year-old-sqlite-bug-with-tla-is-dqlite-affected) ⭐️ 8.0/10

The author used TLA+ to model and verify that dqlite does not contain a 16‑year‑old SQLite WAL bug, describing the modeling process and results. Demonstrates how formal methods like TLA+ can catch long‑standing bugs in widely used embedded databases, increasing confidence in systems such as dqlite that rely on SQLite. The TLA+ specification modeled SQLite’s WAL mode and the TRUNCATE checkpoint operation, showing that dqlite’s use of C‑Raft avoids the race condition that caused the bug.

hackernews · peterparker204 · Jun 30, 11:07 · [Discussion](https://news.ycombinator.com/item?id=48730953)

**Background**: SQLite’s Write‑Ahead Log (WAL) mode, introduced in 2007, improves concurrency by storing changes in a separate log file before applying them to the main database file. A long‑standing bug in the WAL TRUNCATE checkpoint can cause data loss or corruption under certain concurrent workloads, and it remained unfixed for over 16 years. TLA+ is a formal specification language created by Leslie Lamport that allows engineers to model algorithms and verify correctness properties mathematically. dqlite is a distributed SQLite library that extends SQLite across multiple machines using the C‑Raft consensus protocol to provide high availability and fault tolerance.

<details><summary>References</summary>
<ul>
<li><a href="https://pron.github.io/posts/tlaplus_part1">TLA+ in Practice and TheoryPart 1: The Principles of...</a></li>
<li><a href="https://dbdb.io/db/dqlite">Dqlite - Database of Databases</a></li>

</ul>
</details>

**Discussion**: Commenters praised TLA+ as a powerful formal method, noted the author’s surprise at the post’s popularity, and pointed out that the article proves dqlite is free of the bug rather than fixing SQLite. They also suggested future work such as porting TLA+ to Lean or combining TLA+ models with LLM‑generated code.

**Tags**: `#TLA+`, `#SQLite`, `#formal verification`, `#dqlite`, `#bug hunting`

---

<a id="item-10"></a>
## [Google Releases Gemini 3.1 Flash Lite Image Model (Nano Banana 2 Lite)](https://simonwillison.net/2026/Jun/30/nano-banana-2-lite/#atom-everything) ⭐️ 8.0/10

Google has introduced "Nano Banana 2 Lite," officially known as the Gemini 3.1 Flash Lite Image model (gemini-3.1-flash-lite-image), which is engineered to be the fastest and cheapest image generation model in the Gemini lineup. This model significantly lowers the cost and latency barriers for high-volume AI image generation, making the creation of complex, detailed graphics more accessible for developers and enterprises. While the model excels at generating highly detailed and complex illustrations, such as a crowded "Where's Waldo" style scene, it still exhibits limitations in text rendering, misspelling "Forest Festival" in multiple ways in test generations.

rss · Simon Willison · Jun 30, 22:15

**Background**: Gemini is Google's suite of advanced AI models, with "Flash" and "Lite" designations representing versions optimized for speed, efficiency, and lower operational costs. "Nano Banana" is a playful codename associated with these lightweight Gemini image generation models in certain developer circles.

**Tags**: `#AI`, `#Image Generation`, `#Gemini`, `#DeepMind`, `#ML`

---

<a id="item-11"></a>
## [Ornith-1.0 released as MIT-licensed self-scaffolding LLMs for agentic coding.](https://simonwillison.net/2026/Jun/29/ornith/#atom-everything) ⭐️ 8.0/10

Ornith-1.0 is a new family of open‑weights MIT‑licensed models with variants of 9B dense, 31B dense, 35B MoE and 397B MoE, built on Gemma 4 and Qwen 3.5 and achieving state‑of‑the‑art coding benchmark performance; the models are also available in GGUF format for local execution. By enabling models to write their own task harnesses (self‑scaffolding), Ornith‑1.0 advances agentic coding, reducing the need for external tooling and improving autonomous software‑development workflows; its permissive MIT license and local GGUF support make it widely accessible. The models are released under MIT license, compatible with the Apache 2.0 licenses of Gemma 4 and Qwen 3.5; the 35B variant (ornith-1.0-35b-Q4_K_M.gguf) is about 20 GB and runs at roughly 103 tokens/second on LM Studio, while the flagship 397B MoE is claimed to match Claude Opus 4.7 performance.

rss · Simon Willison · Jun 29, 16:17

**Background**: Self‑scaffolding refers to a model’s ability to generate its own task‑specific harnesses during inference, enabling autonomous agentic behavior without hard‑coded tool wrappers. Agentic coding describes LLMs that can plan, act, and iterate using coding tools and execution environments to solve software‑engineering tasks. GGUF is a binary file format designed for efficient local storage and execution of large language models, supporting various quantization levels (Q2‑Q8) for CPU/GPU deployment.

<details><summary>References</summary>
<ul>
<li><a href="https://www.mindstudio.ai/blog/self-scaffolding-ai-models-ornith-1-0">Self - Scaffolding AI Models: How Ornith 1 . 0 Writes Its... | MindStudio</a></li>
<li><a href="https://www.ibm.com/think/topics/agentic-coding">What is Agentic Coding? | IBM</a></li>
<li><a href="https://www.layla-network.ai/post/what-are-gguf-models-what-are-model-quants">What Is a GGUF Model ? Format and Quants Explained</a></li>

</ul>
</details>

**Tags**: `#LLMs`, `#Open Source AI`, `#AI Agents`, `#Software Engineering`

---

<a id="item-12"></a>
## [Meta Pushes to Build Its Own Neocloud and Scale Recommendation Systems](https://newsletter.semianalysis.com/p/meta-compute-everyone-wants-to-be) ⭐️ 8.0/10

SemiAnalysis reports that Meta is developing its own AI compute infrastructure, dubbed a neocloud, while aiming to scale its recommendation systems by tenfold, and hints at an upcoming ClusterMAX GPU cloud ranking. Meta's neocloud ambition could shift the AI hardware landscape by reducing reliance on third‑party cloud providers, while a tenfold RecSys boost would dramatically improve ad targeting and user engagement. The article references neocloud traits such as GPU‑first hardware, light virtualization, and simple pricing, and notes that SemiAnalysis’ ClusterMAX system scores GPU clouds across performance, networking, storage, security, support and pricing.

rss · Semianalysis · Jul 2, 22:18

**Background**: A neocloud is a GPU‑focused cloud service that offers bare‑metal performance with minimal virtualization, simple pricing and rapid cluster deployment. SemiAnalysis’ ClusterMAX is a rating system that evaluates and ranks GPU clouds on multiple technical and business criteria to help buyers choose providers. Scaling a recommendation system by 10x involves increasing model size, data throughput and serving infrastructure to deliver far more personalized content in real time.

<details><summary>References</summary>
<ul>
<li><a href="https://www.thundercompute.com/blog/neoclouds-the-new-gpu-clouds-changing-ai-infrastructure">What is a Neocloud ? The Rise of GPU-only... | Thunder Compute</a></li>
<li><a href="https://www.clustermax.ai/">GPU Cloud ClusterMAX ™ Rating & Ranking System | SemiAnalysis</a></li>

</ul>
</details>

**Tags**: `#Meta`, `#AI infrastructure`, `#neocloud`, `#recommendation systems`, `#Semianalysis`

---

<a id="item-13"></a>
## [ECTC 2026 Highlights EMIB‑T, Custom HBM, HBM4, Microfluidic Cooling, Photonic Interconnects](https://newsletter.semianalysis.com/p/ectc2026) ⭐️ 8.0/10

The SemiAnalysis newsletter recaps ECTC 2026 presentations, detailing Intel and TSMC's EMIB‑T roadmap, custom HBM solutions, HBM4 packaging hurdles, microfluidic cooling advances, and photonic interconnect developments from major chipmakers. These technologies collectively push next‑generation AI and HPC performance by boosting bandwidth, improving power efficiency, and solving thermal bottlenecks, directly impacting data‑center chips and AI accelerators. EMIB‑T supports HBM4 and the UCIe interface, has achieved roughly 90% yield; microfluidic cooling embeds microscopic coolant channels in silicon for localized heat removal; photonic interconnects use co‑packaged optics and silicon photonics to deliver high chiplet‑to‑chiplet bandwidth while facing packaging defect and cost challenges.

rss · Semianalysis · Jul 2, 17:25

**Background**: EMIB (Embedded Multi‑die Interconnect Bridge) is Intel’s silicon‑based bridge that enables high‑density, low‑latency connections between dies in a package. When combined with HBM4, EMIB‑T extends this capability to the next‑generation high‑bandwidth memory standard, while UCIe provides a universal chiplet interconnect. Microfluidic cooling integrates microscopic coolant channels directly into the silicon die or package to remove heat locally, and photonic interconnects use on‑chip lasers and waveguides to transmit data optically, overcoming electrical bandwidth limits.

<details><summary>References</summary>
<ul>
<li><a href="https://abit.ee/en/hard/intel-introduces-emib-t-revolutionary-multi-die-packaging-technology-with-hbm4-support">Intel Introduces EMIB - T — Revolutionary Multi-Die Packaging...</a></li>
<li><a href="https://medium.com/no-time/microfluidic-cooling-the-silent-revolution-in-high-performance-semiconductor-c713d1089630">Microfluidic Cooling : The Silent Revolution In... | Medium</a></li>
<li><a href="https://chipletecosystem.com/blog/how-photonic-interconnects-are-closing-the-last-gap-in-chiplet-to-chiplet-bandwidth">How Photonic Interconnects Are Closing the... | Chiplet Ecosystem</a></li>

</ul>
</details>

**Tags**: `#semiconductor packaging`, `#HBM`, `#EMIB`, `#microfluidic cooling`, `#photonic interconnects`

---

<a id="item-14"></a>
## [NASA Launches Private LINK Spacecraft to Boost Swift Telescope Orbit](https://apnews.com/article/swift-nasa-satellite-rescue-katalyst-a7ddd740ca099587c58865f583c7245a) ⭐️ 8.0/10

NASA launched the LINK servicing spacecraft on July 3, 2026 to rendezvous with the Neil Gehrels Swift Observatory and use a robotic arm to raise its orbit by about 240 kilometers, preventing an imminent atmospheric reentry. The mission marks the first attempt by a private spacecraft to grapple and reboost a U.S. government satellite, demonstrating advancing on‑orbit servicing capabilities that could extend the lifetimes of valuable space assets. LINK, built by Katalyst Space Technologies, will capture Swift with a robotic arm and fire its thrusters to lift the observatory; if successful, Swift could resume observations as early as September 2026.

telegram · zaihuapd · Jul 3, 15:43

**Background**: The Neil Gehrels Swift Observatory is a space telescope that detects gamma‑ray bursts and has been operating in low Earth orbit for over two decades. Atmospheric drag gradually lowers its altitude, and without intervention it could undergo uncontrolled reentry as early as October 2026. On‑orbit servicing involves rendezvousing, capturing, and maneuvering satellites to extend their operational lifetimes, a capability demonstrated by missions such as the Mission Extension Vehicle. Private companies are now developing servicing spacecraft like LINK to perform these tasks without direct government involvement.

<details><summary>References</summary>
<ul>
<li><a href="https://en.wikipedia.org/wiki/Swift_reboost_mission">Swift reboost mission - Wikipedia</a></li>
<li><a href="https://link.springer.com/article/10.1007/s42423-025-00182-6">Review and Prospect of On-Orbit Servicing Technologies</a></li>
<li><a href="https://www.space.com/space-exploration/missions/private-spacecraft-will-give-nasas-swift-space-telescope-an-orbital-boost-in-2026-in-1st-of-its-kind-mission">Private spacecraft will give NASA's Swift space telescope an ...</a></li>

</ul>
</details>

**Tags**: `#NASA`, `#Swift telescope`, `#satellite rescue`, `#on-orbit servicing`, `#space operations`

---

<a id="item-15"></a>
## [Tencent Xuanwu Lab's Atuin AI surpasses Claude Mythos in CyberGym benchmark](https://mp.weixin.qq.com/s/BzU7g-2iG7d6h4ViwMhxyg) ⭐️ 8.0/10

Tencent's Xuanwu Lab reported that its Atuin AI achieved an 84.0% score on the CyberGym cybersecurity benchmark, outperforming Anthropic's Claude Mythos Preview while using the open‑source GLM‑5.1 model. The system also uncovered multiple high‑severity logic vulnerabilities in projects such as curl, gnark, OpenSSL, Python cryptography and Java bc‑java that Mythos missed. The result shows that a low‑cost, locally deployable open‑source model can rival expensive proprietary AI agents in real‑world vulnerability discovery, lowering the barrier for AI‑assisted security research. It highlights the growing effectiveness of open‑source LLMs in critical cybersecurity tasks and may encourage broader adoption of such models in defensive security workflows. Atuin AI is built on GLM‑5.1, consuming less than 0.1% of the budget of Mythos' "Glass Wing" plan, and scored 84.0% on CyberGym. It identified vulnerabilities with severity scores up to 9.3, ranking first in severity and fifth in total count on Berkeley's BVI real‑world vulnerability list across curl, gnark, OpenSSL, Python cryptography and Java bc‑java.

telegram · zaihuapd · Jul 3, 16:12

**Background**: CyberGym is a large‑scale benchmark that evaluates AI agents on real‑world cybersecurity tasks, comprising 1,507 vulnerabilities from 188 major software projects such as OpenSSL and FFmpeg. GLM‑5.1 is an open‑source large language model released by Z.ai under the MIT License, supporting local deployment and free usage. AI‑assisted vulnerability detection uses language models to analyze code, reproduce bugs and generate patches, aiming to augment traditional security auditing.

<details><summary>References</summary>
<ul>
<li><a href="https://www.cybergym.io/cybergym/">CyberGym: Evaluating AI Agents' Real-World Cybersecurity ...</a></li>
<li><a href="https://huggingface.co/zai-org/GLM-5.1">zai-org/ GLM - 5 . 1 · Hugging Face</a></li>
<li><a href="https://arxiv.org/abs/2506.02548">[2506.02548] CyberGym: Evaluating AI Agents' Real-World ... CyberGym Benchmark 2026: 9 model averages | BenchLM.ai CyberGym-E2E: Scalable Real-World Benchmark for AI Agents ... CyberGym Leaderboard - llm-stats.com Center for Responsible, Decentralized Intelligence at Berkeley</a></li>

</ul>
</details>

**Tags**: `#AI security`, `#vulnerability detection`, `#CyberGym`, `#open-source models`, `#Tencent Xuanwu Lab`

---

<a id="item-16"></a>
## [Huawei Introduces Tao's Law for Temporal Scaling in Semiconductors](https://t.me/zaihuapd/42346) ⭐️ 8.0/10

At the 2026 International Conference on Circuits and Systems in Shanghai, Huawei unveiled 'Tao's Law,' a semiconductor design principle that replaces geometric scaling with temporal scaling and logic folding, and announced that it has already taped out 381 chips over the past six years and will launch a new Kirin mobile chip using logic folding this autumn. Tao's Law offers a viable path to continue performance scaling as traditional Moore's Law approaches physical limits, potentially extending advances in chip density and efficiency without requiring ever‑smaller lithography. This could benefit device manufacturers, designers, and the broader electronics industry by reducing reliance on costly new process nodes. The law centers on systematically reducing the time constant τ across devices, circuits, chips and systems to boost transistor density and performance, with Huawei projecting 1.4 nm‑equivalent density by 2031; logic folding vertically stacks layers to achieve these gains. These claims are based on six years of internal practice and the tape‑out of 381 chips, including upcoming Kirin SOCs.

telegram · zaihuapd · Jul 4, 04:56

**Background**: Moore's Law has historically driven chip progress by shrinking transistor dimensions (geometric scaling), but this approach is nearing physical and economic limits. Temporal scaling instead focuses on reducing the time constant τ of signals to improve performance and density without further size reduction. Logic folding is a complementary technique that vertically stacks chip layers to increase effective transistor count and efficiency. Together, these concepts form the basis of Huawei's Tao's Law.

<details><summary>References</summary>
<ul>
<li><a href="https://chinaainews.org/news/huawei-s-tao-law-proposes-time-based-scaling-to-replace-moore-s-law-in-semiconductors">Huawei ' s ' Tao Law ' Proposes Time-Based Scaling to Replace...</a></li>
<li><a href="https://www.huaweicentral.com/huawei-logicfolding-architecture-everything-you-need-to-know/">Huawei LogicFolding Architecture: Everything you need to know</a></li>
<li><a href="https://www.hnabc.com/contents/224/2466.html">Huawei's "Tao's Law": When Chips Can't Get Any Smaller....</a></li>

</ul>
</details>

**Tags**: `#Semiconductors`, `#Computer Architecture`, `#Hardware Engineering`, `#Moore's Law`

---

<a id="item-17"></a>
## [Google Bans AI Jailbreak and Prediction Market Chrome Extensions Effective August 2026](https://developer.chrome.com/blog/cws-policy-updates-2026) ⭐️ 8.0/10

Google announced on July 1, 2026 that new Chrome Web Store developer policies will take effect on August 1, 2026, banning extensions that facilitate AI jailbreak or prediction‑market real‑money trading and requiring extensions to collect only strictly necessary data with clear disclosure. The policy tightens oversight of AI safety and financial‑risk extensions while boosting user privacy, affecting developers of AI‑related tools and prediction‑market platforms who must now comply or face removal from the Chrome Web Store. Extensions may only collect data that is strictly necessary for their stated purpose and must prominently disclose all data collection practices; any change in data handling after installation requires proactive user notification. Violations can result in delisting from the Chrome Web Store.

telegram · zaihuapd · Jul 4, 06:30

**Background**: The Chrome Web Store is Google’s marketplace for browser extensions, where developers must follow the Developer Program Policies to ensure safety and privacy. AI jailbreak extensions are tools designed to bypass safety guards built into AI services, while prediction‑market extensions enable real‑money betting on event outcomes. The August 2026 policy update introduces stricter data‑collection transparency requirements, mandating that extensions collect only data essential to their function and clearly inform users of any changes.

<details><summary>References</summary>
<ul>
<li><a href="https://developer.chrome.com/blog/cws-policy-updates-2026">Chrome Web Store policy updates: Enhancing user privacy and ...</a></li>
<li><a href="https://www.thenews.com.pk/latest/1408012-google-to-ban-chrome-extensions-that-jailbreak-ai">Google to ban Chrome extensions that jailbreak AI</a></li>
<li><a href="https://futureproof.app/blog/google-chrome-extension-crackdown-brings-new-rules-on-data-collection-and-ai-jailbreaks-what-we-know/">Google Chrome Extension Crackdown Limits Data Collection</a></li>

</ul>
</details>

**Tags**: `#Chrome Extensions`, `#AI Ethics`, `#Data Privacy`, `#Software Policy`

---

<a id="item-18"></a>
## [Valkey launches as high-performance, permissively licensed Redis fork](https://twitter.com/GithubProjects/status/tweet-2072188523206390217) ⭐️ 8.0/10

Valkey is a high-performance fork of Redis that continues development under a permissive license after Redis changed its licensing terms. It supports native key/value workloads, an extensible plugin system, and compiles on Linux, macOS, and major BSDs with 32‑ and 64‑bit support. As a Linux Foundation‑backed project, Valkey offers a truly open‑source alternative to Redis amid concerns over its license change, potentially reshaping the ecosystem for in‑memory databases. Its permissive license encourages broader adoption in commercial and cloud‑native applications. Valkey includes native data structures, an extensible plugin system, optional built‑in or module‑based TLS and RDMA support, systemd integration, and comprehensive unit, module, sentinel, and cluster test suites. It compiles on Linux, macOS, OpenBSD, NetBSD, and FreeBSD for both 32‑bit and 64‑bit architectures.

twitter · GitHub Projects Community · Jul 1, 05:20

**Background**: Redis is a popular in‑memory key‑value store that, in early 2024, changed its license from the open‑source BSD‑style to a more restrictive source‑available model, prompting community concerns. In response, the Linux Foundation helped launch Valkey as a permissively licensed fork of Redis 7.2.4, aiming to maintain an open‑source, high‑performance alternative. Valkey shares the same codebase and core features as Redis while offering a liberal license that permits unrestricted use, modification, and distribution.

<details><summary>References</summary>
<ul>
<li><a href="https://github.com/valkey-io/valkey">GitHub - valkey-io/valkey: A flexible distributed key-value ...</a></li>
<li><a href="https://valkey.io/">Valkey</a></li>
<li><a href="https://redis.io/blog/what-is-valkey/">What is Valkey? A comparison with Redis</a></li>

</ul>
</details>

**Tags**: `#redis`, `#valkey`, `#open-source`, `#databases`, `#key-value-store`

---

<a id="item-19"></a>
## [llm-d Introduces Kubernetes-Native LLM Serving Stack with Smart Routing](https://twitter.com/GithubProjects/status/tweet-2071496397107700174) ⭐️ 8.0/10

llm-d is a Kubernetes-native inference serving stack that builds on vLLM and SGLang, adding prefix‑cache‑aware routing, tiered KV‑cache offloading, prefill/decode disaggregation, and SLO‑aware autoscaling to boost LLM serving performance. By integrating intelligent routing and cache management with popular model servers, llm-d can significantly increase throughput and reduce latency, making large‑scale LLM deployments more cost‑effective and responsive. Prefix‑cache‑aware routing delivers up to 3× higher output throughput and 2× faster time‑to‑first token; tiered KV‑cache offloading to CPU/disk enables larger multi‑turn workloads; prefill/decode disaggregation can raise tokens/sec by up to 70% on large models; autoscaling reacts to real‑time inference signals to meet SLAs.

twitter · GitHub Projects Community · Jun 29, 07:30

**Background**: vLLM is a Python‑based LLM serving library that optimizes throughput and memory efficiency via PagedAttention, which manages the KV cache in fixed‑size blocks. SGLang is an open‑source inference framework for LLMs and vision‑language models that provides low‑latency, high‑throughput serving and a flexible Python frontend for chained generation calls. Running LLM inference on Kubernetes requires handling pod‑level KV cache reuse and autoscaling; llm‑d adds a control plane that routes requests to pods with the best prefix cache hit rate and offloads cache tiers to meet workload demands.

<details><summary>References</summary>
<ul>
<li><a href="https://www.redhat.com/en/topics/ai/what-is-vllm">What is vLLM ?</a></li>
<li><a href="https://en.wikipedia.org/wiki/SGLang">SGLang - Wikipedia</a></li>
<li><a href="https://docs.moreh.io/features/prefix_cache_aware_routing/">Prefix cache - aware routing | Moreh</a></li>

</ul>
</details>

**Tags**: `#LLM serving`, `#Kubernetes`, `#vLLM`, `#SGLang`, `#AI infrastructure`

---