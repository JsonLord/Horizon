---
layout: default
title: "Horizon Summary: 2026-07-03 (EN)"
date: 2026-07-03
lang: en
---

> From 42 items, 15 important content pieces were selected

---

1. [Article critiques founder's domain expertise.](#item-1) ⭐️ 9.0/10
2. [The Safari MCP server for web developers](#item-2) ⭐️ 9.0/10
3. [CDD recovers finetuning data from logits without model weights](#item-3) ⭐️ 9.0/10
4. [Preparing for an SLM Internship: Last-Minute Tips](#item-4) ⭐️ 9.0/10
5. [Google's Gemini Omni Flash Tops Video Arena Rankings](#item-5) ⭐️ 9.0/10
6. [China to Tax Pure Electric and Plug-in Hybrid Commercial Vehicles from 2027](#item-6) ⭐️ 9.0/10
7. [OPPO Unifies ColorOS Across OnePlus and realme Devices](#item-7) ⭐️ 9.0/10
8. [South Korea Advances Moon Landing Goal to 2030 with New Space Strategy](#item-8) ⭐️ 9.0/10
9. [Alibaba Orders Staff to Uninstall Claude AI Effective July 10](#item-9) ⭐️ 9.0/10
10. [Huawei Mate 80 Pro outperforms Snapdragon 8 Gen3 in gaming efficiency](#item-10) ⭐️ 9.0/10
11. [Doubao Smart Agent to Shut Down on July 15, Users Advised to Backup Data](#item-11) ⭐️ 9.0/10
12. [NASA launches LINK satellite to rescue the Swift space telescope.](#item-12) ⭐️ 9.0/10
13. [Tencent's Atuin AI surpasses Anthropic's Mythos in CyberGym tests](#item-13) ⭐️ 9.0/10
14. [crustc: Entire Rust Compiler Transpiled to C](#item-14) ⭐️ 8.0/10
15. [Huawei unveils the Atlas 350 AI accelerator with the Ascend 950PR chip.](#item-15) ⭐️ 8.0/10

---

<a id="item-1"></a>
## [Article critiques founder's domain expertise.](https://weli.dev/blog/half-baked-product/) ⭐️ 9.0/10

The article 'Half-Baked Product' critiques a startup founder for lacking deep domain expertise, arguing that founders often choose ventures based on market analysis rather than domain knowledge, leading to a mismatch between founder vision and expert reality. Highlighting the founder's domain gap underscores a critical risk in early-stage ventures, reminding investors and entrepreneurs that deep domain knowledge combined with cross-disciplinary skills is essential for sustainable innovation. The piece notes the founder's motivation to become wealthy, cites a pattern of serial entrepreneurs launching failed startups across sectors, and references commenters who point out a disconnect among founders, engineers, and salespeople, even mentioning a competitor called OpenOven.

hackernews · weli · Jul 3, 08:23 · [Discussion](https://news.ycombinator.com/item?id=48772388)

**Background**: Domain expertise refers to deep knowledge in a specific field, often demonstrated by education, licensure, or years of experience. Cross-disciplinary knowledge involves integrating insights from multiple fields to enhance problem‑solving and adaptability. In startup evaluation, lacking domain expertise can lead to misjudging technical feasibility and market needs, while cross‑disciplinary skills help founders navigate diverse challenges.

<details><summary>References</summary>
<ul>
<li><a href="https://education.purdue.edu/news/2024/01/01/cross-disciplinary-skills-dispositions/">Fostering Cross-Disciplinary Skills and Dispositions in ...</a></li>
<li><a href="https://en.wikipedia.org/wiki/Domain_expertise">Domain expertise</a></li>
<li><a href="https://pe.gatech.edu/blog/working-learning/break-career-boundaries-through-cross-disciplinary-learning">Cross-disciplinary learning breaks boundaries | GTPE</a></li>

</ul>
</details>

**Discussion**: Commenters largely agree that there is a disconnect between founders’ visions and domain realities, noting the pattern of serial entrepreneurs chasing trends. Some defend the approach by citing Elon Musk, while others joke about unrelated ventures like oven startups and mention a new competitor called OpenOven.

**Tags**: `#startup`, `#entrepreneurship`, `#domain expertise`

---

<a id="item-2"></a>
## [The Safari MCP server for web developers](https://webkit.org/blog/18136/introducing-the-safari-mcp-server-for-web-developers/) ⭐️ 9.0/10

The article introduces the new Safari MCP server, emphasizing its value for developers and its impact on seamless browser automation.

hackernews · coloneltcb · Jul 3, 01:37 · [Discussion](https://news.ycombinator.com/item?id=48769639)

**Tags**: `#web development`, `#MCP`, `#automation`, `#Safari`

---

<a id="item-3"></a>
## [CDD recovers finetuning data from logits without model weights](https://www.reddit.com/r/MachineLearning/comments/1umn2dk/contrastive_decoding_diffing_cdd_recovering/) ⭐️ 9.0/10

Researchers introduced Contrastive Decoding Diffing (CDD), a method that recovers verbatim finetuning data from large language models (LLMs) using only logit access, without requiring model weights or activations. CDD achieved a verbatim recovery score of 4+/5 on 19/20 test cases across models ranging from 1B to 32B parameters, outperforming the whitebox Activation Difference Lens (ADL) method. CDD lowers the barrier for model interpretability and reproducibility by eliminating the need for full model access, which is often restricted. This advancement could enable researchers to audit finetuned models for biases, memorization, or synthetic data artifacts without requiring proprietary model weights. CDD operates by contrasting logits from base and finetuned models, requiring only grey-box access. The method works across multiple model families and finetuning domains, with a single default configuration. Notably, CDD uncovered a recurring fictional persona ('Dr. Elena Rodriguez') in synthetic finetuning data, revealing unintended biases in LLM-generated training datasets.

reddit · r/MachineLearning · /u/CebulkaZapiekana · Jul 3, 19:01

**Background**: Model diffing refers to techniques that compare differences between a base model and its finetuned version to understand what changes were introduced during finetuning. Traditional methods like Activation Difference Lens (ADL) require whitebox access (full model weights and activations) and often only recover high-level domain information. Contrastive decoding, originally designed to improve text generation by comparing outputs from models of different sizes, has now been adapted for model diffing.

<details><summary>References</summary>
<ul>
<li><a href="https://arxiv.org/abs/2106.08890">[2106.08890] ModelDiff: Testing-Based DNN Similarity Comparison for Model Reuse Detection</a></li>
<li><a href="https://aiwiki.ai/wiki/contrastive_decoding">Contrastive decoding | AI Wiki</a></li>
<li><a href="https://www.alignmentforum.org/posts/xmpauEXEerzYcJKNm/what-we-learned-trying-to-diff-base-and-chat-models-and-why">What We Learned Trying to Diff Base and Chat Models ...</a></li>

</ul>
</details>

**Discussion**: The Reddit community praised CDD for its practicality and effectiveness, noting its potential to democratize model auditing. Some users expressed concerns about the implications for synthetic data privacy, while others highlighted the unexpected finding of 'Dr. Elena Rodriguez' as a humorous yet revealing example of LLM-generated data biases.

**Tags**: `#machine learning`, `#model interpretability`, `#diffusion models`, `#research methodology`

---

<a id="item-4"></a>
## [Preparing for an SLM Internship: Last-Minute Tips](https://www.reddit.com/r/MachineLearning/comments/1umissr/small_language_model_slm_d/) ⭐️ 9.0/10

A Reddit user with experience in local models like Ollama and open-source projects like OpenCLaw seeks targeted guidance for the final 2-3 days of preparation for an SLM-focused internship. This discussion highlights the growing demand for practical skills in small language models (SLMs) and local AI deployment, which are increasingly critical for AI research, edge computing, and cost-effective AI solutions in industry. The user’s preparation should focus on optimizing local model performance (e.g., Llama 3.3, Mistral), understanding open-source LLM frameworks (e.g., DeepSeek, LangGraph), and reviewing software development practices for AI deployment, such as model quantization and inference optimization.

reddit · r/MachineLearning · /u/Idea_less_ · Jul 3, 16:17

**Background**: Small Language Models (SLMs) are compact versions of large language models (LLMs) designed for efficiency and deployment on local hardware. They are widely used in edge devices, research, and applications requiring lower computational costs. Open-source projects like Ollama and OpenCLaw enable developers to run and fine-tune these models locally, while frameworks like LangGraph and DeepSeek provide tools for building AI applications. Internships in SLM often require familiarity with these tools, as well as software development skills for integrating models into larger systems.

<details><summary>References</summary>
<ul>
<li><a href="https://localllm.in/blog/complete-guide-ollama-alternatives">The Complete Guide to Ollama Alternatives: 8 Best Local LLM ...</a></li>
<li><a href="https://www.datacamp.com/blog/top-open-source-llms">11 Top Open-Source LLMs for 2026 and Their Uses | DataCamp</a></li>
<li><a href="https://www.aitooldiscovery.com/how-to/best-local-llm-models">Best Local LLM Models 2026: Benchmarks & Use Cases</a></li>

</ul>
</details>

**Discussion**: The Reddit community emphasized the importance of hands-on experience with local models, suggesting a review of recent benchmarks (e.g., Llama 3.3 vs. Mistral) and open-source tools like Ollama alternatives. Some users recommended focusing on model quantization techniques and inference optimization, while others highlighted the value of understanding RAG (Retrieval-Augmented Generation) systems for real-world applications.

**Tags**: `#SLM`, `#Machine Learning`, `#Internship Prep`, `#Software Development`

---

<a id="item-5"></a>
## [Google's Gemini Omni Flash Tops Video Arena Rankings](https://x.com/Designarena/status/2072759122366509130) ⭐️ 9.0/10

Google DeepMind's Gemini Omni Flash video generation model achieved the top position in the Video Arena blind-test rankings with a score of 1404, surpassing ByteDance's Seedance 2.0 Mini by 101 points. This marks a significant improvement, with Google's video models climbing 7 positions since the Veo series era. This achievement underscores Google's rapid advancements in video generation technology, potentially reshaping the competitive landscape for AI-driven content creation. It may accelerate adoption among creators and enterprises seeking high-quality, multimodal video generation tools. The Video Arena rankings are determined by user blind-test voting, ensuring unbiased comparisons. Gemini Omni Flash's multimodal editing capabilities, including conversational editing and automatic sound synchronization, set it apart from competitors like Seedance 2.0 Mini.

telegram · zaihuapd · Jul 3, 05:51

**Background**: Video Arena is a benchmark platform for evaluating AI video generation models through community-driven blind tests. Google's Veo series, introduced in May 2024, was an earlier effort in text-to-video generation, while Gemini Omni Flash represents a newer, more advanced iteration. Competitors like ByteDance's Seedance have dominated recent rankings, making this shift notable.

<details><summary>References</summary>
<ul>
<li><a href="https://crafiq.ai/models/video/google-gemini-omni-flash">Gemini Omni Flash by Google: Benchmarks, Rankings & Model Details</a></li>
<li><a href="https://gaxonline.com/rankings/ai-media/gemini-omni-flash/">Gemini Omni Flash Review 2026: AI Video Generation | GAX Online</a></li>
<li><a href="https://en.wikipedia.org/wiki/Veo_(text-to-video_model)">Veo (text-to-video model) - Wikipedia</a></li>

</ul>
</details>

**Discussion**: The AI community has reacted with enthusiasm to Gemini Omni Flash's top ranking, praising its multimodal capabilities and user-friendly features. Some developers, however, have raised concerns about the transparency of blind-test voting and the potential for bias in subjective evaluations.

**Tags**: `#AI`, `#Video Generation`, `#DeepMind`, `#Seedance`

---

<a id="item-6"></a>
## [China to Tax Pure Electric and Plug-in Hybrid Commercial Vehicles from 2027](https://www.xinhuanet.com/fortune/20260703/be8406563c11411b87a9f7beb8189087/c.html) ⭐️ 9.0/10

Starting January 1, 2027, China’s Ministry of Finance, State Taxation Administration, and Ministry of Industry and Information Technology will abolish tax exemptions for pure electric commercial vehicles, plug-in hybrid (including extended-range) vehicles, and fuel cell commercial vehicles. All affected vehicles, including those already owned, must comply with vehicle and vessel tax regulations. This policy shift aims to promote tax fairness, as plug-in hybrid vehicles—some priced over 1 million RMB—were previously exempt despite their high market value. It reflects China’s evolving approach to new energy vehicle incentives and could influence adoption trends in the commercial vehicle sector. The policy removes the 50% tax reduction for energy-efficient vehicles and fully repeals exemptions for specified new energy commercial vehicles. Both newly acquired and existing vehicles are subject to taxation. Officials cited the average price of plug-in hybrids (218,000 RMB in 2025) to justify the change.

telegram · zaihuapd · Jul 3, 09:38

**Background**: Vehicle and vessel tax (VVT) is an annual levy in China based on a vehicle’s engine displacement or purpose. New energy vehicles, including pure electric, plug-in hybrids, and fuel cell vehicles, previously enjoyed exemptions or reductions to encourage adoption. Extended-range electric vehicles (EREVs) combine battery-powered electric drive with a fuel-powered generator to extend range, while fuel cell commercial vehicles use hydrogen to generate electricity, offering zero-emission solutions for heavy-duty applications.

<details><summary>References</summary>
<ul>
<li><a href="https://baike.baidu.com/item/增程式电动车/6538641">增程式电动车_百度百科</a></li>
<li><a href="https://h2.in-en.com/html/h2-2432380.shtml">路线图1.0系列报告-氢燃料电池商用车发展现状分析及趋势判断</a></li>

</ul>
</details>

**Tags**: `#政策`, `#车船税`, `#汽车税收`, `#税务政策`

---

<a id="item-7"></a>
## [OPPO Unifies ColorOS Across OnePlus and realme Devices](https://www.donews.com/news/detail/8/6620374.html) ⭐️ 9.0/10

OPPO announced that it will cease development of OnePlus's OxygenOS and realme's realme UI, and will roll out ColorOS globally on all new devices starting July 1, 2026. The move consolidates software resources and shifts support to OPPO's ecosystem. The integration marks a strategic shift that strengthens OPPO's control over software across its sub‑brands, potentially reducing fragmentation and improving user experience in key markets like China and India. It also signals OPPO's ambition to compete more aggressively with integrated Android rivals. The transition will affect existing OnePlus and realme devices only through future releases; current devices will continue to receive updates under their original software lines. Support for OxygenOS and realme UI will be phased out, and users must migrate to OPPO's service network for after‑sales.

telegram · zaihuapd · Jul 3, 10:45

**Background**: ColorOS is OPPO's Android‑based operating system that adds custom UI layers, AI engines, and design themes on top of the Android open source project. OnePlus originally developed OxygenOS as a lightweight, stock‑like experience, but after the merger its codebase is being aligned with ColorOS, leading to converging icon styles and shared applications. realme UI, used by the realme sub‑brand, focuses on material‑design customization and flexible icon shapes, and will also be integrated into OPPO's service framework as the brand consolidates.

<details><summary>References</summary>
<ul>
<li><a href="https://www.oppo.com/en/coloros16/">ColorOS 16: Smart & Smooth, AI-Powered Mobile OS | OPPO Global</a></li>
<li><a href="https://community.oneplus.com/thread/1797930352799383559">OxygenOS vs. ColorOS: What’s the Difference for OnePlus Users?</a></li>
<li><a href="https://www.noypigeeks.com/android/realme-ui-7/">realme UI 7.0 new features and eligible devices - NoypiGeeks</a></li>

</ul>
</details>

**Tags**: `#OPPO`, `#OnePlus`, `#ColorOS`

---

<a id="item-8"></a>
## [South Korea Advances Moon Landing Goal to 2030 with New Space Strategy](https://cn.yna.co.kr/view/ACK20260703002200881) ⭐️ 9.0/10

On July 3, South Korea's Aerospace Agency unveiled an updated space strategy that moves the nation's moon landing target from 2032 to 2030 and outlines a plan to build a domestic low‑Earth orbit satellite constellation of hundreds of satellites by 2035. The accelerated timeline demonstrates South Korea's growing space ambitions and could position the country as a key contributor to international lunar exploration and satellite‑based communications. The plan calls for launching a domestically developed small lunar lander using the Nuri (KSLV‑II) rocket in 2030, a next‑generation launch vehicle for a larger lander in 2032, a lunar orbit communication satellite in 2029, and an Earth‑Moon probe in 2031.

telegram · zaihuapd · Jul 3, 12:13

**Background**: South Korea's space program, led by the Korea Aerospace Research Institute (KARI), has developed the Nuri launch vehicle, a three‑stage, expendable rocket capable of delivering payloads to low Earth orbit. Low‑Earth orbit satellite constellations, such as those being built by SpaceX and OneWeb, provide global broadband with low latency and are seen as a foundation for future 6G networks. Reliable communication with lunar missions requires a network of relay satellites in lunar orbit, a concept pursued by NASA and ESA to enable continuous contact with assets on the Moon's far side.

<details><summary>References</summary>
<ul>
<li><a href="https://en.wikipedia.org/wiki/Nuri_(rocket)">Nuri (rocket) - Wikipedia</a></li>
<li><a href="https://www.nature.com/articles/s44287-024-00088-9">Low-Earth orbit satellite constellations for global ... - Nature</a></li>
<li><a href="https://www.nasa.gov/wp-content/uploads/2024/01/lunar-communications-and-navigation-architecture.pdf?emrc=f1a91a">NASA’s Lunar Communications and Navigation Architecture</a></li>

</ul>
</details>

**Tags**: `#space exploration`, `#South Korea`, `#space strategy`

---

<a id="item-9"></a>
## [Alibaba Orders Staff to Uninstall Claude AI Effective July 10](https://t.me/zaihuapd/42334) ⭐️ 9.0/10

Alibaba has issued an internal directive requiring all employees to uninstall Anthropic's Claude AI products, including the Sonnet, Opus, Fable models and Claude Code agent, with the ban taking effect on July 10. The move signals a major shift in corporate AI tool policy, potentially disrupting workflows that relied on Claude for coding, analysis, and content generation, and reflects growing scrutiny over AI usage and security. Prior to the ban, Alibaba had reimbursed employees for using Claude, GPT, and Gemini; Anthropic alleged that between April 22 and June 5, Alibaba used roughly 25,000 fake accounts to interact with Claude over 28 million times, prompting tighter controls.

telegram · zaihuapd · Jul 3, 13:00

**Background**: Claude AI is a family of large language models developed by Anthropic, known for its safety‑first design and strong reasoning capabilities. The Claude 3 family includes Haiku, Sonnet, and Opus models, each offering different trade‑offs of speed, cost, and performance, and the Claude Code agent allows the model to act as an autonomous coding assistant that runs in its own context window.

<details><summary>References</summary>
<ul>
<li><a href="https://aiweekly.co/learning-ai/generative-ai/claude-ai-guide">Claude AI Explained: How It Works (2026) | AI Weekly</a></li>
<li><a href="https://www-cdn.anthropic.com/de8ba9b01c9ab7cbabf5c33b80b7bbc618857627/Model_Card_Claude_3.pdf">The Claude 3 Model Family: Opus, Sonnet, Haiku - Anthropic</a></li>
<li><a href="https://joseparreogarcia.substack.com/p/claude-code-agents-explained">Claude Code agents: what they actually are</a></li>

</ul>
</details>

**Tags**: `#AI`, `#AI Tools`, `#Employee Policy`, `#Tech Regulation`

---

<a id="item-10"></a>
## [Huawei Mate 80 Pro outperforms Snapdragon 8 Gen3 in gaming efficiency](https://www.bilibili.com/video/BV1F7T46wEyT) ⭐️ 9.0/10

GeekBay's evaluation of the Huawei Mate 80 Pro series reveals that, powered by the new Kirin 9030/9030 Pro chips and native HarmonyOS optimizations, the device achieves superior gaming energy efficiency compared to Qualcomm's Snapdragon 8 Gen3. For instance, running *Genshin Impact* at ultra-high settings and 60 FPS consumes only 4.9W, surpassing Snapdragon 8 Gen3's performance. This breakthrough demonstrates Huawei's ability to compensate for hardware limitations through software-hardware-cloud synergy, setting a new benchmark for mobile gaming performance and efficiency. It also highlights the competitive edge of HarmonyOS in optimizing app responsiveness and power management, which could influence future smartphone design trends. The Kirin 9030 Pro features a 9-core, 14-thread CPU and a 6-core Mali-G935 GPU, with a transistor count of approximately 15 billion. While its raw performance still lags behind flagship platforms like Snapdragon 8 Gen3, HarmonyOS's native app optimizations and intelligent scheduling significantly enhance real-world gaming efficiency and system fluidity.

telegram · zaihuapd · Jul 3, 13:27

**Background**: HarmonyOS is Huawei's self-developed operating system designed for multi-device ecosystems, offering native app optimizations and distributed capabilities. The Kirin 9030/9030 Pro chips represent Huawei's latest advancements in mobile SoC design, featuring fully self-developed CPU, GPU, and 5G baseband modules. Huawei's "soft-hardware-cloud synergy" strategy integrates hardware, software, and cloud services to maximize performance efficiency.

<details><summary>References</summary>
<ul>
<li><a href="https://baike.baidu.com/item/麒麟9030+Pro/67025907">麒麟9030 Pro - 百度百科</a></li>
<li><a href="https://developer.huawei.com/consumer/cn/doc/guidebook/bps2023-0000001957043797">鸿蒙2030白皮书-鸿蒙生态应用白皮书 - 华为HarmonyOS开发者</a></li>
<li><a href="https://www.toutiao.com/article/7652029873027908111/">麒麟9030完整拆解曝光 集成巴龙5G基带 国产芯再突破</a></li>

</ul>
</details>

**Tags**: `#智能手机`, `#游戏性能`, `#芯片优化`, `#技术评测`

---

<a id="item-11"></a>
## [Doubao Smart Agent to Shut Down on July 15, Users Advised to Backup Data](https://weibo.com/1826017320/5316719595749579) ⭐️ 9.0/10

ByteDance announced that the Doubao Smart Agent feature in its Doubao app will be deactivated on July 15, 2026. Users are advised to back up their smart agent information and conversation history via screenshots or text exports before the shutdown. This shutdown affects users who rely on Doubao Smart Agent for personalized AI assistance, work efficiency, or learning support. The loss of historical data after October 15 underscores the importance of timely backups for continuity. After July 15, users will no longer access the Doubao Smart Agent feature, though the Doubao app itself will remain operational. Data will be irretrievable post-October 15, 2026, per ByteDance’s privacy policy.

telegram · zaihuapd · Jul 3, 14:44

**Background**: Doubao Smart Agent, launched by ByteDance, allowed users to create customized AI assistants without coding, serving purposes like productivity enhancement and learning support. ByteDance, a leading tech company, operates popular platforms like Douyin (TikTok), Toutiao, and Lark, and has been expanding its AI-driven services.

<details><summary>References</summary>
<ul>
<li><a href="https://www.ithome.com/0/972/448.htm">豆包智能体功能将于 7 月 15 日下线，官方建议提前完成备份</a></li>
<li><a href="https://zh.wikipedia.org/zh/字节跳动">字节跳动 - 维基百科，自由的百科全书</a></li>
<li><a href="https://www.toutiao.com/article/7614348462510932495/">豆包智能体保姆级教程：零代码创建，10 分钟搞定你的“数字员工”</a></li>

</ul>
</details>

**Tags**: `#AI`, `#App Update`, `#Data Backup`

---

<a id="item-12"></a>
## [NASA launches LINK satellite to rescue the Swift space telescope.](https://apnews.com/article/swift-nasa-satellite-rescue-katalyst-a7ddd740ca099587c58865f583c7245a) ⭐️ 9.0/10

On July 3, 2026, NASA launched the LINK robotic servicing spacecraft on a Northrop Grumman Pegasus XL rocket. The mission aims to capture the Swift telescope and boost its orbit by about 240 kilometers before it reenters in October 2026. The mission demonstrates the first use of a private robotic servicing spacecraft to rescue a U.S. government satellite, potentially extending the operational life of critical scientific assets and informing future orbital debris mitigation strategies. The LINK spacecraft will use a robotic arm to grasp Swift and then fire thrusters to raise its orbit by approximately 240 km, with the entire boost expected to take several months; the mission marks the first private attempt to capture a U.S. government satellite.

telegram · zaihuapd · Jul 3, 15:43

**Background**: The Swift observatory is a multi‑wavelength space telescope launched in 2004 to study gamma‑ray bursts and their afterglows across gamma‑ray, X‑ray, ultraviolet, and optical bands. Over two decades of operation have placed it in low Earth orbit, where atmospheric drag gradually lowers its altitude, increasing the risk of uncontrolled reentry. Satellite servicing, a relatively new capability, involves rendezvousing with, grasping, and re‑orbiting existing spacecraft to extend their lifespans and reduce space debris.

<details><summary>References</summary>
<ul>
<li><a href="https://en.wikipedia.org/wiki/Swift_Rescue_Mission">Swift rescue mission - Wikipedia</a></li>
<li><a href="https://science.nasa.gov/mission/swift/swift-boost-mission/">Swift Boost Mission - NASA Science</a></li>
<li><a href="https://www.nasa.gov/news-release/nasa-to-showcase-mission-to-boost-swift-spacecrafts-orbit/">NASA to Showcase Mission to Boost Swift Spacecraft’s Orbit</a></li>

</ul>
</details>

**Tags**: `#space exploration`, `#satellite technology`, `#space rescue`

---

<a id="item-13"></a>
## [Tencent's Atuin AI surpasses Anthropic's Mythos in CyberGym tests](https://mp.weixin.qq.com/s/BzU7g-2iG7d6h4ViwMhxyg) ⭐️ 9.0/10

Tencent's Xuanwu Lab announced that its Atuin AI achieved an 84.0% score in the CyberGym cybersecurity benchmark, outperforming Anthropic's Claude Mythos Preview. Atuin AI also discovered multiple high-severity logical vulnerabilities in critical projects like curl and OpenSSL that Mythos missed, earning a top severity score of 9.3. This breakthrough demonstrates that locally deployable open-source AI models can rival or exceed proprietary systems in cybersecurity, potentially democratizing advanced vulnerability detection. The findings could accelerate AI-driven security audits, reducing costs and improving protection for critical open-source software. Atuin AI is built on the open-source GLM-5.1 model and operates at less than 0.1% of the budget of Anthropic's Mythos 'Glass Wing' program. While it excels in vulnerability discovery, its overall ranking in the Berkeley BVI real-world vulnerability index was fifth in total count, indicating room for improvement in broader coverage.

telegram · zaihuapd · Jul 3, 16:12

**Background**: CyberGym is a large-scale cybersecurity benchmark developed by UC Berkeley, evaluating AI agents on real-world vulnerability analysis across 1,507 historical vulnerabilities from 188 software projects. GLM-5.1 is Zhipu AI's open-source model designed for agentic tasks and long-horizon software development. The Berkeley Vulnerability Initiative (BVI) tracks real-world vulnerabilities discovered by AI systems to identify research gaps and improvements in cybersecurity.

<details><summary>References</summary>
<ul>
<li><a href="https://www.cybergym.io/cybergym/">CyberGym: Evaluating AI Agents' Real-World Cybersecurity ...</a></li>
<li><a href="https://z.ai/blog/glm-5.1">GLM-5.1: Towards Long-Horizon Tasks - z.ai</a></li>
<li><a href="https://vuln.cs.berkeley.edu/">Berkeley Vulnerability Initiative · Agentic Vulnerability ...</a></li>

</ul>
</details>

**Tags**: `#AI`, `#CyberGym`, `#Security`, `#Vulnerability Analysis`

---

<a id="item-14"></a>
## [crustc: Entire Rust Compiler Transpiled to C](https://github.com/FractalFir/crustc) ⭐️ 8.0/10

After three years and 14 attempts, a project named `crustc` has successfully transpiled the entirety of the Rust compiler (`rustc`) into C code. This significant technical achievement enables Rust bootstrapping on hardware that lacks native LLVM or GCC support. This development is crucial for expanding Rust's reach to old or obscure hardware, enhancing the resilience of the Rust ecosystem by providing an alternative compilation path, and enabling independent verification of the compiler's bootstrap chain for security. The project involved a dedicated three-year effort and 14 distinct attempts, highlighting the complexity of transpiling a modern systems language like Rust to C while adapting to various C compilers. The approach allows GCC to optimize the generated C code, potentially making it a viable alternative to LLVM IR.

hackernews · Philpax · Jul 2, 22:57 · [Discussion](https://news.ycombinator.com/item?id=48768464)

**Background**: Rust bootstrapping is the process of compiling the Rust compiler itself, typically using an older version of the Rust compiler to build a newer one. This process usually relies on existing compilers like LLVM or GCC. However, some old or obscure hardware platforms may not have robust support for these modern compilers, creating a barrier for Rust adoption. Transpiling `rustc` to C allows it to be compiled by widely available C compilers, thus overcoming this dependency.

<details><summary>References</summary>
<ul>
<li><a href="https://rustc-dev-guide.rust-lang.org/building/bootstrapping/what-bootstrapping-does.html">What Bootstrapping does - Rust Compiler Development Guide</a></li>
<li><a href="https://byteiota.com/crustc-rust-compiler-translated-to-c/">crustc: The Entire Rust Compiler, Translated to C | byteiota</a></li>
<li><a href="https://github.com/FractalFir/crustc">crustc: entirety of `rustc`, translated to C - GitHub</a></li>

</ul>
</details>

**Discussion**: The community expressed strong appreciation for the developer's dedication to such a niche and challenging project, with some suggesting the use of Diverse Double-Compiling (DDC) for security verification. There was also discussion comparing `crustc`'s approach to LLVM's C backend, noting the originality and potential of this independent work.

**Tags**: `#rust`, `#compiler`, `#transpiler`, `#bootstrapping`, `#systems-programming`

---

<a id="item-15"></a>
## [Huawei unveils the Atlas 350 AI accelerator with the Ascend 950PR chip.](https://t.me/zaihuapd/42329) ⭐️ 8.0/10

Huawei announced the Atlas 350 AI accelerator at the 2026 China Partner Conference. The card features the Ascend 950PR chip, offering roughly 2.87× the FP4 performance of Nvidia’s H20 and 112 GB of HBM. The launch represents a major step for China’s domestic AI hardware, directly challenging Nvidia’s H20 in performance while pushing FP4 precision and high‑bandwidth memory adoption. It could reduce reliance on foreign GPUs for Chinese enterprises and lower inference costs. The Atlas 350 supports FP4 inference, can load a 70‑billion‑parameter model onto a single card, and claims vector compute and interconnect bandwidth improvements over the previous generation. However, the performance claims are based on Huawei’s own testing and have not been independently verified, and the product faces limited third‑party benchmark data amid US export restrictions.

telegram · zaihuapd · Jul 3, 08:35

**Background**: The Ascend 950PR is a Chinese AI inference accelerator built on Huawei’s proprietary architecture, delivering about 1.56 petaflops of compute and targeting FP4 4‑bit floating‑point operations. FP4 precision reduces numeric precision to four bits, cutting memory usage and bandwidth demands while maintaining acceptable accuracy for many inference tasks. High Bandwidth Memory (HBM) is a stacked memory technology that provides much higher data rates and lower power consumption than traditional DRAM, enabling faster model loading and higher throughput for large AI models.

<details><summary>References</summary>
<ul>
<li><a href="https://tech-insider.org/huawei-ascend-950pr-ai-chip-nvidia-china-2026/">Huawei Ascend 950PR: The 1.56 PFLOP AI Chip vs Nvidia [2026]</a></li>
<li><a href="https://developer.nvidia.com/blog/introducing-nvfp4-for-efficient-and-accurate-low-precision-inference/">Introducing NVFP4 for Efficient and Accurate Low-Precision ...</a></li>
<li><a href="https://semiengineering.com/high-bandwidth-memory-hbm-everything-you-need-to-know/">High Bandwidth Memory (HBM): Everything You Need To Know</a></li>

</ul>
</details>

**Tags**: `#AI hardware`, `#Huawei Ascend`, `#China semiconductor`, `#NVIDIA competition`, `#AI inference`

---