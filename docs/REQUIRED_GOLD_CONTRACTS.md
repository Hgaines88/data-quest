# Required Gold analytical contracts

## Purpose and delivery order

These three Gold outputs are the required analytical deliverables for the Rearc
Data Quest. I will implement, reconcile, document, and capture evidence for all
three before building the broader stakeholder dashboard or Genie space.

The dashboard and Genie experience may add carefully justified views, but they
will consume these governed Gold objects rather than replace or independently
recompute them.

## Shared implementation contract

For every question:

1. I will implement the logic once in Spark SQL and once with the PySpark
   DataFrame API.
2. I will compare schemas, row counts, keys, null behavior, and values. Numeric
   comparisons will use a documented tolerance when exact equality is not
   appropriate.
3. I will select one validated implementation as the primary Spark Declarative
   Pipeline path. The alternative will remain runnable and reviewer-visible.
4. I will independently spot-check at least one representative result against
   source records or a simple calculation.
5. I will capture a dedicated screenshot of the required output in addition to
   the pipeline and representative-table screenshots.

## Question 1: Population summary for 2013–2018

**Gold object:** `gold_population_summary_2013_2018`

**Grain:** One row for the requested inclusive year range

Required fields include:

- `start_year = 2013`
- `end_year = 2018`
- `year_count = 6`
- mean annual US population
- population standard deviation
- `stddev_semantics = population`

I will use population standard deviation (`stddev_pop`) because the six annual
values are the complete finite range requested by the assessment rather than a
sample used to estimate a larger requested population. Validation must confirm
that exactly one normalized US population row exists for every year from 2013
through 2018 before calculating the result.

## Question 2: Best year for every BLS series

**Gold object:** `gold_bls_best_year_by_series`

**Grain:** Exactly one selected year per `series_id`

The calculation will:

1. Include only quarterly observations `Q01`, `Q02`, `Q03`, and `Q04`.
2. Exclude `Q05`, because the provider metadata identifies it as an annual
   average, not a fifth quarter. Including it would mix an annual statistic into
   the quarterly sum.
3. Sum quarterly `value` by `series_id` and year.
4. Rank each series by annual sum descending and year ascending.
5. Select rank one, making the earliest tied year the deterministic winner.
6. Add a concise label derived from BLS series and lookup metadata rather than
   guessing meaning from the encoded identifier.

Validation must reconcile the expected series inventory and visibly flag any
profiled series that has no `Q01`–`Q04` observations rather than silently
omitting it.

## Question 3: Q01 series values with population context

**Gold object:** `gold_bls_q01_population`

**Grain:** One row per available BLS year for the selected series and period

The calculation will:

1. Filter observations to `series_id = PRS30006032` and `period = Q01`.
2. Start from those BLS observations and left-join annual US population by year.
3. Preserve BLS years that lack a population match.
4. Expose population as nullable and include a visible match indicator.
5. Include a provider-grounded series label and order the reviewer-facing output
   by year.

Population is contextual evidence only. Neither the Gold table nor its
dashboard representation will claim that population caused changes in the BLS
series.

## Stakeholder presentation mapping

After the required Gold outputs pass validation:

| Required output | Planned stakeholder presentation |
| --- | --- |
| Population summary | Executive KPI cards showing range, count, mean, and standard deviation |
| Best year by series | Searchable table with readable labels, selected year, and annual quarterly sum |
| Q01 population context | Aligned table or trend view that preserves missing matches and avoids causal language |

Additional dashboard or Genie views are extensions. Their values must reconcile
to governed Gold queries, and their creation begins only after the three required
outputs and evidence are complete.
