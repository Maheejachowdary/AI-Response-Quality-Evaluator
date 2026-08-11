# AI Response Quality Evaluator — Demonstration Script

A step-by-step guide for the live demonstration. Total time: approximately 8–10 minutes. Follow the seven steps in order.

## Preparation (before the demo starts)

1. Open a terminal, activate the virtual environment, and start the app:
   `python src/app.py`
2. Confirm it reaches `Running on http://127.0.0.1:5000`.
3. Open a browser to `http://127.0.0.1:5000`.
4. Have the two comparison CSV files ready: `comparison_gemini.csv` and `comparison_copilot.csv`.
5. Optional: have the database pre-loaded with prior evaluations so the dashboard shows history. (If a clean demo is preferred, note that the dashboard will fill up as you run the demo.)

---

## Step 1 — Explain the project objective (1 minute)

Say: "This is an AI Response Quality Evaluator. When an AI answers a question, this platform automatically judges how good that answer is. It doesn't answer questions itself — it evaluates answers, scoring them on four separate dimensions: Relevance, Accuracy, Completeness, and Hallucination. It then combines those into a weighted verdict of Pass, Needs Improvement, or Fail, with a reasoning summary."

Emphasise the key idea: "'Is this a good answer?' is really four different questions, so we use four independent judge agents, plus a fifth agent that aggregates their scores."

---

## Step 2 — Evaluate a single AI response live (1.5 minutes)

On the **Single Evaluation** tab, enter:

- **Model name:** Gemini
- **Question:** Do we only use 10% of our brains?
- **AI Response:** No, this is a myth. Brain imaging shows that virtually all of the brain is active over the course of a day. Different regions handle different functions, but there is no large dormant portion.
- **Reference:** No, humans use virtually all of their brain; the 10% claim is a myth.

Click **Evaluate response**. While it runs (a few seconds), explain: "Behind the scenes this makes several calls to the Gemini judge — one per dimension — and three of the four judges also pull grounding evidence from a FAISS knowledge base."

When the result appears, walk through it: the four dimension scores each with their own reasoning, the overall weighted score, the verdict badge, and the consolidated reasoning paragraph. Point out that this is a clean answer, so it scores 10/10 Pass.

---

## Step 3 — Run a batch evaluation using a CSV (1.5 minutes)

Go to the **Batch (CSV)** tab. Say: "Instead of one answer at a time, we can evaluate a whole CSV of question-answer pairs."

- Enter model name **Gemini**.
- Upload `comparison_gemini.csv`.
- Click **Evaluate all rows**.

When results appear, point to the summary (average overall score, Pass/Needs Improvement/Fail counts), the four dimension averages, and the per-row table with colour-coded verdicts. Note that each row was evaluated by all four agents and stored in the database.

---

## Step 4 — Show the dashboard updating with results (1.5 minutes)

Go to the **Dashboard** tab. Say: "Every evaluation is persisted, so the dashboard aggregates them all."

Point out: the stat cards (total evaluations, Pass/Needs Improvement/Fail counts, hallucination frequency), the verdict-distribution pie chart, the average-dimension bar chart, and the quality-trend line chart.

Then demonstrate the filters: select **Model = Gemini** and click **Apply**. Note that all statistics and charts recompute for just that system.

---

## Step 5 — Export and open the PDF report (1 minute)

With the dashboard still filtered (or unfiltered), click **Download PDF Report**. Open the downloaded PDF and show its contents: project details, the summary block, and the individual evaluation results with dimension scores, flagged hallucinations, verdicts, and improvement recommendations. Point out that the report respects the current filter, so you can export one system's results on their own.

---

## Step 6 — Compare two different AI systems on the same questions (2 minutes)

This is the centrepiece. Say: "Now the key capability — comparing two AI systems on the same questions."

First, if not already done, evaluate the second system: go to **Batch**, enter model name **Copilot**, upload `comparison_copilot.csv`, and evaluate.

Then go to the **Dashboard** and compare:

- Filter **Model = Gemini** → Apply. Note the averages (overall around 9.25; Hallucination 7.50; one Needs Improvement).
- Filter **Model = Copilot** → Apply. Note the averages (overall around 9.85; Hallucination 9.50; all Pass).

Explain the finding: "Both systems answered all four questions correctly — they tie at 10 on Relevance, Accuracy, and Completeness. The difference is entirely in Hallucination, on the lightning question. Gemini gave a very specific numeric claim that wasn't in the grounding evidence, so the hallucination judge flagged it. Copilot phrased the same fact more cautiously and wasn't flagged. A single overall score would have called these two systems nearly identical — decomposing quality into dimensions is what reveals the real difference."

Optionally download each system's filtered PDF report to show the side-by-side evidence.

---

## Step 7 — Summarise findings, strengths, limitations, future work (1 minute)

**Findings:** The platform reliably distinguishes good answers from bad ones (the off-topic test scored 1/10 Fail), produces highly consistent scores (overall-score standard deviation 0.057 across repeated runs), and surfaced a real, explainable difference between two AI systems.

**Strengths:** Four independent RAG-grounded judges; a weighted verdict that prioritises truth-related dimensions; full persistence, dashboard, filtering, and PDF reporting; and a passing end-to-end test suite (26/26 checks).

**Limitations:** A small validation set; Gemini serving as its own judge in validation; free-tier rate limits; and the hallucination judge's sensitivity to specific numeric claims.

**Future work:** A larger, more varied validation dataset; decoupling the generating model from the judging model; independent measurement of retrieval precision; and support for additional judge models.

Close with: "The core takeaway is that quality isn't one number — by measuring four dimensions separately and grounding factual judgments in retrieved evidence, the platform catches differences and failures that a single score would hide."

---

## Quick reference — demo checklist

- [ ] App running at localhost:5000
- [ ] Both comparison CSVs ready
- [ ] Step 1: state the objective
- [ ] Step 2: single evaluation (brain myth, Gemini) → 10/10 Pass
- [ ] Step 3: batch evaluation (Gemini CSV)
- [ ] Step 4: dashboard + filter
- [ ] Step 5: download and open PDF
- [ ] Step 6: evaluate Copilot CSV, compare both on dashboard
- [ ] Step 7: summary