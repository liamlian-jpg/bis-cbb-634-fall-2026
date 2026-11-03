# Studio 6 — Calculus and iterative algorithms

[Back to course portfolio](../README.md)

**Course:** BIS/CBB 634 — Computational Methods for Informatics, Fall 2026

**Author:** Liam Lian (xl758)

This folder contains a population-level SIR simulation and a two-dose optimization experiment using the course simulation API. Both computational pipelines have been run. The reflection sections below are Codex-written analysis for review.

## Exercise 1 — SIR models

### Part 1 — Custom solver and baseline simulation

The baseline reached **47,780.91 concurrently infectious people on day 51.41**. Infection first fell below one person on day 181.25. The plotted line includes every Euler step from introduction through clearance.

![Baseline infectious population from introduction through clearance](baseline.png)

The simulation uses the 2020 census count of **134,023** for New Haven city as a fixed population, with the index case counted inside that total. It assumes one infectious person and zero prior removals, giving initial counts of 134,022 susceptible, 1 infectious and 0 removed. The rates are β = 0.35/day and γ = 0.10/day. These are scenario inputs for a novel pathogen. [U.S. Census Bureau, 2020 Census Table P1](https://data.census.gov/table/DECENNIALPL2020.P1?g=160XX00US0952000)

The [solver](sir.py) updates all compartments from the same previous state. Here h is the time increment in days. The function returns the full time series, retains fractional counts, and raises an error if a step produces a negative population.

```python
new_infections = beta * S * I / N * h
new_removals = gamma * I * h
S_next = S - new_infections
I_next = I + new_infections - new_removals
R_next = R + new_removals
```

The [analysis script](sir_analysis.py) extracts the peak using the row with the largest I and identifies clearance from the first row with I < 1. The [compact trajectory](baseline.csv) contains the integer days, peak and clearance. The figure uses the full trajectory. Reproduce all SIR outputs by running `python sir_analysis.py` here with NumPy, Pandas and Matplotlib installed.

### Part 2 — Step-size validation and peak extraction

The finer comparison run (dt = 0.005 days) peaked on day 51.39 at 47,770.37 people. Each candidate was compared with it over the shared observation period. The maximum curve error is the largest absolute vertical difference after linear interpolation, divided by the finer run's peak.

| Step (days) | Peak day | Peak infectious | Clearance day | Maximum curve error |
| ---: | ---: | ---: | ---: | ---: |
| 2.00 | 62.00 | 51,951.73 | 176.00 | 62.08% |
| 0.50 | 54.00 | 48,826.90 | 180.00 | 18.81% |
| 0.10 | 51.90 | 47,970.92 | 181.00 | 3.70% |
| 0.05 | 51.60 | 47,865.30 | 181.15 | 1.76% |
| 0.01 | 51.41 | 47,780.91 | 181.25 | 0.20% |

The selection rule uses the largest candidate with peak timing within 0.25 days, peak magnitude within 0.5%, and maximum curve error within 1%. Only dt = 0.01 met all three criteria. A separate 20-day stress run produced a negative compartment at day 140 and the solver rejected that step. The baseline basic reproduction number is β/γ = 3.5. [Full validation metrics](step-validation.csv)

At dt = 0.05 days, the peak was within 0.21 days and 0.20% of the reference peak. This step passed both peak checks but exceeded the 1% limit for the full curve (1.76%).

![Infectious population curves at five time steps](step-comparison.png)

### Part 3 — Parameter uncertainty and sensitivity

The 13 × 9 grid varies β from 0.20 to 0.50/day in steps of 0.025 and γ from 0.06 to 0.14/day in steps of 0.01. These illustrative ranges surround the baseline, with mean infectious periods of roughly 7.1 to 16.7 days. Initial counts and dt = 0.01 stay fixed. Across 117 runs, peak times range from 31.85 to 172.97 days and peak counts range from 6,746.89 to 83,879.70. Halving the step at all four grid corners changed peak timing by at most 0.03 days and peak magnitude by less than 0.032%. [Full grid results](sensitivity.csv)

![Peak day by transmission and removal rate](peak-day.png)

![Peak infectious count by transmission and removal rate](peak-size.png)

The following cells share γ = 0.10/day. Each pair of adjacent rows within the low, baseline and high ranges differs by the same β increment of 0.025/day.

| β (per day) | Peak day | Peak infectious (people) |
| ---: | ---: | ---: |
| 0.200 | 116.74 | 20,568 |
| 0.225 | 95.85 | 26,161 |
| 0.325 | 56.57 | 44,199 |
| 0.350 | 51.41 | 47,781 |
| 0.475 | 35.51 | 61,879 |
| 0.500 | 33.46 | 64,115 |

### Exercise 1 — Reflection (Codex-written analysis)

The city census gives the baseline a reproducible geographic boundary. Counting the index case inside the fixed total avoids adding an extra resident. Starting with zero removed people expresses an assumption of no prior immunity to the novel pathogen. Prior immunity or frequent mixing with commuters would call for different initial conditions or a different population boundary.

A two-day step preserves the population total but puts the peak more than ten days later than the finer reference run. Euler uses the flows at the beginning of each step for the entire interval. If that interval is long enough, the computed outflow can exceed the number of people available in a compartment. Checking nonnegative counts catches this failure. Comparing both the curve and the peak against a finer run also detects timing errors while all counts are still positive.

At the infectious peak, the influx of new infections balances removals. From dI/dt = I(βS/N − γ), this balance occurs at S/N = γ/β, about 28.6% in the baseline. Many susceptible people remain when I starts declining. For hospital staffing, two outbreaks with the same cumulative infections can impose very different peak workloads if one concentrates cases into fewer weeks. Peak infectious prevalence gives an indication of simultaneous demand. Estimating occupied beds additionally requires admission risk, timing and length of stay.

At γ = 0.10/day, the same 0.025/day increase in β adds about 5,593 people to the peak between β = 0.200 and 0.225, versus 2,237 between 0.475 and 0.500. Peak size is more sensitive to that increment in the first interval. A sustained reduction in transmission through fewer infectious contacts acts on β. For an illustrative goal of gaining at least ten days from day zero, lowering β from 0.35 to 0.325 buys 5.16 days, while lowering it to 0.30 buys 11.52 days. The latter is a 14.3% reduction in β and meets that timing goal on the sampled grid. Whether it prevents overload depends on the hospital's capacity and the admissions generated by that curve.

### Exercise 1 — Code evolution and design choices

The first check traced a single Euler update in a synthetic population of 1,000. For the portfolio, I adopted the New Haven city scenario and kept the peak annotation on the full baseline curve. I also kept the five step sizes on common axes. Both required sensitivity maps use the same transmission and removal axes and mark the baseline with a star.

### Exercise 1 — AI assistance

I used OpenAI Codex to propose the scenario, tolerances, grid and figure layouts, generate and run the Python code, and draft the computational documentation. Its checks included population conservation, clearance and comparison with the continuous-model peak.

## Exercise 2 — In silico synergy optimization

### Part 1 — API architecture and request handling

The [optimization script](optimize.py) sends a GET request to the course endpoint at `/cgi-bin/error_function.py` with dose coordinates in the query parameters `a` and `b`. The response body contains one numerical disease-burden score. The client identifies itself with a course-specific User-Agent, spaces live requests at least one second apart within a run, checks the HTTP response and keeps a persistent cache. An empty score in the [request ledger](api_scores.csv) records a failed request and counts toward the budget.

Run `python optimize.py` here with NumPy and Requests installed to reproduce the search from the ledger. This default uses zero new API requests. The explicit `--live` option retrieves missing values within the shared budget.

### Part 2 — Custom bounded gradient descent

For each axis, the solver estimates the slope from the change in burden over a dose increment of 0.00001, reusing the current score. It uses a backward difference near the upper bound. Each descent step projects both doses into [0, 1].

```python
trial = np.clip(x - step * grad, 0, 1)
trial_value = score(trial)
```

The initial learning rate is 0.15. Subsequent steps use the displacement and change in gradient to estimate a learning rate when their inner product is positive. Backtracking halves a trial step until it gives sufficient decrease. The script checks the projected gradient norm against 0.0001, caps each start at 40 iterations, and shares a 150-request ceiling across starts. All four starts reached the gradient criterion after two accepted steps.

For the start at (0.40, 0.20), the recorded burden at the initial point and the two accepted updates was 1.294915 → 1.002950 → 1.000000. The run used 9 distinct doses, including the finite-difference probes. The projected gradient norm at the last point was 0.000000 at the recorded precision.

### Part 3 — Multi-start search and optima

| Initial (a, b) | Final (a, b), rounded | Disease burden | Additional distinct doses |
| --- | --- | ---: | ---: |
| (0.40, 0.20) | (0.7120, 0.1690) | 1.00000000015 | 9 |
| (0.80, 0.80) | (0.2160, 0.6890) | 1.10000000005 | 9 |
| (0.15, 0.85) | (0.2160, 0.6890) | 1.10000000005 | 6 |
| (0.85, 0.15) | (0.7120, 0.1690) | 1.00000000015 | 6 |

The course specifies one global and one suboptimal local minimum. Under that specification, the basin near **(0.712, 0.169)** is the global minimum and the basin near **(0.216, 0.689)** is the higher local minimum. Finite differences identify both coordinates approximately. The four trajectories alone establish which observed score is lower. [Accepted trajectories, scores and stopping diagnostics](optimization.json)

### Exercise 2 — Reflection (Codex-written analysis)

The GET request makes the two dose inputs explicit and retrieves a score without requesting a change to the service. Query parameters fit that use. The path exposes the CGI script and its implementation language. A stable resource path such as `/assays/{id}/response` could preserve the same client contract if the implementation changed. Across assays, clients also need consistent dose units, score definitions and error responses before they can compare results. The custom User-Agent identifies the experiment to the operator, and the one-second interval spaces out requests.

Under the assignment's cohort analogy, each new dose evaluation has a cost. Reusing the center score cuts a two-axis forward-difference gradient to two additional probes. Sharing the ledger across starts also avoids paying twice where trajectories meet. In a noisy animal experiment, an independent replicate would supply additional evidence about variability. Replaying a cached value serves a different purpose.

A single fixed learning rate would have to suit both steep and shallow regions. The adaptive step uses the observed change in slope, then backtracks when the proposed move fails to reduce the score sufficiently. Projection keeps trial doses feasible. At a boundary, projecting the gradient step also tests whether movement in an allowed direction remains possible. Four separated starts spend some of the query budget on discovering a second basin. The gradient tolerance limits spending within each basin, and the shared budget caps the total cost even if convergence is slow.

Both minima were reached twice in this deterministic simulation. For an unknown experimental surface, agreement across starts would justify a focused confirmation experiment at the better dose pair and nearby feasible doses. A decision to advance would require a prespecified improvement over a comparator, reproducibility, safety at the proposed exposure, and evidence that small dosing errors preserve the benefit. Further searching has value when the remaining uncertainty could change that decision. The two simulated burden scores alone establish neither safety nor readiness for a clinical trial.

### Exercise 2 — Code evolution and design choices

For the portfolio, I adopted the four-start search and kept a table with one row per start. The last column counts additional distinct doses, so shared evaluations are counted only once. The request ledger also records the interrupted third run. Together these records account for **30 distinct evaluated doses in 31 request attempts**.

### Exercise 2 — AI assistance

I used OpenAI Codex to propose the starting points and numerical settings, generate the optimizer, run the live search, and verify the four trajectories by offline replay. It also drafted the computational documentation.
