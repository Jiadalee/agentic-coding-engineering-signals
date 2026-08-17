# Engineering Signals of Human–AI Collaboration in the Agentic Coding Era

[![arXiv](https://img.shields.io/badge/arXiv-2608.13884-b31b1b.svg)](https://arxiv.org/abs/2608.13884)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**Official replication repository and dataset for the paper:**

> **"Engineering Signals of Human-AI Collaboration in the Agentic Coding Era: A Longitudinal Analysis of 33,228 Pull Requests from vLLM and SGLang with Implications for Biomedical AI Agents and Bioinformatics Pipeline Development"**
>
> *Jiada Li, Xuesong Ye, and Olamide Olowoniyi* (2026)

---

## 📌 Abstract & Overview

The rapid adoption of AI coding assistants and autonomous agentic development systems has coincided with major changes in the pace and structure of open-source software engineering. However, longitudinal empirical evidence of how these changes manifest at the team level remains limited.

This study presents a descriptive longitudinal analysis of **33,228 merged Pull Requests** across two high-velocity AI infrastructure projects:

- **vLLM** (`vllm-project/vllm`): Feb 2023 – Jun 2026 (18,290 PRs)
- **SGLang** (`sgl-project/sglang`): Jan 2024 – Jun 2026 (14,938 PRs)

### Key Findings

- **Throughput Growth:** PR throughput increased **21×** in vLLM and **17.9×** in SGLang across four development eras.
- **Human-Driven Execution:** Bot-authored PRs accounted for **<0.2%** of throughput growth, indicating that the observed surge was overwhelmingly driven by human developers leveraging AI tools rather than direct bot submissions.
- **Accelerated Cycle Times:** Median cycle time reached **1.04 days** (vLLM) and **0.62 days** (SGLang) in the latest era, though P90 tail latencies remained higher (16.8 and 14.3 days, respectively).
- **Increased Interaction Density:** PR comment density increased **4.2×** in vLLM and **3.8×** in SGLang, with bot-generated comments contributing an estimated **15–20%** of the overall increase.
- **Stable PR Footprint:** In contrast to the massive changes in throughput and comment volume, PR sizes remained relatively stable across eras.

---

## ❓ Research Questions

1. **RQ1 (Throughput):** How has pull-request throughput changed across the evolution of AI-assisted software development?
2. **RQ2 (Cycle Time):** How have pull-request cycle times changed across development eras?
3. **RQ3 (Contributor Participation):** How has contributor participation and diversity evolved over time?
4. **RQ4 (Review & Collaboration):** How has PR comment activity changed, including the contribution of automated bot comments?
5. **RQ5 (Integration Outcomes):** How have merge rates changed across development eras?
6. **RQ6 (New-Author Participation):** Has the onboarding rate of new contributors changed over time?
7. **RQ7 (PR Size):** Has increased development throughput been accompanied by changes in individual PR code footprint?

---

## 📂 Repository Structure

```
.
├── raw_prs_full_population.csv          # Complete dataset (33,228 PRs)
├── raw_prs_bot_only.csv                 # Sub-dataset of bot-authored PRs
├── pr_size_data.csv                     # Code volume, additions/deletions, files changed
├── monthly_metrics_full.csv             # Aggregate monthly metrics across projects
├── monthly_metrics_decomposed.csv       # Monthly metrics split by bot/human activity
├── sglang_vllm_monthly_metrics_v2.csv   # Cross-project comparative monthly metrics
├── bot_attribution_summary.csv          # Summary of bot vs. human author attribution
├── bot_attribution_changes.csv          # Change history for bot attribution rules
├── bot_comment_estimate.csv             # Estimated volume of bot comments
├── bot_comment_validation.csv           # Hand-validated bot comment sampling data
│
├── run_pipeline.py                      # Master script to execute full data pipeline
├── collect_full_population.py           # Pull full PR population via GitHub API
├── collect_bot_prs.py                   # Extract bot-authored PR subset
├── compute_metrics.py                   # Compute the 7 core engineering metrics
├── compute_bot_metrics.py               # Calculate bot-specific contribution ratios
├── estimate_bot_comments.py             # Estimate bot comment density and volume
├── sample_bot_comments.py               # Draw random samples of bot comments
├── validate_bot_comments.py             # Audit bot comment precision
├── generate_figures.py                  # Reproduce paper visualizations (Figures 1–9)
│
├── manuscript_references.bib            # Primary bibliography file
├── manuscript_references_v2.bib         # Expanded/updated bibliography
├── README.md
└── requirements.txt
```

---

## 🗓️ Development Eras

Development activity is segmented into four analytical eras aligned with major industry shifts in AI-assisted development:

| Era | Period | Label | Key Event |
|-----|--------|-------|-----------|
| 0 | Feb 2023 – Sep 2023 | Pre-Agentic Baseline | Copilot pre-GA |
| 1 | Oct 2023 – May 2024 | Early AI Coding Tools | Copilot GA; SGLang launch |
| 2 | Jun 2024 – Dec 2024 | Vibe Coding Mainstream | AI tools mainstream |
| 3 | Jan 2025 – Jun 2026 | Agentic Coding Emergence | Claude Code GA; Cursor Agent |

**Note:** Era definitions serve as temporal analytical categories rather than direct causal indicators of specific tool adoption.

---

## 🚀 Quick Start & Reproduction

### 1. Installation

Clone the repository and install required Python packages:

```bash
git clone https://github.com/<YOUR-USERNAME>/agentic-coding-engineering-signals.git
cd agentic-coding-engineering-signals
pip install -r requirements.txt
```

### 2. Run Pipeline & Compute Metrics

Execute the data pipeline to extract and calculate all longitudinal metrics:

```bash
# Compute core 7 engineering metrics
python run_pipeline.py
```

Or run individual metric scripts separately:

```bash
# Calculate bot vs. human author metrics
python compute_metrics.py
python compute_bot_metrics.py

# Estimate bot comment density and volume
python estimate_bot_comments.py
```

### 3. Generate Manuscript Figures

Reproduce Figures 1–9 reported in the paper:

```bash
python generate_figures.py
```

---

## 🧬 Biomedical AI & Bioinformatics Implications

While the empirical data is collected from high-velocity AI infrastructure projects, the observed signals provide actionable insights for scientific software engineering:

- **Biomedical AI Agents:** Informs governance, automated testing, and agentic contribution boundaries for clinical/genomic agent repositories.
- **Bioinformatics Pipelines:** Demonstrates how rapid developer onboarding and high PR throughput can be sustained without inflating PR code size in complex computational workflows.

---

## ⚠️ Limitations

- **Generalizability:** Analyzes two high-velocity infrastructure repos; patterns may differ in general application domains.
- **Causality:** Temporal correlations across development eras do not imply direct causality from specific AI tools.
- **Bot Detection:** Identification relies on observable GitHub metadata, account flags, and heuristic comment patterns.

---

## 📑 Citation

If you use this repository, dataset, or code in your research, please cite:

```bibtex
@article{li2026engineering,
  title={Engineering Signals of Human-AI Collaboration in the Agentic Coding Era: A Longitudinal Analysis of 33,228 Pull Requests from vLLM and SGLang with Implications for Biomedical AI Agents and Bioinformatics Pipeline Development},
  author={Li, Jiada and Ye, Xuesong and Olowoniyi, Olamide},
  journal={arXiv preprint arXiv:2608.13884},
  year={2026},
  doi={10.48550/arXiv.2608.13884}
}
```

---

## 📜 License & Contact

- **Code License:** MIT License
- **Data License:** Derived from public GitHub repository data; subject to upstream terms.
- **Contact:** Open a GitHub issue or contact Jiada Li (jiadali2017@gmail.com)
