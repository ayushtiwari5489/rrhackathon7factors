# Seven-Factor Player Ranking for Rajasthan Royals
**A scouting-support model for T20 and T20I batters and bowlers, built for the RR Hackathon.**

---

## Part 1: The Short Version

### What this is
A ranking model that scores **145 batters** and **140 bowlers** on seven factors and combines them into one **Final Score from 0 to 100**. It is a shortlisting tool for scouts, not an automatic selection list.

### The data at a glance

| Metric | Result |
| :--- | :--- |
| **Matches analysed** | 865 |
| **Delivery rows processed** | 196,630 |
| **Eligible batters** | 145 |
| **Eligible bowlers** | 140 |
| **Analysis period** | 22 Jan 2022 to 1 Nov 2026 |
| **Formats** | T20 and T20I |

### How the Final Score is built
Every player is turned into a percentile (0 to 100) on each of seven factors. The factors are then blended using fixed weights:

$$\text{Final Score} = 0.285 \times F_1 + 0.266 \times F_2 + 0.1805 \times F_3 + 0.1045 \times F_4 + 0.076 \times F_5 + 0.038 \times F_6 + 0.05 \times F_7$$

> **Key takeaway:** More than half of the score (**55.1%**) comes from recent consistency ($F_1$) and performance under pressure ($F_2$).

### Model Pipeline · 8 Steps from Raw File to Shortlist
$$\text{200,999 raw rows} \longrightarrow \text{196,630 filtered rows} \longrightarrow \text{0 to 100 match score} \longrightarrow \text{7 factors as percentiles} \longrightarrow \text{1 weighted blend} \longrightarrow \text{Shortlist for scouts}$$

---

### Top 10 Batters (Latest Pipeline Run)
*Top 10 of 145 eligible batters:*
1. **Maaz Sadaqat** — **82.90** *(8 matches, extreme F2/F5 scores of 100)*
2. **Harry Brook** — **81.37** *(55 matches, elite F1 and F7 scores)*
3. **Finn Allen** — **75.93** *(42 matches, explosive powerplay boundary conversion)*
4. **Daryl Mitchell** — **75.82** *(48 matches, spin handling and middle-overs pressure absorption)*
5. **Vaibhav Sooryavanshi** — **75.78** *(14 matches, fearless aggressive intent)*
6. **Abhishek Sharma** — **75.30** *(46 matches, top-order strike-rate and boundary delta)*
7. **Ashutosh Sharma** — **74.11** *(22 matches, specialist death-overs finisher)*
8. **Heinrich Klaasen** — **73.47** *(52 matches, elite middle-overs spin destroyer)*
9. **Jos Buttler** — **72.93** *(58 matches, proven match-winner, highest opposition quality)*
10. **Tim David** — **72.27** *(50 matches, death boundary hitter, clutch win contribution)*

### Top 10 Bowlers (Latest Pipeline Run)
*Top 10 of 140 eligible bowlers:*
1. **Benjamin Sears** — **78.55** *(24 matches, express 145k+ pace and steep bounce)*
2. **Gerald Coetzee** — **76.86** *(32 matches, aggressive breakthrough enforcer in collapses)*
3. **Sufiyan Muqeem** — **75.49** *(18 matches, deceptive left-arm wrist spin)*
4. **Matthew Humphreys** — **75.23** *(16 matches, slow left-arm orthodox control)*
5. **Mohammad Nawaz** — **73.62** *(45 matches, reliable finger spin containment)*
6. **Sunil Narine** — **73.34** *(54 matches, world-benchmark economy rating)*
7. **Lungi Ngidi** — **71.86** *(38 matches, deceptive seam changes and death overs execution)*
8. **Abrar Ahmed** — **71.76** *(26 matches, mystery leg-spin variations)*
9. **Rakibul Hasan** — **70.88** *(22 matches, disciplined orthodox containment)*
10. **Mahedi Hasan** — **70.64** *(36 matches, powerplay specialist off-spinner)*

### Read this before using the numbers
Maaz Sadaqat leads the batters with perfect $F_2$ and $F_5$ scores, but his model rests on **only eight matches**. Harry Brook is second with **55 matches** and strong $F_1$ and $F_7$ scores. Both profiles deserve a closer look. **A high Final Score is a reason to scout a player, not a reason to buy one.**

---

## Part 2: The Detailed Version

### 1. Dataset and Analysis Scope
The latest successful pipeline run produced **865 matches** and **196,630 delivery rows**, covering **145 eligible batters** and **140 eligible bowlers** between **22 January 2022 and 1 November 2026**. Both T20 and T20I formats are included.

The uploaded delivery file contained **200,999 rows**. The difference of 4,369 rows comes from the competition, date, and innings filters. It does not mean all excluded rows were invalid deliveries.

---

### 2. Match-Level Scoring: The Foundation
Before any factor is calculated, every player's performance in every match receives a score between **0 and 100**. All seven factors build on these match scores. They are analyst-defined scoring rubrics, not official cricket ratings.

#### Batter Match Score Components & Caps
| Component | Weight | Cap Rule |
| :--- | :--- | :--- |
| **Runs** | 35% | Capped at 60 runs |
| **Strike rate** | 25% | Capped at 200.0 |
| **Boundary-ball %** | 20% | Capped at 40.0% |
| **Dot-ball performance** | 20% | Relative inverse dot rate |

#### Bowler Match Score Components & Caps
| Component | Weight | Cap Rule |
| :--- | :--- | :--- |
| **Wickets** | 30% | Capped at 4 wickets |
| **Economy** | 25% | Lower economy rewarded |
| **Dot-ball %** | 20% | Higher dot-ball share |
| **Boundary prevention**| 15% | Lower boundaries conceded |
| **Wicket rate** | 10% | Strike-rate efficiency |

> *The caps stop a single freak innings or spell from dominating a player's record.*

---

### 3. The Seven Factors and Their Weights
All seven factors are converted to percentiles on a 0 to 100 scale before the final calculation. The final formula is:

$$\text{Final Score} = 0.285 \times F_1 + 0.266 \times F_2 + 0.1805 \times F_3 + 0.1045 \times F_4 + 0.076 \times F_5 + 0.038 \times F_6 + 0.05 \times F_7$$

The weights add up to **100%**.

---

### 4. How Each Factor Works

#### F1: Recent Consistency (28.50%)
* **Window:** 2 November 2025 to 1 November 2026.
* Looks at four things for batters and bowlers alike: how often the player scored at least 60 in the match-level model ($P_{60}$), how stable their match scores are (measured by standard deviation, $P_{\text{stability}}$), and role-specific rates.
* **Base Calculation:**
  $$F_{1\text{ base}} = 0.65 \times P_{60} + 0.35 \times P_{\text{stability}}$$
* **For Batters:**
  $$F_1 = 0.60 \times F_{1\text{ base}} + 0.20 \times P_{\text{strike rate}} + 0.10 \times P_{\text{boundary}} + 0.10 \times P_{\text{inverse dot}}$$
* **For Bowlers:**
  $$F_1 = 0.60 \times F_{1\text{ base}} + 0.20 \times P_{\text{inverse economy}} + 0.10 \times P_{\text{wicket rate}} + 0.10 \times P_{\text{dot}}$$
* **Why RR can use it:** It identifies players who repeatedly produce good performances rather than relying on one or two exceptional games.

#### F2: Pressure and Collapse Performance (26.60%)
* **Collapse Definition:** A delivery counts as a collapse situation if four or more wickets have already fallen, or at least two wickets have fallen in the preceding 18 delivery rows.
* **Pressure Definition:** A collapse situation, or a second-innings required run rate (RRR) of 9 or more.
* **For Batters:**
  $$F_2 = 0.50 \times P_{\text{pressure strike rate}} + 0.50 \times P_{\text{collapse strike rate}}$$
* **For Bowlers:**
  $$F_2 = 0.35 \times P_{\text{inverse pressure economy}} + 0.25 \times P_{\text{pressure wicket rate}} + 0.25 \times P_{\text{inverse collapse economy}} + 0.15 \times P_{\text{collapse wicket rate}}$$
* **Why RR can use it:** Highlights players whose performances deserve closer examination in difficult situations, particularly when a team is losing wickets or chasing a demanding target.

#### F3: All-Match Participant Comparison (18.05%)
* Each player's match score is compared with every other player's performance in the exact same match.
* The within-match rank is converted to a score:
  $$\text{Rank score} = 100 \times \left(1 - \frac{\text{Rank} - 1}{21}\right)$$
* The factor combines **60%** weighted within-match rank score and **40%** weighted proportion of performances that beat the mean score of the other players in that match.
* **Why RR can use it:** A player is judged against the pitch conditions and performances of the other participants, rather than only by a fixed statistical threshold.

#### F4: Opposition Strength (10.45%)
* For batters, the model considers the historical quality of the opposition bowling unit.
* For bowlers, it considers the historical quality of the opposition batting unit.
* **Strict Anti-Leakage:** Only strictly earlier match dates are used to calculate opposition quality, so future results are never used to judge an earlier performance.
* **Why RR can use it:** Gives analysts context when comparing players who have faced different levels of opposition (e.g. elite international attacks vs weaker leagues).

#### F5: Match-Winning Contribution (7.60%)
* Raw formula:
  $$F_{5\text{ raw}} = \text{mean score in wins} - \text{mean score in losses}$$
* The result is converted into a percentile. If a player has no recorded wins or no recorded losses, the factor receives a neutral score of 50.
* **Why RR can use it:** Helps investigate whether a player's individual scores tend to be stronger in victories than defeats. *(Does not prove that the player caused the victory).*

#### F6: Historical Performance (3.80%)
* Covers the period from **22 January 2022 to 1 November 2025**.
* Takes the player's mean match score in that period and converts it into a percentile.
* **Why RR can use it:** Stops the ranking from looking only at the latest season and keeps a small long-term component.

#### F7: De-overlapped Overall Performance (5.00%)
* **Most important statistically:** First, an overall performance index is built.
  * *For batters:* 60% mean match-score percentile, 20% batting-average percentile, 10% strike-rate percentile, 5% boundary-ball % percentile, and 5% inverse dot-ball % percentile.
  * *For bowlers:* 60% mean match-score percentile, 20% inverse economy percentile, 10% wicket-rate percentile, 5% dot-ball % percentile, and 5% inverse boundary-conceded % percentile.
* Then **Ordinary Least Squares (OLS) regression** is applied:
  $$F_{7\text{ base}} = \beta_0 + \beta_1 \times F_2 + \beta_2 \times F_3 + \beta_3 \times F_6 + \epsilon$$
* The residuals ($\epsilon$) are percentile-ranked to obtain $F_7$. In plain terms, the part of overall performance already explained by $F_2$, $F_3$, and $F_6$ is removed, so only the brand-new information remains.
* **Why RR can use it:** Keeps extra overall performance information without rewarding the same characteristics twice.

---

### 5. Latest Player Rankings Observations
* **Batters:** Led by Maaz Sadaqat (82.90) and Harry Brook (81.37), with a drop of more than five points to third place. Places 3 to 10 sit within about 3.7 points of each other (75.93 to 72.27), so their order is sensitive to small changes.
* **Bowlers:** More evenly spread. Benjamin Sears leads on 78.55, and the top ten span 7.91 points.

---

### 6. How RR Can Use the Results
The rankings should be used as a shortlisting and scouting-support tool, not as an automatic selection list:
1. **Player shortlisting:** Identify players who deserve deeper scouting attention.
2. **Recent performance:** Use $F_1$ to investigate repeatability and recent form.
3. **Pressure suitability:** Use $F_2$ to find players worth reviewing in high-pressure situations.
4. **Opposition context:** Use $F_4$ to understand the quality of opponents faced.
5. **Winning contribution:** Use $F_5$ to investigate the relationship between individual performances and team results.
6. **Role-based recruitment:** Further divide players by batting position, batting role, bowling type, and bowling phase.
7. **Auction preparation:** Combine the rankings with availability, price, role scarcity, squad balance, and scouting reports.

---

### 7. Reading Two Profiles Side by Side
Maaz Sadaqat leads the batter ranking with an $F_2$ score of 100 and an $F_5$ score of 100. However, his model includes only eight matches, so these extreme scores may reflect a small sample. Harry Brook ranks second, with 55 matches and strong $F_1$ and $F_7$ scores. RR should examine both profiles rather than treating the final score alone as a recruitment decision.

---

### 8. Limitations
1. Match scores are analyst-defined rubrics, not official ratings.
2. Players with few matches can receive extreme percentile scores.
3. $F_5$ shows association with winning, not causation.
4. The ranking does not yet separate players by batting position, role, bowling type, or phase.
5. Price, availability, and squad balance are outside the model.
