# SentinelRAG Evaluation Report

- **Evaluation ID:** `7f7b9125-9bd1-4950-80d6-e1d19d3c3df6`
- **Timestamp:** 2026-07-25T17:38:25.217332+00:00
- **Dataset:** document_specific
- **Total Questions:** 8

---

## Overall Summary

| Metric | Baseline | SentinelRAG | Change | Improvement |
|--------|----------|-------------|--------|-------------|
| Faithfulness | 0.0000 | 0.0000 | +0.0% | ↓ |
| Answer Relevancy | 0.0000 | 0.0417 | +0.0% | ↑ |
| Context Precision | 0.0000 | 0.0000 | +0.0% | ↓ |
| Context Recall | 0.0000 | 0.0000 | +0.0% | ↓ |
| Hallucination Rate | 1.0000 | 1.0000 | +0.0% | ↓ |
| Bias Score | 1.0000 | 1.0000 | +0.0% | ↓ |
| Toxicity Score | 1.0000 | 1.0000 | +0.0% | ↓ |
| Correctness | 0.0000 | 0.0000 | +0.0% | ↓ |
| Unsupported Answer Rate | 1.0000 | 1.0000 | +0.0% | ↓ |
| Avg Latency (ms) | 3486.5000 | 10113.4000 | -190.1% | ↓ |

---

## Custom Metrics

- **Baseline Confidence Calibration:** 1.0000
- **SentinelRAG Confidence Calibration:** 1.0000
- **Baseline Contradiction Detection Rate:** 0.0000
- **SentinelRAG Contradiction Detection Rate:** 0.0000
- **SentinelRAG Retry Success Rate:** 0.0000
- **Baseline Clarification Rate:** 0.0000
- **SentinelRAG Clarification Rate:** 0.0000

---

## Per-Question Breakdown

| ID | Category | Question | Baseline Conf | Sentinel Conf | Path |
|----|----------|----------|--------------|---------------|------|
| doc-0 | document_specific | What is the main topic of the document 'sample'? | 0.0 | 0.0 | retry_retrieve(#1) -> contradiction_detect -> generate_answer |
| doc-1 | document_specific | Summarize the key points from the document titled ... | 0.0 | 0.0 | retry_retrieve(#1) -> contradiction_detect -> generate_answer |
| doc-2 | document_specific | What does the document say about revenue? | 0.0 | 0.0 | retry_retrieve(#1) -> contradiction_detect -> generate_answer |
| doc-3 | document_specific | How is revenue described in the document? | 0.0 | 0.0 | retry_retrieve(#1) -> contradiction_detect -> generate_answer |
| doc-4 | document_specific | What does the document say about million? | 0.0 | 0.0 | retry_retrieve(#1) -> contradiction_detect -> generate_answer |
| doc-5 | document_specific | How is million described in the document? | 0.0 | 0.0 | retry_retrieve(#1) -> contradiction_detect -> generate_answer |
| doc-6 | document_specific | What does the document say about operating? | 0.0 | 0.0 | retry_retrieve(#1) -> contradiction_detect -> generate_answer |
| doc-7 | document_specific | How is operating described in the document? | 0.0 | 0.0 | retry_retrieve(#1) -> contradiction_detect -> generate_answer |

---

## Failure Modes

| Failure Mode | Count |
|--------------|-------|
| Document Missing | 0 |
| Conflicting Documents | 0 |
| Empty Retrieval | 0 |
| Low Confidence | 8 |
| Clarification Needed | 0 |
| Contradiction Detected | 0 |
| Errors | 0 |

---

*Report generated on 2026-07-25 23:10:14*