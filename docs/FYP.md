# Tab 1

#### Site of choice: Google Scholar


# Goal 1: Understanding beginning of CAPTCHA’s

- Search word: CAPTCHA origin
### Paper 1: A SURVEY ON CAPTCHA: ORIGIN, APPLICATIONS AND CLASSIFICATION. Saved to Zotero

- CAPTCHA = Completely Automated Public Turing Tests to Tell Computers and Humans Apart.
- Term CAPTCHA coined in 2000 by CMU team; precursors: Moni Naor (1996) automated Turing test; AltaVista (1997) early practical deployment. [Algwil, 2023]
- Core tension: usability vs. security — “easy for humans, hard for software” remains difficult to attain in one scheme. [Algwil, 2023]
- Each generation reacts to prior attacks/shortcomings → explains continual redesign (cat-and-mouse). [Algwil, 2023]
- As of 2023: a CAPTCHA that balances usability/security across devices is “still beyond reach.” [Algwil, 2023]
- Links back to Turing’s (1950) imitation game: CAPTCHA reverses it (machine tests for humans). [Algwil, 2023]
- Paper 2 link:
- Together, Algwil (2023) provides the historical lineage of CAPTCHA development, while von Ahn et al. (2003) formally define and standardize what a CAPTCHA is.
### Paper 2: CAPTCHA: Using Hard AI Problems for Security

- THE original CAPTCHA paper
- Definition (pure form):[von Ahn, 2003]
- “A program that can generate and grade tests that: (A) most humans can pass, but (B) current computer programs can’t pass.”
- They note that proving humans succeed and bots fail cannot be done mathematically, only empirically:
- For FYP, this will be handled via survey
- “A statement of the form ‘V is (α, β)-human executable’ can only be proven empirically.”
- The paper also emphasizes that CAPTCHA systems should remain publicly available and transparent, stating that:
- “V should be a program whose code is publicly available.”
- This underlines a core cybersecurity principle that true security should rely on the hardness of the underlying AI problem, not secrecy of the algorithm.
- The authors argue that breaking a CAPTCHA is equivalent to advancing AI as “any program that has high success over V can be used to solve a hard AI problem.”
- These ideas created the foundation of all subsequent CAPTCHA research
# Goal 2: Researching the Dual-Defense Plan

Context/Motivation (2024–2025): Modern multimodal AI and object detectors solve most conventional CAPTCHAs  Wu et al. (2025) ; bots can also reliably  mimic behavior (mouse/typing). Wei et al. (2019)

#### Defense 1 – Trace-the-Path (Motor-Control CAPTCHA)

- Current attack gap: Modern bots can imitate cursor motion statistically but still struggle to reproduce fine-grained neuromotor patterns that come from human muscle control. Behavioral mimicry CAPTCHAs exist, yet few truly analyze how motion unfolds in real time.
- Proposed defense: The user traces or follows a simple curve once using a mouse or touch input. The system evaluates trajectory dynamics—velocity, acceleration, micro-jitter, and hesitation timing—rather than the final drawing.
- Why it works: This moves CAPTCHA strength from image or text recognition into the motor-control domain, an area still underexplored by current AI. Each path is procedurally generated per session, removing any pre-training advantage.
- Novelty: Combines motion biometrics with short-lived, per-session paths and optional micro-gestures, producing a unique interaction that is quick for humans but costly to automate or relay.
- Weakness: Advanced reinforcement-learning bots could learn to emulate human-like noise; device variability (mouse vs. touch) may affect usability if not calibrated.
#### Defense 2 – Ephemeral Visual-Reasoning CAPTCHA

- Current attack gap: Vision-language and object-detection models now solve almost all image CAPTCHAs, but they remain weak at instant abstract reasoning and perceptual illusions. These cognitive challenges are largely unexploited in deployed systems.
- Proposed defense: Present a one-click abstract or illusion-based puzzle generated in real time—e.g., “click the asymmetric shape” or “choose the next item in the sequence.” Each challenge exists only once, per session.
- Why it works: Tests human intuition and contextual reasoning instead of recognition. The puzzle disappears quickly, leaving no reusable data for model training or relay attacks.
- Novelty: Uses procedural, per-session generation of minimal-friction puzzles grounded in human perception. Tasks last seconds and rely on intuition, keeping user satisfaction high while resisting dataset-driven AI solvers.
- Weakness: Future AI models with stronger reasoning could close the gap; some puzzles may risk higher cognitive load if not tuned for clarity and speed.
Stretch Goal: Combine both defenses and see if it would reduce ai ability to solve


### Paper 3: CAPTCHAs as a Moving-Target Defense  [Antoniu‑Ioan,2025]

- Search word: captcha attacks and defenses
- Basis for defense 2
- Frames CAPTCHAs as Moving Target Defense (MTD): unpredictability, per-session variation, increased attacker cost.
- Connecting to cat-and-mouse dynamic (Algwil, 2023) → adaptability is essential.
- Motivates procedural, per-session generation with usability in mind. [Antoniu‑Ioan, 2025]
- CAPTCHAs should balance usability and adaptive unpredictability.

### Paper 4: BeCAPTCHA: Behavioral bot detection using touchscreen and mobile sensors benchmarked on HuMIdb[Acién et al., 2021]

- Search word: behavioural captcha
- Proposes drag-and-drop (swipe) + touchscreen + accelerometer features to capture neuromotor signals.
- Evaluates against GAN/handcrafted synthetic gestures; shows discriminative power of human motion patterns.
- Strong empirical foundation for motor-control style CAPTCHAs. [Acién, 2021]
- Paper eludes to behavioural CAPTCHA’s being the most resistant
- Agree or disagree through findings
- Human behaviour data was extracted via samples
- Bots were generated
- Introduces HuMIdb, a multimodal dataset (600 users, 14 sensors) for studying real human-mobile interaction
- TODO explore weaknesses and specific improvements
- Find supporting papers on getting data for human behaviour
- Straight away dataset is public, AI can train on it. How to get around this?

# Goal 3: Understanding attacks (and defenses)

### Paper 5: Recognizing objects in adversarial clutter: breaking a visual CAPTCHA

#### 2003: Attack(text

- THE original Attack CAPTCHA paper
- Paper 5: Recognizing Objects in Adversarial Clutter: Breaking a Visual CAPTCHA — [Mori & Malik, 2003] - Breaks EZ‑Gimpy ~92%; Gimpy ~33% via shape contexts; concludes EZ‑Gimpy no longer suitable.
- Establishes CAPTCHAs as moving targets: when AI improves, deployed schemes fail. [Mori & Malik, 2003]
- Kick started the cat-and-mouse cycle
#### 2005: Defense (image pivot)

- IMAGINATION: a robust image-based CAPTCHA generation system — [Datta et al., 2005] - Early pivot from text to images: controlled distortions on natural images; user selects label from curated list.
- Aim: human clarity + CBIR/recognition resistance; improved satisfaction vs. text. [Datta, 2005]
#### 2011: Attack(large-scale text fragility)

- Text-based CAPTCHA Strengths and Weaknesses — [Bursztein et al., 2011]
-  13/15 popular text CAPTCHAs vulnerable to Decaptcha. Only Google and reCAPTCHA resist
- Segmentation is chokepoint; background noise ineffective. Hurts users more than machines [Bursztein, 2011]
- “By 2011, a single generic tool (Decaptcha) could break 13/15 popular text CAPTCHAs, showing that segmentation-centric defenses and background noise were fundamentally fragile.Only Google and reCAPTCHA held up under their methodology.”
#### 2014: Attack(text effectively obsolete)

- Multi-digit Number Recognition… — [Goodfellow et al., 2014] - Unified deep CNN (end-to-end) achieves 99.8% on hardest reCAPTCHA text → text CAPTCHAs effectively obsolete for security. [Goodfellow, 2014]
- “We show that we are able to achieve a 99.8% accuracy on the hardest reCAPTCHA puzzle.”
- With text CAPTCHAs effectively obsolete, deployments shifted toward image-focused challenges (e.g., object selection/grids) — a direction foreshadowed by Datta et al. (2005) IMAGINATION, which had already pivoted from text segmentation to image understanding.
- unCaptcha (WOOT’17) — automated solving of reCAPTCHA audio with high success(‘85.15% accuracy’); accessibility channel compromised. [unCaptcha, 2017]
- Link in with above para on text and audio obsolete
#### 2014: Defense (reCAPTCHA v2)

- Google pivot to reCAPTCHA v2 by introducing ‘NO-CAPTCHA’
- Checkbox + risk analysis; low-risk pass silently; higher-risk get image-selection grids; extensive environment checks. [Google, 2014]
- Google acknowledge arms race
- ‘economic incentives have resulted in an arms race, where fraudsters develop automated solvers and, in turn, captcha services tweak their design to break the solvers.’
#### 2019: Attack (image, online)

- Google’s reCAPTCHA v2 is compromised
- ImageBreaker — first fully online break of reCAPTCHA v2 image grids; ~92.4% in 14.86s avg; ~95% offline; works on static & dynamic grids. [ImageBreaker, 2019]
- Nice definition from Hossen et al.(2019)
- Google’s reCaptcha v2 is adopted by millions of websites. Its motto (principle) is to create a task that is “Easy for humans, hard for bots.”
#### 2018: Defense (reCAPTCHA v3)

- Score‑based (0.0–1.0), no visible challenge; background risk + “actions”; reduces friction. [Google, 2018]
#### 2018 -: (reCAPTCHA v3 limitations)

- Score manipulation reported in lab settings via mouse‑trajectory RL/spoofing → behavior-only scoring can be gamed. [v3‑bypass study]
- Akroul et al. (2019) ‘proposed method achieves a success rate of 97.4% on a 100 × 100 grid’.
- Behavioural scoring can be compromised under certain conditions
- Any behavior-only check is attackable without extra signals.
- Arms Race Summary
- Text: broadly fragile by 2011; 99.8% reCAPTCHA text reading by 2014.
- Image + risk (v2): reduces friction but audio/image channels automated by 2017–2019.
- Score-only (v3): fewer prompts but behavioral spoofing possible in controlled settings.
- Therefore, next section evaluates defenses beyond recognition:
- Motor‑control trajectory signals (how actions are performed; anti‑spoof design, short TTL, per‑session paths).
- Ephemeral abstract/illusion puzzles (procedural generation; per‑session uniqueness; short TTL, minimal relay surface).
# Research Question

Do CAPTCHAs that incorporate Moving Target Defense (MTD) principles—using per-session procedural generation, polymorphism, and short TTL—reduce automated attack success and increase attacker cost while preserving human usability, compared to their static equivalents, and does this effect differ between (a) motor-control trajectory and (b) visual-reasoning CAPTCHAs?


# Beyond Recognition

    Beyond Recognition


Reframing CAPTCHAs as Human-Usable

Moving Target Defences


Oluwajomiloju Olajitan

23373326


Department of Computer Science and Information Systems

Faculty of Science and Engineering

University of Limerick


Submitted to the University of Limerick for the degree of

Bsc. in  Immersive Software Engineering   academic year 2025/26


Supervisor: Dr. Salaheddin Alakkari

University of Limerick

Ireland


Supervisor: Dr. Roisin Lyons

University of Limerick

Ireland


## Abstract

CAPTCHAs (Completely Automated Public Turing tests to tell Computers and Humans Apart) have evolved from distorted text to behavioural and risk-scored mechanisms amid a persistent cat-and-mouse dynamic. This paper traces the history of CAPTCHAs from early AI-hard puzzles through image grids and “invisible” behavioural signals to current challenges posed by deep-learning solvers, low-latency relay markets, and human-like automation. This paper frames CAPTCHAs through the lens of Moving Target Defense (MTD), emphasizing how per-session procedural generation, polymorphism, and short time-to-live (TTL) increase attacker uncertainty and cost. Building on this theory, the paper designs and implements two prototype defenses: (a) a motor-control, trajectory-based challenge that evaluates neuromotor dynamics rather than static end-points; and (b) an ephemeral visual-reasoning challenge with one-click prompts and abstract/illusion-style stimuli that favour human perceptual intuition over dataset-driven recognition. The paper outlines an evaluation plan combining automated attack pipelines with a human user study measuring success rate, solve time, and frustration. Contributions include a historical synthesis of the CAPTCHA arms race, an MTD-oriented design framework which defines the basis for both CAPTCHA challenge families, and an experimental protocol to test whether these designs can improve security while preserving user satisfaction.


## Declaration

I herewith declare that I have produced this paper without the prohibited assistance of third

parties and without making use of aids other than those specified; notions taken over directly

or indirectly from other sources have been identified as such. This paper has not previously

been presented in identical or similar form to any other Irish or foreign examination board.

The thesis work was produced under the supervision of Dr. Salaheddin Alakkari and Dr. Roisin Lyons at University of Limerick


## Ethics Declaration

I herewith declare that my project involves human participants and that I have received approval from the Science and Engineering Ethics Committee prior to undertaking this part of the project. The application number for this project is:


## Table of Contents


## I. Introduction


### A. Summary


CAPTCHAs (Completely Automated Public Turing tests to tell Computers and Humans Apart) operate as a verification layer designed to separate human activity from automated threats such as fake registrations, credential stuffing, and scraping. The 2025 Bad Bot Report accounts for automation making up "51% of all web traffic", surpassing human traffic for the first time in a decade (Imperva, 2025). Yet CAPTCHAs also impose friction on legitimate users, creating tension between security and usability.


Since their formalization by von Ahn et al. (2003) as "hard AI problems, p. 299" that humans solve easily but machines cannot, CAPTCHAs have evolved through successive generations—from distorted text through image grids to behavioral scoring—yet each generation has succumbed to advancing AI capabilities. Creating tests that remain "easy for humans, hard for bots" (Hossen et al., 2019, p. 10) has proven elusive, and as of 2023, a CAPTCHA that balances usability and security across devices remains "still beyond reach" (Algwil, 2023, p. 3).


This persistent failure of static designs suggests a fundamental problem: When the core signal is learnable at scale, the CAPTCHAs effective lifespan shrinks. This evolution can be reframed through the lens of Moving Target Defense (MTD), a cybersecurity paradigm where defenders continually alter system properties to increase attacker uncertainty and cost (Jajodia et al., 2011). Applied to CAPTCHAs, MTD principles such as per-session procedural generation, high polymorphism, and short time-to-live (TTL) aim to reduce solver effectiveness and longevity by denying stable training data and compressing relay windows (Antoniu-Ioan, 2025).


As AI-driven automation grows and legitimate AI crawlers increase background bot activity, security layers must become more intent-sensitive and adaptive to avoid false positives while deterring adversaries (Cloudflare, 2024). The proposed MTD-oriented approach treats CAPTCHAs as dynamic, procedural systems rather than static puzzles, aligning defensive agility with the pace of offensive innovation.


### B. Research Question


This study addresses the following overarching research question:

Do CAPTCHAs that incorporate Moving Target Defense (MTD) principles reduce automated attack success and increase attacker cost while preserving human usability, compared with their static equivalents?

A secondary sub-question further investigates the dilemma:

Does this effect vary between (a) motor-control trajectory challenges and (b) visual-reasoning challenges?

To address these questions, two prototype CAPTCHAs are developed and evaluated through automated attack simulations and human user studies measuring success rate, completion time, and frustration.

### C. Contributions


Within this context, this paper makes three contributions. First, it provides a historical synthesis of the CAPTCHA arms race, documenting how improvements in machine perception and relay economics have repeatedly shortened the half-life of static designs. Second, it presents an MTD-oriented design framework arguing that its core principles are capable of raising attacker cost without overwhelming users. Third, it implements two prototype defenses that realise this framework: a motor-control challenge evaluating trajectory dynamics (velocity, acceleration, micro-jitter, hesitation) and a visual-reasoning challenge presenting one-click prompts over abstract or illusion-style stimuli. Both are procedurally generated per session, include multiple polymorphic families, and use short TTLs to minimise reuse and relay value.

## II. Literature Review


### A. From AI-hard text puzzles to image prompts


Von Ahn et al. (2003) defined CAPTCHAs as public tests that most humans can pass but programs cannot, with effectiveness demonstrated empirically. Framed as a reversed Turing test where machines, rather than humans, assess intelligence. This ties CAPTCHA security directly to AI capability: a system that consistently passes a CAPTCHA has, by definition, mastered the underlying AI-hard task and thus advances the state of AI.


Historical surveys trace the lineage from Naor's 1996 "automated Turing test" through the coinage of CAPTCHA at Carnegie Mellon in 2000 and early practical deployments at AltaVista (Algwil, 2023). These accounts highlight a persistent usability–security tension that drives continual redesign: schemes must be simple enough for diverse human users yet complex enough to resist automated solvers. Early deployments relied on distorted text to exploit weaknesses in optical character recognition, but even at this stage the balance between human solvability and machine resistance remained elusive.


As the limitations of text segmentation became apparent, research pivoted to image-based generation. Datta et al. (2005) demonstrated IMAGINATION, which applied controlled distortions to natural images and required users to select labels from curated lists. The system aimed for human clarity while resisting content-based image retrieval, anticipating an industry-wide shift toward image prompts. In parallel, attack work showed how incremental advances in computer vision could invalidate deployed schemes: Mori and Malik (2003) broke EZ-Gimpy at 92% success using shape context matching and concluded that the scheme was no longer suitable for security purposes. This established the cat-and-mouse dynamic of defensive pivots followed by methodical breaks that has recurred throughout subsequent generations.


### B. Collapse of recognition-centric CAPTCHAs


By 2011, research revealed systemic fragility in text-based schemes. Bursztein et al. (2011) tested 15 popular text CAPTCHAs and found that 13 were vulnerable to a single generic breaking pipeline (Decaptcha), with segmentation serving as the primary chokepoint. Crucially, the study demonstrated that background noise and distortion often harmed legitimate users more than they hindered automated solvers, undermining the usability–security balance. Google's reCAPTCHA was part of the few schemes that resisted the methodology, foreshadowing the eventual industry consolidation around a few providers.


The vulnerability of text CAPTCHAs accelerated dramatically with deep learning. Goodfellow et al. (2014) applied an end-to-end convolutional neural network to multi-digit street number recognition and achieved 99.8% accuracy on the hardest reCAPTCHA text challenges. This result effectively ended text CAPTCHAs as a viable security control, as the unified architecture bypassed traditional segmentation stages entirely. The shift toward image-based prompts, already underway with IMAGINATION, became industry standard as providers introduced "No-CAPTCHA" experiences combining lightweight checkbox interactions for low-risk traffic with escalating object-selection grids for suspicious sessions (Google, 2014).


However, image-based schemes also proved vulnerable. Sivakorn et al. (2016) demonstrated deep learning attacks against reCAPTCHA v2's semantic image challenges, achieving 70.78% success on image grids and 83.5% on Facebook's image CAPTCHA. Hossen et al. (2019) refined this approach with ImageBreaker, the first fully online system to break reCAPTCHA v2 image grids, achieving 92.4% success in 14.86 seconds per challenge. The system worked against both static and dynamic grids, showing that real-time object detection pipelines could operate at practical speeds. Simultaneously, Bock et al. (2017) automated reCAPTCHA's audio accessibility channel with 85.15% accuracy, demonstrating that alternative modalities intended for accessibility were equally compromisable. Together, these results compressed the half-life of static, recognition-centric artifacts across text, image, and audio domains.


### C. Behavioural scoring and spoofing risks


To reduce visible friction while maintaining security, providers shifted toward invisible behavioral assessment. ReCAPTCHA v3, introduced in 2018, replaced on-screen challenges with continuous risk scoring based on mouse movements, click patterns, and environmental signals, returning a score between 0.0 and 1.0 that websites could use to make access decisions (Google, 2018). This approach aimed to eliminate user friction entirely for legitimate traffic while escalating only high-risk sessions.


However, evidence quickly emerged that behavior-only scoring remained vulnerable to sophisticated attacks. Akroul et al. (2019) applied reinforcement learning to model mouse trajectories, training an agent that mimicked natural cursor movement to navigate the grid with near perfect accuracy. The method achieved 97.4% success on a 100×100 grid and 96.7% on full screen resolution, demonstrating that behavioral signals, when stable and observable, could be replicated through trial-and-error optimization. Similarly, Tan et al. (2019) explored adversarial attacks on mouse dynamics authentication, showing that generative approaches—including statistics-based, imitation-based, and surrogate-based strategies—could produce cursor paths that evaded behavioral classifiers, particularly when attackers could approximate the authentication model's architecture.


These findings illustrate a broader pattern: any stable, observable single-channel signal becomes modelable under sustained adversarial attention. Behavioral scoring that relies on consistent features (e.g., velocity histograms, pause durations) without additional layers of unpredictability risks the same fate as earlier recognition-based schemes. This line of work clarified that behavior alone, when static and learnable, does not provide durable resistance and motivated exploration of designs that restrict observability, vary stimuli dynamically, and limit useful feedback to attackers.


### D. Behavioural signals and neuromotor dynamics


A complementary research direction moved beyond recognition tasks toward capturing how users interact with interfaces. The premise is that human motor control exhibits fine-grained dynamics that reflect neuromotor processes difficult for machines to replicate convincingly, even when statistical properties can be approximated.


Acién et al. (2021) proposed BeCAPTCHA, a behavioral bot detection system using touchscreen and mobile sensor data. The study collected multimodal interaction traces from 600 users performing drag-and-drop tasks, capturing 14 sensor streams including touch coordinates, accelerometer, gyroscope, and magnetometer data. Analysis demonstrated that human neuromotor patterns exhibited distinctive characteristics that distinguished them from automated inputs. The authors reported high separability between human and bot samples, suggesting that behavioral biometrics could form a robust CAPTCHA foundation.


Wei et al. (2019) extended this line of inquiry to mouse dynamics for web bot detection, applying convolutional neural networks to representations of mouse movement data converted into images encoding spatial and kinematic information. Their approach achieved 96.2% detection of bots with statistical attack capability, significantly outperforming traditional methods using handcrafted features or recurrent neural networks. The study highlighted that deep learning could automate feature extraction from behavioral traces, capturing subtle patterns that distinguish human control from programmatic emulation.


However, practical caveats emerged from this research. Device variability complicates calibration as mouse-based interaction differs substantially from touchscreen gestures, requiring separate models or adaptive thresholds. Public datasets such as HuMIdb, while valuable for benchmarking, also enable adversaries to train imitation models, raising the risk that widely-shared behavioral signatures become replicable. Additionally, stable feedback loops (attackers observe classifier responses and iteratively refine synthetic trajectories) can aid emulator training, as demonstrated by reinforcement learning approaches to reCAPTCHA v3.

These considerations collectively point toward designs that restrict observability (e.g., limiting solver feedback), vary stimuli dynamically (procedural path generation rather than fixed templates), and impose short interaction windows (reducing time for trial-and-error refinement). The motor-control CAPTCHA paradigm thus benefits from coupling behavioral analysis with Moving Target Defense principles: evaluating dynamics rather than end-points, generating unique challenges per session, and expiring samples quickly to limit adversarial learning.


### E. Ephemeral visual reasoning beyond dataset reuse


As modern vision-language models (VLM) and object detectors began matching or exceeding human performance on recognition benchmarks, research turned toward visual reasoning challenges that shift difficulty from pattern matching to rapid perceptual inference. These designs propose one-click, ephemeral prompts (selecting the asymmetric shape, identifying the next item in a short sequence) generated procedurally per session and expiring within seconds. The goal is to exploit perceptual and cognitive faculties that humans perform intuitively through techniques like top-down processing, whereas deep learning models, despite strong recognition accuracy, often falter on novel or counter-intuitive patterns that deviate from regularities.


Wu et al. (2025) introduced MCA-Bench, a multimodal benchmark evaluating CAPTCHA robustness against VLM attacks. The study fine-tuned specialized cracking agents for diverse CAPTCHA categories (text, image, interactive puzzles) and demonstrated that challenge complexity, interaction depth, and model solvability interrelate in measurable ways. Critically, the findings revealed that while contemporary VLMs excel at static recognition tasks, they remain comparatively weak on challenges requiring abstract reasoning under strict time constraints.


This addresses two attack vectors simultaneously. First, they limit dataset accumulation: if each challenge is unique and expires quickly, adversaries cannot build large categorised datasets for supervised learning, and crowdsourced labeling services lose value when solutions cannot be reused. Second, they constrain relay attacks: the combination of short TTL and rapid expiration compresses the window for forwarding challenges to human solvers, increasing coordination costs and reducing success rates.


However, this approach may come at the cost of usability. Abstract or cognitively challenging puzzles may frustrate users or exclude individuals with cognitive differences, undermining accessibility. Effective CAPTCHAs must balance cognitive challenge with speed and clarity, and tasks should be resolvable by most humans within 2-3 seconds based on intuition, without requiring specialized knowledge or extended deliberation. Pilot testing and iterative refinement are essential to gauge difficulty, ensure cross-demographic solvability, and maintain the "easy for humans" criterion.


### F. CAPTCHAs through the lens of Moving Target Defense


Moving Target Defense (MTD) emerged in cybersecurity as a paradigm shift from static defensive postures to continuous, proactive reconfiguration of system properties. Jajodia et al. (2011) articulated MTD's core principle of creating asymmetric uncertainty and cost for adversaries by deliberately and dynamically changing the attack surface, forcing attackers to invest repeatedly in reconnaissance, exploit development, and adaptation rather than achieving durable compromises through one-time efforts. MTD techniques include address space randomization, network topology shuffling, software diversity, and dynamic configuration changes which are each aimed at invalidating attacker assumptions and making learned intelligence ephemeral.


Applied to CAPTCHAs, Antoniu-Ioan (2025) framed these challenges as natural instances of Moving Target Defense. Each CAPTCHA instance is, by design, randomly generated per session, aligning with MTD's goal of increasing system unpredictability. The treatment emphasises three specific levers that operationalise MTD principles for CAPTCHA design:

- Per-session procedural generation: Rather than drawing from a fixed pool of challenges, the system generates each instance algorithmically at request time using fresh random seeds. This eliminates the possibility of attackers pre-solving a finite challenge set or training models on exhaustive samples. Procedural generation also enables arbitrarily large challenge spaces, ensuring that even if attackers accumulate solved examples, the coverage remains statistically negligible.
- High polymorphism across challenge families: Instead of relying on a single challenge type (e.g., only text distortion or only image grids), MTD-oriented CAPTCHAs incorporate multiple orthogonal families—motor-control trajectories, abstract visual reasoning, sequence completion, illusion resolution—that require fundamentally different solver architectures. Polymorphism raises the bar for generalizable attacks as an attacker capable of solving one family efficiently must develop entirely separate pipelines for others, multiplying development costs and reducing the return on investment for solver infrastructure.
- Short time-to-live (TTL): Each challenge is bound to a cryptographic nonce with a brief validity window (e.g., 6 seconds in the current prototype). After expiration, the challenge cannot be resubmitted, and the associated solution becomes worthless. Short TTL directly targets relay attacks by compressing the time available for forwarding challenges to human solvers and returning responses. It also limits the window for iterative solver refinement: if an attacker's automated solver fails initially, the challenge expires before adjustments can be tested, forcing the attacker to request a fresh (different) challenge and reducing the utility of trial-and-error learning.

Together, these levers reduce the reuse value of learned policies and labeled data, complicate solver generalization across modalities, and compress the time available for coordinated relays. This framing places agility at the center of durability, aligning with surveys documenting the repeated shortening of security half-life for static artifacts (Algwil, 2023; Xu et al., 2020). The MTD perspective rejects the assumption that CAPTCHA security derives from obscuring the challenge generation algorithm (security through obscurity) and instead embraces transparency: the algorithm can be public, as von Ahn et al. (2003) originally advocated, because security rests on the hardness of dynamically generated instances and the inability of attackers to leverage prior solutions or stable patterns.


### G. Evaluation patterns in the literature


Two evaluation strands recur across CAPTCHA research, reflecting the dual requirements of security and usability. First, automated attack evaluation tests schemes against contemporary solver technologies to measure resistance. For recognition-based CAPTCHAs (text, image, audio), studies deploy vision pipelines using state-of-the-art object detectors (YOLO, Faster R-CNN) or vision-language models (CLIP, ViT) to approximate adversarial capabilities. For behavioral CAPTCHAs, evaluation involves trajectory emulators—either heuristic models that replicate statistical properties of human movement or reinforcement learning agents that learn policies through interaction—to assess whether synthetic patterns can evade detection.


Metrics in this strand include solver success rate (percentage of challenges correctly solved), attempts-per-success (number of tries needed per successful solution, reflecting solver brittleness), mean time-to-solve (including both algorithmic latency and any required human relay time), and degradation under constraints (shortened TTL or increased polymorphism). These measures quantify attacker cost and the robustness of defensive mechanisms. Studies often report results across multiple difficulty levels or challenge families to map the vulnerability spectrum and identify weak points.


Second, human-centered usability studies measure whether defenses remain practical for legitimate users. Participants complete sequences of CAPTCHA challenges under controlled conditions, and researchers record success rate (percentage of challenges users solve correctly), time-to-solve (median and variance), and subjective frustration or satisfaction (typically via Likert-scale ratings). These metrics directly address the "easy for humans" requirement and ensure that security improvements do not degrade user experience unacceptably. Usability testing often includes diverse device types (mouse versus touchscreen), demographic groups, and accessibility considerations to verify cross-population solvability.


The dual-strand evaluation approach reflects von Ahn et al.'s (2003) original emphasis on empirical validation: because formal proof of human-computer separability is impossible, effectiveness must be demonstrated through direct measurement. Best practices emerging from the literature include pilot testing to calibrate challenge difficulty and thresholds, controlled hardware and network settings for automated solvers to isolate performance factors, repeated runs across fresh procedural seeds to account for generative variance, and statistical rigor (effect sizes, confidence intervals) in reporting results. These practices enable reproducibility and fair comparison across studies.


### H. Synthesis and identified gap


Across two decades of research and deployment, a consistent pattern emerges: once a CAPTCHAs discriminative signal becomes learnable at scale its durability collapses. Advances in machine perception (from shape contexts to end-to-end convolutional networks to vision-language models) and solver orchestration erode recognition-centric defenses and single-channel behavioral signals. The cat-and-mouse dynamic persists because static artifacts provide stable training targets: attackers accumulate labeled data, refine models offline, and eventually surpass human-level performance on specific challenge types, as demonstrated by the progression from text breaking (Mori & Malik, 2003; Goodfellow et al., 2014) through image grids (Sivakorn et al., 2016; Hossen et al., 2019) to behavioral spoofing (Akroul et al., 2019; Tan et al., 2019).


Literature casting CAPTCHAs as Moving Target Defense argues for agility in contrast to their static counterparts (Antoniu-Ioan, 2025), claiming MTD principles aim to deny attackers stable training distributions, reusable solutions, and extended time windows for relay coordination or iterative refinement. Motor-control challenges that evaluate trajectory dynamics rather than end-points, and ephemeral visual reasoning prompts that favor quick perceptual intuition, represent instantiations of this philosophy: they shift difficulty onto axes where humans retain practical advantages while constant change undermines solver persistence.


However, evidence that jointly measures attacker success, attacker cost, and human usability under these specific MTD levers remains limited, particularly interaction types such as motor control and visual reasoning. Prior studies typically evaluate single challenge types in isolation, report offline attack results without TTL constraints, or omit comparative baselines between static and dynamic variants. The gap is an empirical test of whether procedurally generated, polymorphic, TTL-bound CAPTCHAs measurably improve the security-usability tradeoff compared to static equivalents, and whether the effect magnitude differs between behavioral (motor) and cognitive (visual reasoning) challenges. Controlled experiments that isolate MTD effects are needed to establish whether dynamism measurably improves the attacker-defender asymmetry without degrading practical usability.


## III. Methodology


This study aims to evaluate two CAPTCHA prototypes: (i) a motor-control, trajectory-based challenge and (ii) an ephemeral visual-reasoning challenge. This paper's methodology integrates techniques from prior empirical studies, specifically motion feature extraction following Acién et al. (2021) and MTD principles applied by Antoniu-Ioan (2025). These inform the hypotheses, metrics, and baseline comparisons carried out.


Prototypes are implemented as a web application with a Python/FastAPI backend for challenge generation and logging, and a JavaScript Canvas frontend for rendering and input capture. A new challenge instance is generated per session. The motor-control task elicits a single trace-the-path action and logs velocity, acceleration, and micro-jitter, while the visual-reasoning task presents one-click abstract or illusion prompts that expire rapidly and records selection accuracy and response time. All interaction data—timestamps, outcomes, device class, and trajectory samples where applicable—are anonymised and stored in SQLite/PostgreSQL.


Evaluation proceeds along two streams. Automated attacks include a ViT/YOLO vision pipeline for visual puzzles, a reinforcement-learned or heuristic trajectory emulator for motor control, and a relay simulation with injected delay to probe TTL sensitivity (Wu et al., 2025). Metrics comprise solver success, attempts-per-success, mean time-to-solve, and degradation as TTL shortens. The human-usability study (30+ adults) requires participants to complete balanced sequences of both CAPTCHA types on mouse and touch devices; success, completion time, and five-point frustration ratings are recorded. Target thresholds are set at ≥90% human success and ≤3 seconds median completion time; static non-MTD baselines such as challenges with fixed patterns and no TTL constraints are included for comparison to isolate the effect of MTD principles.


The gathered data is analysed using descriptive summaries and inferential tests (t-tests or Mann–Whitney U as appropriate), reporting effect sizes and 95% confidence intervals. Reliability is supported by the pilot phase to refine thresholds, fixed hardware and network settings for automated tests, and repeated solver runs across fresh procedural seeds to account for generative variance. Limitations include modest sample size, device variability (mouse versus touch), simplified attack models relative to industrial adversaries, and absence of long-term field deployment; nonetheless, the design provides a controlled, replicable basis to test whether MTD principles measurably reduce automated success while preserving practical usability.


### A. Ethical Considerations


This study involves human participants and requires approval from the University of Limerick Science and Engineering Ethics Committee. A Science and Engineering Expedited Application will be submitted prior to participant recruitment (application reference: [TO BE ASSIGNED]). No human testing will commence until written approval is received. Participants will be adults aged 18 or over who provide informed consent. All interaction data (timestamps, success outcomes, device class, and trajectory samples) will be anonymised at the point of collection, with no retention of personally identifiable information. Data will be archived in accordance with university research data management policies.


### B. Risk Mitigation and Limitations


Several methodological risks are acknowledged and mitigated. Ethics approval timelines (4-8 weeks) are accommodated by early application submission in the project's initial phase. Device variability between mouse and touchscreen inputs is addressed through device-specific threshold calibration and separate statistical analyses per input modality. Limited participant availability, which could degrade statistical power, is mitigated via pilot testing to refine protocols and the use of non-parametric tests suitable for smaller samples. Technical risks are managed through extensive pre-study testing, logging, and fallback to static challenge variants if system failures occur during data collection. Study limitations include modest sample size relative to large-scale industry deployments, simplified attack models compared to industrial adversaries with greater resources, and absence of long-term field deployment data. Nonetheless, the controlled experimental design provides a replicable basis for isolating MTD effects and testing whether procedural generation and TTL constraints measurably improve security-usability tradeoffs.


## IV. Bibliography


‘2025 Bad Bot Report’ (n.d.) Resource Library, available: https://www.imperva.com/resources/resource-library/reports/2025-bad-bot-report/ [accessed 5 Nov 2025].

Acien, A., Morales, A., Fierrez, J., Vera-Rodriguez, R., and Delgado-Mohatar, O. (2021) ‘BeCAPTCHA: Behavioral bot detection using touchscreen and mobile sensors benchmarked on HuMIdb’, Engineering Applications of Artificial Intelligence, 98, 104058, available: https://doi.org/10.1016/j.engappai.2020.104058.

von Ahn, L., Blum, M., Hopper, N.J., and Langford, J. (2003) ‘CAPTCHA: Using Hard AI Problems for Security’, in Biham, E., ed., Advances in Cryptology — EUROCRYPT 2003, Berlin, Heidelberg: Springer, 294–311, available: https://doi.org/10.1007/3-540-39200-9_18.

Akrout, I., Feriani, A., and Akrout, M. (2019) ‘Hacking Google reCAPTCHA v3 using Reinforcement Learning’, available: https://doi.org/10.48550/arXiv.1903.01003.

Algwil, A.M. (2023) ‘A SURVEY ON CAPTCHA: ORIGIN, APPLICATIONS AND CLASSIFICATION’, Journal of Basic Sciences, 36(1), 1–37.

Antoniu-Ioan, C. (2025) ‘CAPTCHAs as a Moving-Target Defense’, in 2025 25th International Conference on Control Systems and Computer Science (CSCS), Presented at the 2025 25th International Conference on Control Systems and Computer Science (CSCS), 563–567, available: https://doi.org/10.1109/CSCS66924.2025.00089.

Bock, K., Patel, D., Hughey, G., and Levin, D. (2017) ‘unCaptcha: A Low-Resource Defeat of reCaptcha’s Audio Challenge’, Presented at the 11th USENIX Workshop on Offensive Technologies (WOOT 17), available: https://www.usenix.org/conference/woot17/workshop-program/presentation/bock [accessed 3 Nov 2025].

Bursztein, E., Martin, M., and Mitchell, J. (2011) ‘Text-based CAPTCHA strengths and weaknesses’, in Proceedings of the 18th ACM Conference on Computer and Communications Security, CCS ’11, New York, NY, USA: Association for Computing Machinery, 125–138, available: https://doi.org/10.1145/2046707.2046724.

Cloudflare Radar 2024 Year in Review [online] (2025) available: https://radar.cloudflare.com/year-in-review/2024 [accessed 5 Nov 2025].

Datta, R., Li, J., and Wang, J.Z. (2005) ‘IMAGINATION: a robust image-based CAPTCHA generation system’, in Proceedings of the 13th Annual ACM International Conference on Multimedia, MULTIMEDIA ’05, New York, NY, USA: Association for Computing Machinery, 331–334, available: https://doi.org/10.1145/1101149.1101218.

Goodfellow, I.J., Bulatov, Y., Ibarz, J., Arnoud, S., and Shet, V. (2014) ‘Multi-digit Number Recognition from Street View Imagery using Deep Convolutional Neural Networks’, available: https://doi.org/10.48550/arXiv.1312.6082.

Hossen, I., Tu, Y., Rabby, F., Islam, N., and Cao, H. (n.d.) ‘Bots Work Better than Human Beings: An Online System to Break Google’s Image-based reCaptcha v2’.

Jajodia, S., Ghosh, A.K., Swarup, V., Wang, C., and Wang, X.S. (2011) Moving Target Defense: Creating Asymmetric Uncertainty for Cyber Threats, Springer Science & Business Media.

Liu, W. and Manager, G.P. (n.d.) ‘Introducing reCAPTCHA v3: the new way to stop bots’, Google Online Security Blog, available: https://security.googleblog.com/2018/10/introducing-recaptcha-v3-new-way-to.html [accessed 5 Nov 2025].

Mori, G. and Malik, J. (2003) ‘Recognizing objects in adversarial clutter: breaking a visual CAPTCHA’, in 2003 IEEE Computer Society Conference on Computer Vision and Pattern Recognition, 2003. Proceedings., Presented at the 2003 IEEE Computer Society Conference on Computer Vision and Pattern Recognition, 2003., I–I, available: https://doi.org/10.1109/CVPR.2003.1211347.

Sivakorn, S., Polakis, I., and Keromytis, A.D. (2016) ‘I am Robot: (Deep) Learning to Break Semantic Image CAPTCHAs’, in 2016 IEEE European Symposium on Security and Privacy (EuroS&P), Presented at the 2016 IEEE European Symposium on Security and Privacy (EuroS&P), 388–403, available: https://doi.org/10.1109/EuroSP.2016.37.

Tan, Y.X.M., Iacovazzi, A., Homoliak, I., Elovici, Y., and Binder, A. (2019) ‘Adversarial Attacks on Remote User Authentication Using Behavioural Mouse Dynamics’, in 2019 International Joint Conference on Neural Networks (IJCNN), 1–10, available: https://doi.org/10.1109/IJCNN.2019.8852414.

Wei, A., Zhao, Y., and Cai, Z. (2019) ‘A Deep Learning Approach to Web Bot Detection Using Mouse Behavioral Biometrics’, in Sun, Z., He, R., Feng, J., Shan, S. and Guo, Z., eds, Biometric Recognition, Cham: Springer International Publishing, 388–395, available: https://doi.org/10.1007/978-3-030-31456-9_43.

Wu, Z., Xue, Y., Feng, Y., Wang, X., and Song, Y. (2025) ‘MCA-Bench: A Multimodal Benchmark for Evaluating CAPTCHA Robustness Against VLM-based Attacks’, available: https://doi.org/10.48550/arXiv.2506.05982.

Xu, X., Liu, L., and Li, B. (2020) ‘A survey of CAPTCHA technologies to distinguish between human and computer’, Neurocomputing, 408, 292–307, available: https://doi.org/10.1016/j.neucom.2019.08.109.
