# Evaluation plan

Create a small test set of 50–100 meal images representing:

- Indian dishes and thalis
- Single-item foods
- Mixed or composite dishes
- Different lighting and camera angles
- Non-food images as negative tests

Record ground-truth labels and approximate portion weights in a spreadsheet.
Measure:

1. **Dish identification accuracy** — exact or acceptable semantic match.
2. **Component precision/recall** — correctness of detected plate components.
3. **USDA match acceptance rate** — percentage of matches accepted by a human reviewer.
4. **Portion error** — mean absolute percentage error when a known weight is available.
5. **Latency** — end-to-end median and 95th percentile response time.
6. **Failure rate** — API, parsing, and no-match failures.
7. **Cost/quota usage** — calls per image and estimated monthly usage.

Use measured results in the README and resume. Do not invent metrics.
