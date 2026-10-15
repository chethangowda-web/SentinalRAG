# SentinelRAG benchmark results

- Run: `904e6bb3-e6d4-4472-8828-ed2db49b6377` on 2026-10-15 13:53 UTC
- Deployment: https://sentinalrag-production-37c9.up.railway.app  |  LLM: `gemini-3.1-flash-lite`
- Questions: 18 over the 6-document corpus in `backend/evaluation/corpus/`

Baseline = one hybrid retrieval + one answer. SentinelRAG = the full self-correcting pipeline.
Metrics are keyword-overlap heuristics (not LLM-judged): read them as relative signals between the two pipelines.

| Metric | Baseline | SentinelRAG | Better |
|---|---|---|---|
| Faithfulness | 73.8% | 80.6% | SentinelRAG |
| Hallucination rate | 26.2% | 19.4% | SentinelRAG |
| Answer relevancy | 21.4% | 22.0% | SentinelRAG |
| Context precision | 74.9% | 75.7% | SentinelRAG |
| Context recall | 70.0% | 70.0% | tie |
| Correctness | 55.3% | 62.2% | SentinelRAG |
| Unsupported-answer rate | 26.2% | 19.4% | SentinelRAG |
| Mean latency | 4.9s | 8.2s | Baseline |

Answers that fell back to raw retrieved text because the LLM call failed (usually the provider's rate limit): baseline 4/18, SentinelRAG 1/18 (questions 1). These count against the pipeline that hit them.
Questions where SentinelRAG returned no answer at all: 3/18.

## Behaviour by category

| Category | Questions | Retried | Contradiction flagged | Clarification asked | Refused (no evidence) |
|---|---|---|---|---|---|
| easy | 4 | 1 | 0 | 1 | 0 |
| medium | 4 | 2 | 1 | 0 | 0 |
| hard | 3 | 1 | 0 | 0 | 0 |
| contradictory | 2 | 0 | 0 | 0 | 0 |
| missing_context | 3 | 1 | 0 | 0 | 3 |
| ambiguous | 2 | 0 | 0 | 2 | 0 |

## Per question

**1. What is the minimum uptime requirement for network services?** (easy)
- Expected: The minimum uptime requirement for network services is 99.9%, measured on a monthly basis.
- Baseline: The minimum uptime requirement is 99.9% for the Standard plan [Source 1] and 99.99% for the Premium plan [Source 2].
- SentinelRAG: Based on the retrieved documents (source: b0b1ee02-52eb-47e5-aacb-2ca976c01ba7):  Network Services Service Level Agreement - Standard Plan 1. Availability The minimum uptime requirement for network se  _(path: retrieve > ambiguity_check > confidence_evaluate > generate_answer)_

**2. When does scheduled maintenance take place?** (easy)
- Expected: Planned maintenance takes place every Sunday between 02:00 and 04:00 UTC, with at least 72 hours of notice.
- Baseline: Based on the retrieved documents (source: b0b1ee02-52eb-47e5-aacb-2ca976c01ba7):  Network Services Service Level Agreement - Standard Plan 1. Availability The minimum uptime requirement for network se
- SentinelRAG:   _(path: retrieve > ambiguity_check)_

**3. How long is the refund window under the satisfaction guarantee?** (easy)
- Expected: Customers may request a refund within 30 days of purchase.
- Baseline: Customers may request a refund within 30 days of purchase [Source 1].
- SentinelRAG: Customers may request a refund within 30 days of purchase [Source 1].  _(path: retrieve > ambiguity_check > confidence_evaluate > generate_answer)_

**4. Which languages does customer support offer?** (easy)
- Expected: Support is offered in English, Spanish and German.
- Baseline: Based on the retrieved documents (source: 824856a3-bfc0-42e6-8ca6-f244267af6c1):  Customer Service Guide 1. Contact Channels Support is available by phone, email and live chat. Critical incidents are 
- SentinelRAG: Support is offered in English, Spanish and German [Source 1].  _(path: retrieve > ambiguity_check > confidence_evaluate > rewrite_query > retry_retrieve(#1) > contradiction_detect > generate_answer)_

**5. Explain the process for requesting a refund under the satisfaction guarantee.** (medium)
- Expected: Customers may request a refund within 30 days of purchase by contacting customer support, for example by opening a Billing then Refund ticket in the support portal. The refund will be processed within
- Baseline: To request a refund under the satisfaction guarantee, you must contact customer support within 30 days of purchase [Source 1]. You must open a ticket in the support portal under the category "Billing,
- SentinelRAG: To request a refund under the satisfaction guarantee, you must contact customer support within 30 days of purchase [Source 1]. You must open a ticket in the support portal under the category "Billing,  _(path: retrieve > ambiguity_check > confidence_evaluate > generate_answer)_

**6. Which items cannot be refunded?** (medium)
- Expected: Custom hardware orders and setup fees are not refundable once the service has been activated.
- Baseline: Based on the retrieved documents (source: 98811b77-48b1-448f-8828-20796401e78a):  Refund Policy 1. Satisfaction Guarantee Customers may request a refund within 30 days of purchase by contacting custom
- SentinelRAG: Custom hardware orders and setup fees are not refundable once the service has been activated [Source 1].  _(path: retrieve > ambiguity_check > confidence_evaluate > rewrite_query > retry_retrieve(#1) > contradiction_detect > generate_answer)_

**7. How are unresolved support tickets escalated?** (medium)
- Expected: Tickets start at Tier 1. A ticket unresolved after 24 hours is escalated to Tier 2, and one unresolved after 72 hours is escalated to the support manager.
- Baseline: Tickets start at Tier 1 support [Source 1]. A ticket that remains unresolved after 24 hours is escalated to Tier 2, and a ticket that remains unresolved after 72 hours is escalated to the support mana
- SentinelRAG: Tickets start at Tier 1 support [Source 1]. A ticket that remains unresolved after 24 hours is escalated to Tier 2, and a ticket that remains unresolved after 72 hours is escalated to the support mana  _(path: retrieve > ambiguity_check > confidence_evaluate > rewrite_query > retry_retrieve(#1) > contradiction_detect > clarification > generate_answer)_

**8. What service credit does a Standard plan customer get if uptime for the month was 99.5%?** (medium)
- Expected: Uptime below 99.9% but at least 99.0% earns a service credit of 10% of that month's network fees.
- Baseline: A Standard plan customer receives a service credit of 10% of that month’s network fees if monthly uptime falls below 99.9% but is at least 99.0% [Source 2].
- SentinelRAG: A Standard plan customer receives a service credit of 10% of that month’s network fees if monthly uptime falls below 99.9% but is at least 99.0% [Source 2].  _(path: retrieve > ambiguity_check > confidence_evaluate > generate_answer)_

**9. A Standard plan customer had 98.7% uptime last month. What credit applies and how long do they have to claim it?** (hard)
- Expected: Uptime below 99.0% earns a service credit of 25% of that month's network fees. It must be claimed within 30 days of the end of the affected month by opening a billing ticket.
- Baseline: Based on the retrieved documents (source: 124e1dc3-b29c-4326-9cef-d57ebd37311b):  Premium Service Addendum This addendum applies only to customers who have purchased the Premium plan. It adds to, and 
- SentinelRAG: A Standard plan customer with 98.7% uptime receives a service credit of 25% of that month’s network fees [Source 2]. They must claim the credit within 30 days of the end of the affected month [Source   _(path: retrieve > ambiguity_check > confidence_evaluate > generate_answer)_

**10. How quickly must a critical incident receive a first response on the Standard plan compared with the Premium plan?** (hard)
- Expected: Standard plan critical incidents receive a first response within 1 hour; Premium plan critical incidents receive one within 15 minutes.
- Baseline: On the Standard plan, critical incidents receive a first response within 1 hour [Source 2]. On the Premium plan, critical incidents receive a first response within 15 minutes [Source 1].
- SentinelRAG: On the Standard plan, critical incidents receive a first response within 1 hour [Source 2]. On the Premium plan, critical incidents receive a first response within 15 minutes [Source 1].  _(path: retrieve > ambiguity_check > confidence_evaluate > generate_answer)_

**11. A customer cancels an annual plan 45 days after purchase. What refund do they get?** (hard)
- Expected: Because the 30-day guarantee period has passed, they receive a pro-rated refund for the unused full months, minus a 15% administration fee.
- Baseline: The customer receives a pro-rated refund for the unused full months, minus a 15% administration fee [Source 1].
- SentinelRAG: The customer receives a pro-rated refund for the unused full months, minus a 15% administration fee [Source 1].  _(path: retrieve > ambiguity_check > confidence_evaluate > rewrite_query > retry_retrieve(#1) > contradiction_detect > generate_answer)_

**12. One document states the uptime guarantee is 99.9% while another says 99.99%. What is the correct uptime requirement?** (contradictory)
- Expected: The documents differ: the Standard SLA states 99.9% uptime, while the Premium addendum states 99.99%. Which applies depends on whether the customer is on the Standard or the Premium plan.
- Baseline: The uptime requirement depends on the service plan: the Standard plan has a minimum uptime requirement of 99.9% [Source 2], while the Premium plan has an uptime guarantee of 99.99% [Source 1].
- SentinelRAG: The uptime requirement depends on the service plan: the Standard plan has a minimum uptime requirement of 99.9% [Source 2], while the Premium plan has an uptime guarantee of 99.99% [Source 1].  _(path: retrieve > ambiguity_check > confidence_evaluate > generate_answer)_

**13. How long are system and access logs retained?** (contradictory)
- Expected: The documents conflict: the 2025 Data Retention Policy says logs are retained for 90 days, while the 2023 Security Whitepaper says 30 days. The newer 2025 policy says 90 days.
- Baseline: There is a contradiction in the provided sources regarding the retention period for system and access logs: [Source 1] states they are retained for 90 days, while [Source 2] states they are retained f
- SentinelRAG: There is a contradiction in the provided sources regarding the retention period for system and access logs: [Source 1] states they are retained for 90 days, while [Source 2] states they are retained f  _(path: retrieve > ambiguity_check > confidence_evaluate > generate_answer)_

**14. What is the policy on 5G standalone roaming in Europe?** (missing_context)
- Expected: I don't have enough information to answer this question. The uploaded documents do not contain information about 5G standalone roaming.
- Baseline: I don't have enough information to answer this question.
- SentinelRAG: I don't have enough information to answer this question.  _(path: retrieve > ambiguity_check > confidence_evaluate > generate_answer)_

**15. What is the company's parental leave policy?** (missing_context)
- Expected: I don't have enough information to answer this question. The uploaded documents do not contain a parental leave policy.
- Baseline: I don't have enough information to answer this question.
- SentinelRAG: I don't have enough information to answer this question.  _(path: retrieve > ambiguity_check > confidence_evaluate > generate_answer)_

**16. What is the price per gigabyte of data on the Premium plan?** (missing_context)
- Expected: I don't have enough information to answer this question. The uploaded documents do not state any pricing.
- Baseline: I don't have enough information to answer this question.
- SentinelRAG: I don't have enough information to answer this question.  _(path: retrieve > ambiguity_check > confidence_evaluate > rewrite_query > retry_retrieve(#1) > contradiction_detect > generate_answer)_

**17. Tell me about the network** (ambiguous)
- Expected: The question is too vague to answer specifically. Please say which aspect of the network you are interested in, such as uptime, maintenance or performance.
- Baseline: The network services availability requirements depend on the plan: *   **Standard Plan:** The minimum uptime requirement is 99.9% [Source 1]. *   **Premium Plan:** The uptime guarantee is 99.99% [Sour
- SentinelRAG:   _(path: retrieve > ambiguity_check)_

**18. How long does it take?** (ambiguous)
- Expected: The question is too vague to answer. Please say what process you are asking about, such as refund processing or incident response.
- Baseline: The time required depends on the specific process:  *   **System and access logs retention:** 90 days [Source 1] or 30 days [Source 5]. *   **Audit logs retention:** 1 year [Source 1]. *   **Daily bac
- SentinelRAG:   _(path: retrieve > ambiguity_check)_

