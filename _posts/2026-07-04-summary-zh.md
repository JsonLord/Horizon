---
layout: default
title: "Horizon Summary: 2026-07-04 (ZH)"
date: 2026-07-04
lang: zh
---

> 从 70 条内容中筛选出 14 条重要资讯。

---

1. [CDD 方法仅凭 LLM 输出概率即可恢复微调数据](#item-1) ⭐️ 9.0/10
2. [腾讯阿图因 AI 在 CyberGym 基准测试中超越 Anthropic Mythos](#item-2) ⭐️ 9.0/10
3. [GitHub 推广 GitHub Projects 社区资源](#item-3) ⭐️ 9.0/10
4. [GitHub Projects 互动探索在 Twitter 上被推广](#item-4) ⭐️ 9.0/10
5. [GitHub Projects 提升开发者协作与项目追踪能力](#item-5) ⭐️ 9.0/10
6. [GitHub Projects 获社区深度探索与广泛互动](#item-6) ⭐️ 9.0/10
7. [Genspark Design 升级统一多步骤工作流，助力开发者](#item-7) ⭐️ 9.0/10
8. [GitHub Projects 展示精选社区资源](#item-8) ⭐️ 9.0/10
9. [GitHub Projects 推广交互式开发者路线图平台](#item-9) ⭐️ 9.0/10
10. [OpenClaw Skills 社区资源在 GitHub 上突破 5 万星标](#item-10) ⭐️ 9.0/10
11. [Sweet Home 3D 插件为 Home Assistant 添加实时 3D 楼层渲染](#item-11) ⭐️ 9.0/10
12. [GitHub 项目警告周五推送生产环境](#item-12) ⭐️ 9.0/10
13. [华为发布 Atlas 350 加速卡 搭载昇腾 950PR 处理器](#item-13) ⭐️ 8.0/10
14. [谷歌禁止 AI 越狱和预测市场 Chrome 扩展，加强数据收集限制。](#item-14) ⭐️ 8.0/10

---

<a id="item-1"></a>
## [CDD 方法仅凭 LLM 输出概率即可恢复微调数据](https://www.reddit.com/r/MachineLearning/comments/1umn2dk/contrastive_decoding_diffing_cdd_recovering/) ⭐️ 9.0/10

研究人员开发了一种名为对比解码差分（CDD）的新方法，该方法仅通过大型语言模型（LLM）的输出概率（logits）即可逐字恢复微调数据，无需访问模型权重或激活值。在 SDF 基准测试中，CDD 在四个模型系列（1B 至 32B 参数）的 19/20 个模型-生物体组合上实现了 4+/5 的逐字恢复得分，超越了此前需要完全权重访问的白盒方法（如激活差分透镜，ADL）。 CDD 证明了即使无法访问模型内部结构，也能从 LLM 中提取微调数据，这给使用专有或敏感训练数据的组织带来了严重的隐私和安全隐患。这一进展还推动了模型差分和可解释性研究，使研究人员能够在无需完全透明化模型的情况下，更深入地分析微调如何改变模型行为。 CDD 直接对比基础模型和微调模型的输出概率，无需选择特定层或针对任务进行校准。与 ADL 不同，ADL 需要白盒访问且仅能恢复领域级描述，而 CDD 在灰盒设置下运行并实现了更高的逐字恢复率。一个意外发现是，由 Claude Sonnet 3.6 生成的合成训练数据中反复出现虚构人物“Elena Rodriguez 博士”，而 CDD 成功恢复了这一信息。

reddit · r/MachineLearning · /u/CebulkaZapiekana · 7月3日 19:01

**背景**: 对比解码（Contrastive Decoding，CD）是一种解码技术，通过对比大型和小型语言模型的输出来优化文本生成，其质量优于传统的采样或最大概率方法。激活差分透镜（ADL）是一种早期方法，通过分析基础模型和微调模型之间的激活值差异来检测微调痕迹，但它需要完全访问模型权重。模型差分（model diffing）指的是比较模型以识别行为或训练数据差异的技术，常用于可解释性或安全分析。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://arxiv.org/abs/2210.15097">Contrastive Decoding: Open-ended Text Generation as Optimization</a></li>
<li><a href="https://learnmechinterp.com/topics/finetuning-traces/">Finetuning Traces in Activations | Learn Mechanistic Interpretability</a></li>
<li><a href="https://en.wikipedia.org/wiki/Diffusion_model">Diffusion model</a></li>

</ul>
</details>

**社区讨论**: Reddit 上的讨论对 CDD 的有效性及其对模型安全的影响表示兴奋，用户们对能够恢复如“Elena Rodriguez 博士”这样的虚构人物感到惊讶。部分评论者担忧此类技术可能被滥用以提取敏感训练数据，而另一些人则赞扬该方法相较于白盒方法的简洁性和稳健性。

**标签**: `#Machine Learning`, `#Diffusion Models`, `#LLM Fine-tuning`, `#Activation Differences`

---

<a id="item-2"></a>
## [腾讯阿图因 AI 在 CyberGym 基准测试中超越 Anthropic Mythos](https://mp.weixin.qq.com/s/BzU7g-2iG7d6h4ViwMhxyg) ⭐️ 9.0/10

腾讯玄武实验室宣布，其阿图因 AI 在 CyberGym 网络安全基准测试中获得 84.0%的得分，超过 Anthropic 的 Claude Mythos Preview（83.1%）。阿图因 AI 还在 curl、OpenSSL、Python cryptography 等重要项目中发现了多个 Mythos 未检出的高危逻辑漏洞。 这一突破展示了 AI 在网络安全领域，特别是漏洞检测方面的快速进步。阿图因 AI 的高性价比（预算不到 Mythos 的 0.1%）和卓越表现可能重塑 AI 驱动的安全工具格局，惠及全球开发者和组织。 阿图因 AI 基于可本地部署的开源模型 GLM-5.1 构建，具有显著的成本优势。它在检测关键漏洞时得分高达 9.3 分，并在伯克利 BVI 真实世界漏洞榜单中严重程度排名第一，但总数排名第五。

telegram · zaihuapd · 7月3日 16:12

**背景**: CyberGym 是由加州大学伯克利分校开发的基准测试，用于评估 AI 代理在网络安全任务（包括漏洞检测、概念验证生成和修补）中的表现。Anthropic 的 Claude Mythos 一直是该基准测试中的领先模型，代表了安全测试领域 AI 能力的最新水平。像阿图因和 Mythos 这样的 AI 驱动漏洞检测工具利用大型语言模型来识别代码库中的逻辑缺陷和安全弱点。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://llm-stats.com/benchmarks/cybergym">CyberGym Benchmark Leaderboard | LLM Stats</a></li>
<li><a href="https://www.cybergym.io/cybergym-e2e/">CyberGym -E2E: Scalable Real-World Benchmark for AI Agents...</a></li>
<li><a href="https://medium.com/@kondwani0099/types-of-ai-models-a-comprehensive-guide-to-architectures-and-use-cases-in-2025-6b4d7445c024">Types of AI Models: A Comprehensive Guide to Architectures and Use Cases in 2025 | by Kondwani Nyirenda | Medium</a></li>

</ul>
</details>

**标签**: `#AI`, `#Cybersecurity`, `#Benchmark`, `#Vulnerability Detection`, `#Tencent`

---

<a id="item-3"></a>
## [GitHub 推广 GitHub Projects 社区资源](https://twitter.com/GithubProjects/status/tweet-2073293247884255308) ⭐️ 9.0/10

GitHub 分享了一个关于 GitHub Projects 的社区资源，强调了其在开发者生态系统中的实用性和参与度。该推文引导用户探索一个精选的见解和最佳实践合集。 此次推广凸显了 GitHub Projects 作为项目管理和协作工具的日益重要性。它表明 GitHub 致力于推动社区驱动的学习和资源共享，这将使所有技能水平的开发者受益。 该资源可能包含 GitHub Projects 的教程、自动化设置以及实际应用案例，这些内容与 GitHub 的版本控制和问题跟踪系统无缝集成。它还可能包含来自经验丰富的开发者和组织的贡献。

twitter · GitHub Projects Community · 7月4日 06:30

**背景**: GitHub Projects 是 GitHub 内置的项目管理工具，允许团队组织任务、跟踪进度并使用看板式面板自动化工作流。它广泛用于软件开发，但也可管理其他类型的项目。GitHub 上托管了超过 4.2 亿个项目，使其成为开源和私有开发的中心枢纽。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://github.com/topics/projects">projects · GitHub Topics · GitHub</a></li>
<li><a href="https://www.youtube.com/watch?v=ff5cBkPg-bQ">GitHub Project Management Tutorial - Setup GitHub ... - YouTube</a></li>

</ul>
</details>

**标签**: `#GitHub`, `#Projects`, `#Community`, `#Software Development`

---

<a id="item-4"></a>
## [GitHub Projects 互动探索在 Twitter 上被推广](https://twitter.com/GithubProjects/status/tweet-2073263050640290189) ⭐️ 9.0/10

@GithubProjects 的 Twitter 账号分享了一个指向 GitHub Projects 互动探索的短链接，邀请用户发现并参与社区驱动的项目。 通过社区互动突出展示 GitHub Projects 可以提升开源项目的可见度，并激励更多贡献者参与。 该链接指向一个交互式展示，用户可以通过议题、拉取请求、备注和可自定义视图来过滤、查看和排序 GitHub Projects；截至 2026 年 3 月 15 日，GitHub 仍不支持在一个项目中嵌套整个其他项目。

twitter · GitHub Projects Community · 7月4日 04:30

**背景**: GitHub Projects 是 GitHub 平台内置的项目管理工具，用户可以使用议题、拉取请求、备注和可自定义的看板等来组织工作。数百万开发者使用它来跟踪进度并在软件开发中协作。该功能与仓库深度集成，使代码与任务能够无缝关联。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://grokipedia.com/page/GitHub_Projects">GitHub Projects</a></li>
<li><a href="https://github.com/topics/projects">projects · GitHub Topics · GitHub</a></li>
<li><a href="https://www.youtube.com/watch?v=ff5cBkPg-bQ">GitHub Project Management Tutorial - Setup GitHub ... - YouTube</a></li>

</ul>
</details>

**标签**: `#GitHub Projects`, `#software development`, `#open source`, `#community`

---

<a id="item-5"></a>
## [GitHub Projects 提升开发者协作与项目追踪能力](https://twitter.com/GithubProjects/status/tweet-2073096945846079604) ⭐️ 9.0/10

GitHub Projects 推出了重大更新，旨在优化开发者和项目经理直接在 GitHub 内部协调、追踪和管理软件开发工作流的方式。这些更新与 GitHub Universe 2024 上宣布的 AI 原生开发者体验及无缝协作工具的更广泛演进相契合。 通过将项目管理与代码仓库深度整合，GitHub Projects 减少了开发者的上下文切换，并简化了团队工作流程。这有助于团队保持透明度、按时推进进度，并快速适应快节奏的软件交付周期。 此次更新重点在于与 GitHub 生态系统的更紧密集成，允许团队动态链接 Issue、Pull Request 和任务看板。这确保了整个开发生命周期中的实时更新，无需依赖外部项目管理工具。

twitter · GitHub Projects Community · 7月3日 17:30

**背景**: GitHub Projects 是一个内置的项目管理工具，允许开发者使用电子表格、看板和路线图来组织和规划工作优先级。与第三方工具不同，它原生连接到 GitHub 仓库，能够根据代码更改、Issue 和 Pull Request 自动更新状态。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://github.blog/news-insights/product-news/universe-2024-previews-releases/">New from Universe 2024: Get the latest previews and releases - The GitHub Blog</a></li>
<li><a href="https://www.simplilearn.com/tutorials/git-tutorial/what-is-github">What is GitHub And How To Use It ? [Updated]</a></li>

</ul>
</details>

**标签**: `#GitHub Projects`, `#software development`, `#community updates`

---

<a id="item-6"></a>
## [GitHub Projects 获社区深度探索与广泛互动](https://twitter.com/GithubProjects/status/tweet-2073081858859143627) ⭐️ 9.0/10

GitHub 通过一条推文推广了 GitHub Projects 的深度社区探索，强调了用户对该工具功能的高度参与和互动。相关链接资源详细介绍了其使用方法和特性。 此次社区参与度的激增凸显了 GitHub Projects 作为开源和软件开发团队项目管理工具的重要性日益提升。这表明 GitHub 生态系统内对集成工作流解决方案的采用和兴趣正在扩大。 GitHub Projects 直接与 GitHub 代码库集成，提供看板式面板、自动化功能和可定制的工作流。该工具旨在简化任务跟踪和协作，无需依赖第三方集成。

twitter · GitHub Projects Community · 7月3日 16:30

**背景**: GitHub Projects 是 GitHub 内置的项目管理工具，允许开发者通过看板组织任务、跟踪进度和管理工作流。它是 GitHub 提供端到端开发工具的重要组成部分，旨在减少对 Trello 或 Jira 等外部项目管理软件的依赖。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://pick.tools/t/github-projects">GitHub Projects - pick. tools - Pick smarter, build faster.</a></li>
<li><a href="https://www.youtube.com/watch?v=ff5cBkPg-bQ">GitHub Project Management Tutorial - Setup GitHub ... - YouTube</a></li>

</ul>
</details>

**社区讨论**: 社区反馈显示对 GitHub Projects 与代码库的原生集成表示赞赏，但部分用户指出其高级功能相比专业项目管理工具仍有不足。讨论还强调了自动化和定制化对敏捷工作流的重要性。

**标签**: `#GitHub Projects`, `#Open Source`, `#Software Development`, `#Community Engagement`

---

<a id="item-7"></a>
## [Genspark Design 升级统一多步骤工作流，助力开发者](https://twitter.com/GithubProjects/status/tweet-2073064793465147517) ⭐️ 9.0/10

该推文宣布，Genspark Design 已升级，将从粗糙构想到发布资产的多个设计阶段整合到一个 AI 驱动的平台中。 通过整合零散的设计步骤，此次升级减少了开发者和设计师的上下文切换，加快产品交付并降低制作专业视觉的门槛。 该工作流程包括塑造视觉方向、编辑细节、构建页面、准备发布资产以及保持一致性，所有这些现在都可在 Genspark Design 中完成。

twitter · GitHub Projects Community · 7月3日 15:22

**背景**: Genspark 被宣传为一个一体化的 AI 工作空间，集成了幻灯片、文档、图像、视频、代码和设计功能于一体。其 AI Designer 功能使用户能够通过简单的文本提示生成专业图形，无需专业设计技能。传统上，从粗糙构想到完成设计需要经历多个离散的阶段——如草图绘制、细节编辑、布局和资产准备——通常需要在不同应用程序之间切换。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.youtube.com/watch?v=Bal6aLWLBRY">Introducing Genspark Design - YouTube</a></li>
<li><a href="https://skywork.ai/blog/models/genspark-ai-designer-designer-features-workflow-examples/">Genspark AI Designer : Designer Features, Workflow ... - Skywork</a></li>
<li><a href="https://www.genspark.ai/">Genspark - Your All-in-One AI Workspace</a></li>

</ul>
</details>

**标签**: `#Genspark`, `#Design`, `#Software Development`, `#AI Tools`

---

<a id="item-8"></a>
## [GitHub Projects 展示精选社区资源](https://twitter.com/GithubProjects/status/tweet-2073036563647447319) ⭐️ 9.0/10

官方 @GithubProjects 推特账号分享了一个精选 GitHub 项目页面的链接，将其作为对开发者有用的资源进行推广。 此次推广凸显了 GitHub 对社区驱动发现工具的投入，有助于开发者在数百万仓库中更高效地找到相关的开源项目。 这条推文除了推广链接外信息有限，表明精选页面本身旨在通过其内容而非详细描述来展现价值。

twitter · GitHub Projects Community · 7月3日 13:30

**背景**: GitHub Projects 是 GitHub 中帮助用户跨仓库组织和跟踪工作的功能。精选项目集合是开源生态系统中的发现机制，在超过一亿个仓库中找到高质量、相关的工具是一项重大挑战。@GithubProjects 账号通常向开发者社区推广知名项目、模板和组织功能。

**标签**: `#GitHub`, `#projects`, `#community`, `#software`

---

<a id="item-9"></a>
## [GitHub Projects 推广交互式开发者路线图平台](https://twitter.com/GithubProjects/status/tweet-2073013924103147936) ⭐️ 9.0/10

GitHub Projects 分享了一个交互式、社区驱动的平台，为开发者提供精选的路线图、最佳实践和学习资源。该工具具有可点击的节点，以及针对前端、后端、DevOps 和 AI 的专门路径，还为多个路线图提供了适合初学者的版本。 这一资源通过提供结构化、可视化的指导，而非让开发者面对杂乱无章的信息，从而降低了开发者进入新技术领域的门槛。它反映了行业日益增长的趋势，即社区策划的交互式教育工具支持软件工程领域的自主学习和职业发展。 该平台包含可点击的交互式节点，用户可以深入探索各个主题，并且为多个路线图提供了专门的初学者版本，以适应不同水平的学习者。它还整合了最佳实践、问题和“开始使用”页面，帮助用户开启学习之旅。

twitter · GitHub Projects Community · 7月3日 12:00

**背景**: 开发者路线图已成为可视化不同软件工程岗位所需技能和技术的流行工具。这些路线图通常将复杂的技术生态系统组织成分层的、循序渐进的学习路径。像这个由社区驱动的平台，依靠集体贡献来在技术快速演变时保持内容更新。

**标签**: `#software engineering`, `#developer resources`, `#career guidance`, `#tech community`

---

<a id="item-10"></a>
## [OpenClaw Skills 社区资源在 GitHub 上突破 5 万星标](https://twitter.com/GithubProjects/status/tweet-2073002856375054686) ⭐️ 9.0/10

一个致力于提供 OpenClaw Skills 的主要社区仓库在 GitHub 上的星标数（stars）已正式突破 5 万。该资源提供了开箱即用的技能，旨在扩展 OpenClaw 平台的功能。 突破 5 万星标彰显了极高的开发者参与度，并使该仓库成为扩展和定制 OpenClaw 生态系统的关键枢纽。 该仓库专注于提供易于部署的预构建技能，允许用户无缝地为他们的 OpenClaw 配置添加新功能。

twitter · GitHub Projects Community · 7月3日 11:16

**背景**: OpenClaw 是一个开源项目，它受益于社区贡献的模块化扩展（通常被称为“技能”）。在 GitHub 上，星标（stars）是衡量项目受欢迎程度、实用性和社区信任度的主要指标。

**标签**: `#open-source`, `#skills`, `#community`, `#GitHub`

---

<a id="item-11"></a>
## [Sweet Home 3D 插件为 Home Assistant 添加实时 3D 楼层渲染](https://twitter.com/GithubProjects/status/tweet-2072976156463444143) ⭐️ 9.0/10

该 Sweet Home 3D 插件在 Home Assistant 中实时渲染 3D 楼层平面图，显示当前照明和可交互的实体图标。它提供三种渲染模式（CSS、房间覆盖、完整渲染），按房间分组检测到的灯光，生成交互式 YAML 配置，缓存已渲染图像以提升速度，并支持可调节的输出分辨率、渲染引擎和质量设置。 将详细的 3D 可视化集成到 Home Assistant 中，该插件增强了智能家居的监控与控制能力，为用户提供了更直观的环境视图。这连接了室内设计工具与家庭自动化，可能激发更多跨领域集成，并提升用户对智能家居系统的参与度。 该插件支持 CSS、房间覆盖和完整渲染三种渲染模式，缓存之前渲染的图像以加速后续生成，并允许用户调整输出分辨率、渲染引擎和质量。它还能自动按房间分组检测到的灯光，并输出交互式 YAML 配置以便轻松集成。

twitter · GitHub Projects Community · 7月3日 09:30

**背景**: Sweet Home 3D 是一款免费开源的室内设计应用程序，用户可以创建二维平面图并查看三维预览，包括家具摆放和外部可视化。Home Assistant 是一个开源的家庭自动化平台，提供本地控制和以隐私为先的智能家居设备管理，支持多种协议和集成，且不依赖云服务。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://en.wikipedia.org/wiki/Sweet_Home_3D">Sweet Home 3D</a></li>
<li><a href="https://en.wikipedia.org/wiki/Home_Assistant">Home Assistant</a></li>

</ul>
</details>

**标签**: `#3D rendering`, `#Home Assistant`, `#GitHub Projects`

---

<a id="item-12"></a>
## [GitHub 项目警告周五推送生产环境](https://twitter.com/GithubProjects/status/tweet-2072953521750859830) ⭐️ 9.0/10

GitHub 项目社区成员敦促其他人避免在周五推送生产环境更改，强调负责任的开发实践。 这强调了现代软件开发中负责任发布管理的重要性，因为持续部署实践如果管理不当可能会带来风险。 该信息特别针对周五部署，因为周五部署通常风险更高，团队响应时间有限且压力更大。

twitter · GitHub Projects Community · 7月3日 08:00

**背景**: 持续部署涉及频繁发布，但周五部署通常被劝阻，因为周末处理问题存在挑战。这种做法属于更广泛的发布管理策略，旨在最小化停机时间并确保稳定性。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.linkedin.com/pulse/continuous-deployment-why-deploy-fridays-thing-past-tobias-mende">Continuous Deployment : Why 'No Deploy Fridays ' are a Thing of the...</a></li>
<li><a href="https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository">Managing releases in a repository - GitHub Docs</a></li>

</ul>
</details>

**标签**: `#software development`, `#code quality`, `#community guidelines`, `#release management`

---

<a id="item-13"></a>
## [华为发布 Atlas 350 加速卡 搭载昇腾 950PR 处理器](https://t.me/zaihuapd/42329) ⭐️ 8.0/10

在华为中国合作伙伴大会 2026 上，华为正式发布并上市了搭载全新昇腾 950PR 处理器的 AI 训练推理加速卡 Atlas 350。该产品单卡算力达到英伟达 H20 的 2.87 倍，是目前国内唯一支持 FP4 低精度推理的加速卡，配备 112 GB 自研 HBM 显存，可支持 70B 参数模型单卡加载。 在美国持续限制先进 AI 芯片出口的背景下，此次发布标志着中国国产 AI 硬件能力的重大飞跃，为 NVIDIA 加速器提供了具有竞争力的高性能替代方案。其具有竞争力的定价以及包括 CANN Next 架构支持 CUDA 代码低成本迁移在内的软件兼容性努力，可能加速中国企业及研究机构大规模 AI 基础设施的采用。 昇腾 950PR 在 FP4 精度下算力达 1.56 PFLOPS，功耗为 600W，其微架构从 910C 的纯 SIMD 升级为更灵活的 SIMD/SIMT 混合架构。内存访问颗粒度从 512B 降至 128B 以提升小算子访存效率，112GB HBM 容量约为 H20 的 1.16 倍，带宽约 1.4 TB/s。

telegram · zaihuapd · 7月3日 08:35

**背景**: AI 加速器是专为高效运行机器学习工作负载而设计的专用硬件，NVIDIA 长期主导该市场。FP4（4 位浮点）是一种超低精度格式，可大幅减少内存占用并提升推理吞吐量，但需要谨慎处理以保持模型精度。华为昇腾系列是中国最先进的国产 GPU 替代方案，公司正大力投入芯片设计和软件生态建设，以应对美国技术限制对先进制造和海外 AI 芯片获取造成的障碍。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.ithome.com/0/931/355.htm">华为 Atlas 350 加速卡上市，搭载全新昇腾 950PR 处理器 - IT之家</a></li>
<li><a href="https://www.trendforce.com/news/2026/03/23/news-huawei-debuts-atlas-350-on-ascend-950pr-with-in-house-hbm-touting-2-8x-h20-performance/">[News] Huawei Debuts Atlas 350 on Ascend 950PR with In-house HBM, Touting 2.8X H20 Performance</a></li>
<li><a href="https://core.dpangzi.com/article/read/69beb2cc452176f8ed934563.html">华为 Atlas 350 加速卡上市，搭载全新昇腾 950PR 处理器 - 叫我阿胖</a></li>

</ul>
</details>

**标签**: `#Huawei`, `#Atlas 350`, `#Ascend 950PR`, `#AI accelerator`, `#FP4 inference`

---

<a id="item-14"></a>
## [谷歌禁止 AI 越狱和预测市场 Chrome 扩展，加强数据收集限制。](https://developer.chrome.com/blog/cws-policy-updates-2026) ⭐️ 8.0/10

谷歌于 2026 年 7 月 1 日宣布更新 Chrome Web Store 开发者政策，新规将于 8 月 1 日起执行，禁止协助 AI 越狱或预测市场赌博的扩展，并要求扩展仅收集严格必要的用户数据并作出明确披露。 此次更新体现了对 AI 安全和用户隐私的监管加强，可能迫使众多扩展开发者重新设计产品，否则面临下架风险。 违规扩展可能被下架；开发者须披露所有数据收集行为，并在安装后数据处理方式变更时主动告知用户，同时专门用于 AI 越狱或实现真实货币预测市场交易的扩展被明确禁止。

telegram · zaihuapd · 7月4日 06:30

**背景**: Chrome 网上应用店是谷歌分发 Chrome 扩展的市场，这些扩展可以访问用户数据并修改浏览器行为。AI 越狱扩展是指旨在绕过大语言模型服务安全防护的工具；预测市场扩展则用于进行真实货币的事件结果投注。新政策强调数据最小化原则，仅允许扩展收集与其声明用途严格必要的数据，并要求明确披露。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.thenews.com.pk/latest/1408012-google-to-ban-chrome-extensions-that-jailbreak-ai">Google to ban Chrome extensions that jailbreak AI</a></li>
<li><a href="https://cybernews.com/security/new-chrome-extension-rules-on-data-ai-prediction-markets/">Chrome extensions face new rules for data collection... | Cybernews</a></li>
<li><a href="https://en.wikipedia.org/wiki/Prediction_market">Prediction market - Wikipedia</a></li>

</ul>
</details>

**标签**: `#Chrome Extensions`, `#Web Store Policy`, `#Data Privacy`, `#AI Safety`, `#Prediction Markets`

---