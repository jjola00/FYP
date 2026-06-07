# Beyond Recognition: User Study Results

**Data exported:** 2026-04-06 16:01
**Source:** Supabase (production cloud database)

---

## 1. Overview

| Metric | Value |
|--------|-------|
| Total sessions | 57 |
| Completed (questionnaire submitted) | 51 |
| Dropouts | 6 |
| Completion rate | 89% |
| Total line CAPTCHA attempts | 277 |
| Total image CAPTCHA attempts | 273 |
| Total questionnaire responses | 51 |

---

## 2. Line Tracing CAPTCHA Results

### 2a. Overall Pass Rate

**195/277 (70%)**

### 2b. Pass Rate by Input Type

| Input | Attempts | Passes | Pass Rate |
|-------|----------|--------|-----------|
| Mouse | 148 | 134 | 90% |
| Touch | 129 | 61 | 47% |

### 2c. Failure Reason Breakdown

| Reason | Count | % |
|--------|-------|---|
| `success` | 195 | 70% |
| `incomplete` | 49 | 17% |
| `non_monotonic_time` | 12 | 4% |
| `speed_violation` | 8 | 2% |
| `jump_detected` | 5 | 1% |
| `non_monotonic_path` | 5 | 1% |
| `low_coverage` | 3 | 1% |

### 2d. Solve Times (ms)

| Metric | Passes | Failures |
|--------|--------|----------|
| Min | 1276 | 227 |
| Median | 2805 | 1647 |
| Max | 5648 | 8126 |
| Mean | 2892 | 2099 |

### 2e. Coverage Ratio

| Metric | Passes | Failures | All |
|--------|--------|----------|-----|
| Min | 0.79 | 0.04 | 0.04 |
| Median | 1.00 | 0.89 | 1.00 |
| Mean | 0.99 | 0.80 | 0.94 |

### 2f. Per-Session Line CAPTCHA Results

| Session | OS | Pointer | Passed | Attempts | Pass Rate | Completed Study |
|---------|----|---------|---------|---------|-----------|----|
| `6a87ea7e` | iPhone | touch | 0 | 5 | 0% | No |
| `e2d9835f` | iPhone | touch | 0 | 4 | 0% | No |
| `fe5e97ca` | iPhone | touch | 1 | 5 | 20% | Yes |
| `b81952b2` | MacIntel | mouse | 4 | 5 | 80% | Yes |
| `fb615558` | Linux armv81 | touch | 3 | 5 | 60% | Yes |
| `529626f2` | iPhone | touch | 2 | 5 | 40% | Yes |
| `b68898b1` | iPhone | touch | 4 | 4 | 100% | Yes |
| `3f021e61` | iPhone | touch | 2 | 5 | 40% | Yes |
| `ca5a90f2` | iPhone | touch | 0 | 5 | 0% | Yes |
| `152b8fc8` | Linux armv81 | touch | 4 | 5 | 80% | Yes |
| `cb5533cf` | Linux armv81 | touch | 3 | 5 | 60% | Yes |
| `c1d27a4c` | iPhone | touch | 3 | 5 | 60% | Yes |
| `2293daa0` | Win32 | mouse | 5 | 5 | 100% | Yes |
| `3db5398b` | Win32 | mouse | 5 | 5 | 100% | Yes |
| `d4a38af7` | iPhone | touch | 3 | 5 | 60% | Yes |
| `b0c8dc26` | Linux x86_64 | mouse | 5 | 5 | 100% | Yes |
| `5e75fc73` | Win32 | mouse | 4 | 5 | 80% | Yes |
| `98342c4c` | Win32 | mouse | 5 | 5 | 100% | Yes |
| `8eeab683` | MacIntel | mouse | 4 | 5 | 80% | Yes |
| `79315c54` | MacIntel | mouse | 5 | 5 | 100% | Yes |
| `27f988c0` | iPhone | touch | 4 | 5 | 80% | Yes |
| `2ea1ddb1` | iPhone | touch | 4 | 5 | 80% | Yes |
| `1508fa05` | iPhone | touch | 2 | 5 | 40% | Yes |
| `3127f5f4` | iPhone | touch | 0 | 5 | 0% | No |
| `a410bf1f` | Win32 | mouse | 5 | 5 | 100% | Yes |
| `2c369961` | iPhone | touch | 0 | 4 | 0% | Yes |
| `2f36b3aa` | iPhone | touch | 4 | 5 | 80% | Yes |
| `740f6713` | iPhone | touch | 5 | 5 | 100% | No |
| `cf476702` | Win32 | mouse | 5 | 5 | 100% | Yes |
| `84d5a01a` | Win32 | mouse | 5 | 5 | 100% | Yes |
| `c431e125` | Win32 | mouse | 5 | 5 | 100% | Yes |
| `db6beb1f` | Win32 | mouse | 4 | 5 | 80% | Yes |
| `469bec7a` | Win32 | mouse | 2 | 5 | 40% | Yes |
| `3f2ced6e` | Win32 | mouse | 5 | 5 | 100% | Yes |
| `45bcfb57` | MacIntel | mouse | 5 | 5 | 100% | Yes |
| `63475412` | Linux armv81 | touch | 3 | 5 | 60% | Yes |
| `22ad0507` | Linux armv81 | touch | 0 | 5 | 0% | No |
| `641b423e` | iPhone | touch | 2 | 4 | 50% | Yes |
| `8c462b0d` | iPhone | touch | 1 | 3 | 33% | Yes |
| `61e46e2d` | Linux x86_64 | mouse | 5 | 5 | 100% | Yes |
| `62688a8b` | Win32 | mouse | 4 | 5 | 80% | Yes |
| `4adb4f79` | Win32 | mouse | 5 | 5 | 100% | Yes |
| `e02acaa8` | Win32 | mouse | 5 | 5 | 100% | Yes |
| `e5d3db83` | Win32 | mouse | 5 | 5 | 100% | Yes |
| `2a73ddc8` | MacIntel | mouse | 5 | 5 | 100% | Yes |
| `7dc9d1c3` | MacIntel | mouse | 1 | 3 | 33% | No |
| `a9e8b43e` | Win32 | mouse | 4 | 5 | 80% | Yes |
| `f27756fb` | Win32 | mouse | 5 | 5 | 100% | Yes |
| `3b66f52e` | iPhone | touch | 4 | 5 | 80% | Yes |
| `85220a1d` | Win32 | mouse | 5 | 5 | 100% | Yes |
| `782f4a1a` | Win32 | mouse | 3 | 5 | 60% | Yes |
| `d5b87260` | MacIntel | mouse | 5 | 5 | 100% | Yes |
| `d20ff998` | Win32 | mouse | 4 | 5 | 80% | Yes |
| `b6a0d9cf` | iPhone | touch | 2 | 5 | 40% | No |
| `9170e90a` | Win32 | mouse | 5 | 5 | 100% | Yes |
| `6524bafb` | Linux armv81 | touch | 2 | 5 | 40% | Yes |
| `c052622d` | Linux armv81 | touch | 3 | 5 | 60% | Yes |

### 2g. Behavioral Flags Triggered on Human Attempts

| Flag | Triggered | % of attempts |
|------|-----------|---------------|
| `speed_const_flag` | 4 | 1% |
| `accel_flag` | 235 | 84% |
| `behavioural_flag` | 240 | 86% |
| `speed_violation` | 19 | 6% |
| `too_perfect_flag` | 0 | 0% |

### 2h. Bot Score Distribution

| Bot Score | Count |
|-----------|-------|
| 0 | 36 |
| 1 | 201 |
| 2 | 28 |
| 3 | 12 |

---

## 3. Image Intersection CAPTCHA Results

### 3a. Overall Pass Rate

**244/273 (89%)**

### 3b. Pass Rate by Input Type

| Input | Attempts | Passes | Pass Rate |
|-------|----------|--------|-----------|
| Mouse | 133 | 120 | 90% |
| Touch | 140 | 124 | 88% |

### 3c. Failure Reason Breakdown

| Reason | Count | % |
|--------|-------|---|
| `all intersections clicked` | 244 | 89% |
| `too many extra clicks (1)` | 11 | 4% |
| `missed 1 intersection` | 11 | 4% |
| `too many extra clicks (2)` | 3 | 1% |
| `missed 2 intersections` | 2 | 0% |
| `too many extra clicks (3)` | 1 | 0% |
| `missed 3 intersections` | 1 | 0% |

### 3d. Solve Times (ms)

| Metric | Passes | Failures |
|--------|--------|----------|
| Min | 1215 | 2056 |
| Median | 3848 | 5692 |
| Max | 15387 | 18083 |
| Mean | 4494 | 7181 |

---

## 4. Questionnaire Results

**51 responses**

### 4a. Demographics

**Device types:**

- Computer: 29 (56%)
- Phone: 22 (43%)

**Age ranges:**

- 18–24: 28 (54%)
- 35–44: 9 (17%)
- 25–34: 7 (13%)
- 45–54: 7 (13%)

**Tech comfort (1=beginner, 5=daily power user):**

- 4/5: 8
- 5/5: 43

### 4b. Likert Scale Ratings (1-5)

| Metric | Mean | Median | Std Dev | n |
|--------|------|--------|---------|---|
| Line difficulty | 2.90 | 3 | 1.25 | 51 |
| Line frustration | 2.94 | 3 | 1.41 | 51 |
| Image difficulty | 1.69 | 1 | 1.05 | 51 |
| Image frustration | 1.84 | 1 | 1.17 | 51 |
| CAPTCHA encounter frequency | 3.75 | 4 | 1.00 | 51 |

### 4c. Ratings by Device Type

**Phone** (n=22):

| Metric | Mean |
|--------|------|
| Line difficulty | 3.73 |
| Line frustration | 3.91 |
| Image difficulty | 1.45 |
| Image frustration | 1.64 |

**Computer** (n=29):

| Metric | Mean |
|--------|------|
| Line difficulty | 2.28 |
| Line frustration | 2.21 |
| Image difficulty | 1.86 |
| Image frustration | 2.00 |

### 4d. Participant Comments

> "Very hard to do the trace on on phone, my thumb practically covers the path"
> -- Phone, 18–24, tech comfort 5/5

> "Trace the path is fun once you get it but I can see a lot of users finding it unintuitive and frustrating. Sometimes my cursor wouldn't release at the end. Crossings was much easier to understand first time round"
> -- Computer, 18–24, tech comfort 5/5

> "It becomes kinda hard to trace the path when my finger is blocking me from seeing it. Maybe if more of the path was visible from the start, it’d be easier to follow"
> -- Phone, 18–24, tech comfort 5/5

> "My finger was too big to drag the line."
> -- Phone, 18–24, tech comfort 5/5

> "fist spot the crossing captcha didn't load 
apart from that all good "
> -- Computer, 18–24, tech comfort 5/5

> "overall I felt either one would be an acceptable alternative to the image based CAPTCHA challenge as sometimes the items in the pictures you need to identify are not clear and obvious "
> -- Computer, 35–44, tech comfort 5/5

> "absolutely fantastic"
> -- Computer, 18–24, tech comfort 5/5

> "Harder to trace on a laptop, but as you do it more times in a row, it becomes easier"
> -- Computer, 18–24, tech comfort 5/5

> "I was too dubm to get the crossing one I first thought we need to put a dot everywhere where it ends and begins but that's just me I got the rest right"
> -- Computer, 18–24, tech comfort 5/5

> "My finger is bigger than the line so it’s hard. To see"
> -- Phone, 18–24, tech comfort 5/5

> "My thumb is in the way for the trace the path which is annoying and makes it hard to do 

Crossings is fun "
> -- Phone, 18–24, tech comfort 5/5

> "Can’t see final point of trace the path because my thumb covers it"
> -- Phone, 18–24, tech comfort 5/5

> "You are very innovative"
> -- Computer, 25–34, tech comfort 5/5

> "Wasn’t able to do trace the path probably  because I have dyspraxia, very frustrating to do "
> -- Phone, 18–24, tech comfort 5/5

> "Very easy to do!"
> -- Computer, 25–34, tech comfort 5/5

> "The path tracing CAPTCHA is difficult on mobile since your finger blocks part of the screen. Otherwise, these challenges are much less strenuous than Google's "choose the squares with X" one."
> -- Phone, 18–24, tech comfort 5/5

> "I can’t see the path under my finger "
> -- Phone, 18–24, tech comfort 5/5

> "Spot Crossing asked only two tests and then scored 2 of 5"
> -- Computer, 35–44, tech comfort 5/5

> "Novel approach to captcha, less frustrating than some current implementations where imagery is unclear and it makes you question your humanity."
> -- Computer, 45–54, tech comfort 5/5

> "The spot the crossings captcha had too many "almost" crossings that weren't obvious. "
> -- Computer, 45–54, tech comfort 5/5

> "I was a little confused on the first one as it was set to trace the path but Identify the crossing was the one i expected"
> -- Computer, 35–44, tech comfort 4/5

> "Love these approaches as they remove the subjectivity in some catchas with the pictures of random objects... the trace the path was a bit tricky though!"
> -- Computer, 45–54, tech comfort 4/5

> "I found my finger was in the way to follow the line on the Trace the Path tasks. Phone user."
> -- Phone, 25–34, tech comfort 5/5

---

## 5. Comparative Analysis

### 5a. Line vs Image CAPTCHA

| Metric | Line CAPTCHA | Image CAPTCHA |
|--------|-------------|---------------|
| Overall pass rate | 70% (195/277) | 89% (244/273) |
| Mouse pass rate | 90% (n=148) | 90% (n=133) |
| Touch pass rate | 47% (n=129) | 88% (n=140) |
| Median solve time (pass) | 2805ms | 3848ms |
| Avg difficulty (Likert) | 2.90/5 | 1.69/5 |
| Avg frustration (Likert) | 2.94/5 | 1.84/5 |

### 5b. Mouse vs Touch (Line CAPTCHA)

| Metric | Mouse | Touch |
|--------|-------|-------|
| Sessions | 30 | 27 |
| Aggregate pass rate | 90% | 47% |
| Mean per-session pass rate | 89.8% | 46.8% |

### 5c. Failure Reasons: Mouse vs Touch (Line CAPTCHA)

| Reason | Mouse | Touch |
|--------|-------|-------|
| `incomplete` | 9 | 40 |
| `jump_detected` | 0 | 5 |
| `low_coverage` | 1 | 2 |
| `non_monotonic_path` | 4 | 1 |
| `non_monotonic_time` | 0 | 12 |
| `speed_violation` | 0 | 8 |

---

## 6. Raw Questionnaire Data

| # | Session | Device | Age | Tech | Freq | Line Diff | Line Frust | Image Diff | Image Frust |
|---|---------|--------|-----|------|------|-----------|------------|------------|-------------|
| 1 | `fe5e97ca` | Phone | 18–24 | 5 | 4 | 3 | 4 | 1 | 1 |
| 2 | `35131335` | Phone | 18–24 | 5 | 2 | 4 | 5 | 2 | 1 |
| 3 | `b81952b2` | Computer | 18–24 | 5 | 5 | 3 | 3 | 1 | 1 |
| 4 | `fb615558` | Phone | 18–24 | 4 | 2 | 2 | 1 | 4 | 3 |
| 5 | `529626f2` | Phone | 18–24 | 4 | 4 | 4 | 5 | 2 | 3 |
| 6 | `b68898b1` | Phone | 18–24 | 5 | 2 | 2 | 3 | 1 | 1 |
| 7 | `3f021e61` | Phone | 18–24 | 5 | 5 | 5 | 3 | 1 | 1 |
| 8 | `ca5a90f2` | Phone | 18–24 | 5 | 4 | 5 | 5 | 1 | 1 |
| 9 | `152b8fc8` | Phone | 18–24 | 5 | 4 | 3 | 3 | 1 | 3 |
| 10 | `cb5533cf` | Phone | 18–24 | 5 | 4 | 4 | 3 | 1 | 1 |
| 11 | `c1d27a4c` | Phone | 18–24 | 5 | 3 | 4 | 4 | 1 | 1 |
| 12 | `2293daa0` | Computer | 18–24 | 5 | 5 | 1 | 1 | 1 | 1 |
| 13 | `d4a38af7` | Phone | 18–24 | 5 | 3 | 4 | 4 | 2 | 3 |
| 14 | `3db5398b` | Computer | 35–44 | 5 | 3 | 1 | 2 | 2 | 2 |
| 15 | `b0c8dc26` | Computer | 18–24 | 5 | 5 | 2 | 4 | 1 | 2 |
| 16 | `5e75fc73` | Computer | 18–24 | 5 | 5 | 5 | 5 | 5 | 5 |
| 17 | `98342c4c` | Computer | 18–24 | 5 | 3 | 1 | 2 | 1 | 2 |
| 18 | `8eeab683` | Computer | 18–24 | 5 | 3 | 1 | 2 | 1 | 1 |
| 19 | `79315c54` | Computer | 18–24 | 5 | 3 | 4 | 3 | 4 | 5 |
| 20 | `27f988c0` | Phone | 18–24 | 5 | 4 | 4 | 4 | 1 | 1 |
| 21 | `2ea1ddb1` | Phone | 18–24 | 5 | 5 | 5 | 5 | 1 | 2 |
| 22 | `1508fa05` | Phone | 18–24 | 5 | 5 | 2 | 4 | 1 | 1 |
| 23 | `a410bf1f` | Computer | 25–34 | 5 | 2 | 2 | 1 | 3 | 2 |
| 24 | `2c369961` | Phone | 18–24 | 5 | 3 | 5 | 5 | 2 | 3 |
| 25 | `2f36b3aa` | Phone | 18–24 | 4 | 4 | 3 | 3 | 2 | 2 |
| 26 | `cf476702` | Computer | 25–34 | 5 | 5 | 1 | 1 | 1 | 1 |
| 27 | `84d5a01a` | Computer | 35–44 | 5 | 3 | 2 | 1 | 1 | 1 |
| 28 | `c431e125` | Computer | 45–54 | 5 | 4 | 2 | 1 | 2 | 1 |
| 29 | `db6beb1f` | Computer | 35–44 | 5 | 3 | 3 | 4 | 3 | 2 |
| 30 | `469bec7a` | Computer | 35–44 | 5 | 3 | 3 | 4 | 1 | 5 |
| 31 | `3f2ced6e` | Computer | 35–44 | 5 | 3 | 2 | 1 | 3 | 3 |
| 32 | `45bcfb57` | Computer | 25–34 | 5 | 5 | 3 | 3 | 1 | 1 |
| 33 | `63475412` | Phone | 18–24 | 5 | 4 | 3 | 4 | 1 | 1 |
| 34 | `641b423e` | Phone | 18–24 | 5 | 2 | 5 | 5 | 1 | 2 |
| 35 | `8c462b0d` | Phone | 18–24 | 5 | 3 | 3 | 5 | 1 | 1 |
| 36 | `61e46e2d` | Computer | 18–24 | 5 | 5 | 2 | 1 | 1 | 1 |
| 37 | `62688a8b` | Computer | 35–44 | 5 | 5 | 2 | 3 | 1 | 2 |
| 38 | `4adb4f79` | Computer | 45–54 | 5 | 3 | 4 | 2 | 1 | 1 |
| 39 | `e02acaa8` | Computer | 45–54 | 5 | 5 | 2 | 2 | 2 | 4 |
| 40 | `e5d3db83` | Computer | 25–34 | 4 | 3 | 2 | 2 | 1 | 1 |
| 41 | `2a73ddc8` | Computer | 35–44 | 4 | 3 | 1 | 1 | 1 | 1 |
| 42 | `a9e8b43e` | Computer | 45–54 | 4 | 4 | 2 | 3 | 1 | 1 |
| 43 | `f27756fb` | Computer | 45–54 | 5 | 5 | 3 | 2 | 1 | 1 |
| 44 | `3b66f52e` | Phone | 25–34 | 5 | 4 | 4 | 3 | 1 | 1 |
| 45 | `85220a1d` | Computer | 35–44 | 5 | 3 | 2 | 1 | 3 | 1 |
| 46 | `782f4a1a` | Computer | 45–54 | 4 | 4 | 4 | 4 | 4 | 4 |
| 47 | `d5b87260` | Computer | 45–54 | 5 | 5 | 1 | 1 | 3 | 3 |
| 48 | `d20ff998` | Computer | 25–34 | 5 | 3 | 3 | 3 | 3 | 2 |
| 49 | `9170e90a` | Computer | 35–44 | 4 | 3 | 2 | 1 | 1 | 1 |
| 50 | `6524bafb` | Phone | 18–24 | 5 | 4 | 4 | 4 | 3 | 2 |
| 51 | `c052622d` | Phone | 25–34 | 5 | 5 | 4 | 4 | 1 | 1 |
