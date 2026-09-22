# Response to reviewers and editors of manuscript number [MANUSCRIPT ID]

# Revision Summary

[Opening acknowledgment and summary of completed revisions to be added after revision.]

- [Revision summary item 1.]
- [Revision summary item 2.]
- [Revision summary item 3.]
- [Revision summary item 4.]
- [Revision summary item 5.]

[Closing acknowledgment.]

# Editor

Thank you for submitting your manuscript to Natural Hazards Research.  

I have completed my evaluation of your manuscript. The reviewers recommend reconsideration of your manuscript following revision. I invite you to resubmit your manuscript after addressing the comments below. Please resubmit your revised manuscript by Oct 01, 2026.
  
When revising your manuscript, please consider all issues mentioned in the reviewers' comments carefully: please outline in a cover letter every change made in response to their comments and provide suitable rebuttals for any comments not addressed. Please note that your revised submission may need to be re-reviewed.      

To submit your revised manuscript, please log in as an author at https://www.editorialmanager.com/nhres/, and navigate to the "Submissions Needing Revision" folder under the Author Main Menu. 

Natural Hazards Research values your contribution and I look forward to receiving your revised manuscript.

**Response:**
[Response to be completed.]

"[Exact revised manuscript text]"
(Page XX, Lines XX–XX)

# Reviewer 1

## Overall Comment

This is a methodologically rigorous and highly practical study. The authors directly confront the real-world challenge of incomplete data and heterogeneous evidence quality in disaster response. Their core contribution lies in constructing a reproducible, tiered decision-making framework that translates equity (gender and functional support) into actionable spatial screening and prioritization tools, setting a benchmark for disaster management research.

**Response:**
[Response to be completed.]

"[Exact revised manuscript text]"
(Page XX, Lines XX–XX)

## Comment 1

Before publication, I recommend further strengthening the following issue: in spatial analyses, given that road damage and bridge collapse are common in post-earthquake environments, the correlation between straight-line distance and actual traversable routes and travel time may be extremely poor. Although this limitation is acknowledged in the discussion, if feasible, conducting a rough estimation of transfer routes would substantially enhance the practical relevance of this part of the analysis.
I look forward to seeing the revised final version.

**Response:**
Thank you for this constructive suggestion. We agree that straight-line proximity cannot establish traversability or travel time after an earthquake. The revised manuscript adds a nominal road-network sensitivity analysis, maps estimated transfer paths in Figure 4b, expands the distance comparison in Table 9, and clarifies the remaining operational limitations in the Discussion. The analysis uses a network constructed from 2024 road centerlines and distinguishes two comparisons: evaluating the original allocation on the road network, and selecting donors by network distance while holding shelter demand, inventories, recipient priorities and mobility scenarios fixed. Under full mobility, evaluating the baseline allocation on the network increases the unit-weighted mean distance from 2.15 to 2.99 km; network-based donor selection gives 2.66 km and changes the donor mix at four recipient shelters. These are nominal route-length estimates, not estimates of post-earthquake travel time. The available evidence does not validate road closures, bridge damage or vehicle access, so we do not present the routes as dispatch-ready.

The data description now distinguishes the two spatial sensitivities:

"We therefore preserve temporary toilets and toilet cars as separate fields, exclude cars and fixed stalls from the temporary-toilet-only shortfall, and compare great-circle and nominal road-network distances as spatial sensitivities."
(Page 9, Lines 163–165)

The Analytical Framework identifies the original donor rule as the baseline and explains how road lengths and off-network connectors are treated:

"In the baseline allocation, the eligible donor with the shortest great-circle distance is selected for each recipient."
(Page 20, Lines 418–420)

"Each Yatsushiro point projects onto its nearest edge, which is split at the projection to preserve partial-edge lengths. We compute shortest undirected network lengths and report geometric off-network connectors separately rather than treating them as verified access."
(Page 21, Lines 427–430)

The Results distinguish mapping the baseline allocation from changing donor selection:

"The baseline allocation selects nearest eligible donors by great-circle distance after recipient priority is established; panel b traces the corresponding nominal shortest road paths without changing that allocation. Several endpoints remain approximate district anchors, and geometric connectors are not verified access routes."
(Page 27, Lines 558–561)

"Evaluating the same allocation on the nominal road network increases the unit-weighted mean to 2.99 kilometers. Selecting donors by network length instead changes the donor mix at four recipients, reassigns nine units and gives a mean network length of 2.66 kilometers, with mean geometric connectors of 0.09 kilometers reported separately. One reassigned unit links records with shared coordinates and therefore has zero modeled network length; this does not establish a zero-distance physical transfer. Transferred quantities and residual shortfalls remain unchanged in all three mobility cases because the nominal network connects all sites and the comparison imposes no distance or travel-time budget. These results show sensitivity of donor selection and distance, not verified feasibility under earthquake damage."
(Page 27, Lines 570–579)

Figure 4b now displays nominal road paths, with the distinction between network paths and unverified access stated in its note:

"Panel b traces nominal shortest road paths for the baseline full reported-surplus allocation, whose donors are selected by great-circle distance; dashed connectors indicate unverified off-network access, and anchor endpoints remain approximate."
(Page 43, Lines 34–37)

Table 9 reports baseline great-circle distances, network distances on the same links, network-selected distances and donor reassignment. Its note explicitly qualifies the shared-coordinate case and the unchanged inventory outcomes:

"The network-selected full-mobility case includes one unit between records with shared coordinates and zero modeled road length, not a verified zero-distance transfer. Quantities and coverage are unchanged across distance rules under the connected nominal network and absence of a distance or travel-time budget."
(Page 63, Lines 5–8)

The Discussion preserves the requirement for operational verification before deployment:

"The nominal road-distance sensitivity does not replace verification of road access and vehicle constraints before dispatch."
(Page 35, Lines 754–755)

"The nominal road network adds route-length information but does not establish post-earthquake traversability, vehicle access, setup requirements or ownership. District-anchor fallbacks and shared coordinates introduce further location uncertainty, including a zero-length modeled transfer that cannot be interpreted as physical co-location. Operational routing and equipment verification are needed before transfers are authorized."
(Page 37, Lines 793–797)

"Further routing analysis should incorporate verified road availability, vehicle constraints, installation times, and waste-service destinations."
(Page 38, Lines 811–812)


# Reviewer 2

## Overall Comment

GENERAL EVALUATION AND OVERVIEW

The manuscript addresses a critical, policy-relevant, and timely topic in urban disaster risk management and public health: equity-sensitive planning and allocation of emergency shelter sanitation infrastructure (WASH) under severe data incompleteness following a major seismic event. The thematic scope aligns exceptionally well with the Aims and Scope of Natural Hazards Research, specifically addressing "Disaster vulnerability, hazard, and risk assessment and management" as well as "Natural Hazards and human society."

The study has notable strengths, including a high-fidelity empirical grounding that combines a 2026 post-earthquake shelter snapshot with 125-meter residential census meshes and administrative Long-Term Care (LTC) registries in Kumamoto and Yatsushiro Cities. Furthermore, the mathematical isolation of the "spatial fragmentation increment" demonstrates why aggregate citywide planning underestimates localized toilet requirements due to integer indivisibility.
However, the manuscript currently suffers from major structural, formatting, and theoretical limitations. The Introduction is excessively long and fragmented; there is no standalone Literature Review section or Literature Positioning Table; the mathematical decision framework lacks a visual flowchart; and the authors fail to contrast their descriptive scenario-based heuristics with established methodologies for optimization under uncertainty (such as Robust Optimization, Stochastic Programming, Distributionally Robust Optimization, Fuzzy Programming, or Monte Carlo Simulation).
Therefore, I recommend major revision. The authors must address the following mandatory revisions before the manuscript can be considered for publication.

MAJOR REVISIONS REQUIRED

**Response:**
[Response to be completed.]

"[Exact revised manuscript text]"
(Page XX, Lines XX–XX)

## Comment 1

1. Mandatory Journal Format Compliance and Citation Restructuring
The manuscript currently violates several explicit formatting requirements specified in the journal's Guide for Authors:
In-Text Citation Style (Severe Violation): The manuscript uses Harvard-style author-year in-text citations (e.g., Cabinet Office, 2024; Deelstra & Bristow, 2020). The journal requires a numbered, square-bracket style (Vancouver style), ordered sequentially by appearance in the text. All citations must be re-formatted, and the reference list must be converted to a numbered sequence.
Structured Abstract Requirement: The journal explicitly mandates a Structured Abstract with explicit sub-headings (e.g., Background/Purpose, Methods, Findings, Conclusions) within a 250-word limit for Full-Length Research Articles. The authors must convert their current single-block abstract into this required structured format.
Numbered Section Headings: Section headings must follow a clear decimal hierarchy (e.g., 1. Introduction, 1.1. Urban Shelter Sanitation..., 1.1.1. ...) as stipulated in the journal instructions.
Mandatory Declarations Sections: The authors must include explicit, separate text headings prior to the bibliography for: (a) Authors' Contribution (CRediT Taxonomy), (b) Ethics Statement, (c) Declaration of Competing Interests (COI), and (d) Acknowledgments.

**Response:**
[Response to be completed.]

"[Exact revised manuscript text]"
(Page XX, Lines XX–XX)

## Comment 2

2. Streamlining the Introduction ("The Introduction Formula")
The current Introduction spans nearly 5 pages across three unnumbered subheadings, creating an unnecessarily verbose opening that dilutes the central research question. The authors are required to condense and streamline the Introduction into approximately 1.5 to 2 pages (5 cohesive paragraphs) following Keith Head's established "Introduction Formula" (Hook, Puzzle, Do, Findings, Roadmap):
Paragraph 1 (The Hook): Define shelter sanitation as a critical urban utility-continuity problem and explain why spatial disaggregation matters.
Paragraph 2 (The Puzzle / The Gap): Highlight the conflict between national equity guidelines and real-world "dirty/incomplete" disaster databases, explaining why prescriptive optimization models suffer from the "optimizer's curse."
Paragraph 3 (The Do): Introduce the proposed two-tiered analytical framework and how it handles incomplete evidence without fabricating observations.
Paragraph 4 (The Findings): Summarize key quantitative metrics (e.g., the +64.3% fragmentation penalty in Kumamoto, the 31-unit shortfall in Yatsushiro, and the rebalancing sensitivity bounds).
Paragraph 5 (The Roadmap): Outline the structural organization of the remaining paper.

**Response:**
[Response to be completed.]

"[Exact revised manuscript text]"
(Page XX, Lines XX–XX)

## Comment 3

3. Establishment of a Dedicated "Literature Review" Section and Positioning Table
The manuscript currently lacks a dedicated, systematic Literature Review. To properly ground the study within the state of the art, the authors must insert a new section—2. Literature Review—organized into three structured sub-domains:
2.1. Disaster WASH Logistics and Planning Under Uncertainty: Discuss secondary need-estimation frameworks (e.g., Rye & Aktas, 2022), multiobjective conflict shelter models (e.g., Hallak et al., 2019), and risk zonation (e.g., Nekooie et al., 2022).
2.2. Social Equity, Gender, and Disability in Emergency Sanitation: Review literature on intersectional WASH vulnerabilities, menstrual health invisibility, older adult exclusion, and socioeconomic impacts (e.g., Al Omari et al., 2024; Lima et al., 2026; Wilbur et al., 2022; Yadav & Barve, 2017).
2.3. Emergency Resource Reallocation and Lateral Transshipment: Review recent advances in humanitarian lateral transshipment, evolutionary game cooperation, progressive supply mechanisms, and two-stage allocation models (e.g., Anvari et al., 2023; Chen et al., 2026; Guo & Nishimura, 2026; Qezelbash-Chamak et al., 2024; Wang et al., 2024).
Literature Positioning Table (Mandatory): To close this section, the authors must present a formal Literature Positioning Table comparing their work against key published papers across parameters such as: Decision Hierarchy, Social Equity Metrics, Uncertainty Handling, Lateral Reallocation Modeling, and Focus on Incomplete Real-World Operational Data.

**Response:**
[Response to be completed.]

"[Exact revised manuscript text]"
(Page XX, Lines XX–XX)

## Comment 4

4. Methodological Flowchart and Graphical Abstract Requirement
The manuscript presents 30 mathematical equations across several subsections, making it difficult for readers to visualize the model's sequential execution.
Methodological Flowchart: The authors must add an explicit visual flowchart (to be placed as the new Figure 1 or at the beginning of Section 3) mapping the multi-stage decision pipeline: from census mesh/LTC inputs, through synthetic equity proxies, sitewise fragmentation calculations, minimax priority rankings, to nearest-donor rebalancing heuristics.
Graphical Abstract: The journal strongly encourages submitting a Graphical Abstract. Authors should format this new methodological flowchart to the journal's exact specifications (531 x 1328 pixels, JPEG/TIFF/PDF format) and upload it as a separate file in the submission system.

**Response:**
Thank you for this suggestion. The revised manuscript includes a methodological flowchart as the new Figure 1, introduced at the beginning of the Analytical Framework. It connects emergency records, census age–sex mesh data, disability and long-term-care statistics, and planning assumptions to the implemented screening and reallocation procedures. The parallel branches distinguish synthetic demand estimation from sitewise requirement calculations, and distinguish robust verification priorities from the operational recipient ordering used in conditional nearest-donor rebalancing. The workflow ends with conditional service packages rather than presenting field verification as a completed analytical stage.

The new introductory sentence and figure note state:

"Figure 1 summarizes the analytical workflow, separating observed evidence, synthetic demand scenarios, verification screens, and conditional resource reallocation."
(Page 14, Lines 281–282)

"Municipality screening covers 11 municipalities, shelter demand scenarios cover 53 matched shelters in Kumamoto and Yatsushiro Cities, and operational pressure and conditional rebalancing analyses concern Yatsushiro. The diagram separates synthetic demand estimation, sitewise requirement calculations, equity verification priorities, and conditional inventory transfers. Functional capacity remains unobserved; conditional transfers do not establish operational feasibility."
(Page 42, Lines 881–885)

A separate graphical abstract combines the data inputs and analytical sequence with the conditional reallocation map and mobility-scenario outcomes. It uses the study's result graphics to communicate the planning framework and the dependence of reallocation outcomes on mobility assumptions, while retaining the distinction between conditional transfers and verified service provision.

## Comment 5

5. Justification of Framework Choice vs. Optimization Under Uncertainty
When dealing with incomplete, noisy, or "dirty" real-world data, the field of Operations Research provides robust mathematical programming techniques specifically designed for optimization under uncertainty—such as Robust Optimization, Two-Stage Stochastic Programming (TSSP), Distributionally Robust Optimization (DRO), Fuzzy Mathematical Programming, Grey Numbers, and Monte Carlo Simulation.
The authors must add an explicit theoretical discussion in Section 5.3 (Operational and Evidence Uncertainty) justifying why they deliberately selected a descriptive, priority-constrained heuristic and deterministic scenario bounds over formal mathematical optimization under uncertainty.
They should explain the practical trade-offs: while robust optimization models prescribe a single "optimal" dispatch plan under assumed uncertainty sets, a descriptive decision-support framework avoids the "optimizer's curse" by providing field managers with defensible sensitivity bounds and verification sequences when operational data (e.g., fixed toilet operability, sewer status, road access) cannot be verified in real time.

**Response:**
Thank you for requesting a clearer justification of the framework choice. The revised Conditional Rebalancing and Service Packages subsection and Operational and Evidence Uncertainty discussion explain why the study uses transparent, conditional screening before dispatch, while explicitly acknowledging the absence of global optimality and probabilistic performance guarantees. The limitation concerns the empirical justification of operational inputs, not the mathematical ability of optimization methods to represent uncertainty. We do not claim that optimization necessarily produces only one dispatch plan or that a heuristic inherently avoids the optimizer's curse; the adjacent discussion recognizes complementary robust, stochastic and distributionally robust approaches.

"The ordering makes the priority given to screened need explicit rather than estimating a trade-off between need and transport cost. Each mobility case is a conditional inventory calculation, not a probability-weighted forecast or a guarantee of feasible deployment."
(Page 21, Lines 421–424)

"We therefore select deterministic scenario bounds and a priority-constrained heuristic to support verification before dispatch, rather than to prescribe an optimal allocation from unverified operational inputs. The available records do not establish the joint operational states of toilets, sewers, waste removal and road access, or provide a validated basis for assigning their probabilities. This limits the empirical justification of an optimization model, not the mathematical possibility of formulating one. Our approach makes selected assumptions and their conditional consequences inspectable, at the cost of providing neither global optimality nor probabilistic performance guarantees. Its bounds apply only to the declared scenarios and need not contain the realized outcome. Once operational inputs and decision objectives are verified, formal optimization can complement this screening stage; the present analysis does not test whether its heuristic outperforms such alternatives."
(Pages 32–33, Lines 681–692)

## Comment 6

6. Minor Methodological and Reporting Enhancements
Table of Nomenclature: To improve mathematical legibility, the authors should include a comprehensive Table of Nomenclature in the Appendix listing all sets, indices, parameters, synthetic variables, and decision indicators used in Equations 1-30.
Quantitative Conclusions: Expand the Conclusion section to explicitly reiterate key synthetic demographic metrics (e.g., the Base functional-support demand of 30.6 persons at Yatsushiro Arena) alongside the logistical rebalancing metrics for a more balanced summary of results.

**Response:**
[Response to be completed.]

"[Exact revised manuscript text]"
(Page XX, Lines XX–XX)

## Comment 7

REQUIRED REFERENCES TO BE ADDED TO THE BIBLIOGRAPHY
The authors must cite the following relevant publications within the text (using the required numbered citation format) and include their full details in the reference list:

Al Omari, S., Honein-AbouHaidar, G., & Sibai, A. M. (2024). By the numbers and in their own words: A mixed methods study of unmet needs and humanitarian inclusion of older Syrian refugees in Lebanon. PLOS ONE, 19(7), e0302082. https://doi.org/10.1371/journal.pone.0302082

Anvari, M., Anvari, A., & Boyer, O. (2023). A prepositioning model for prioritized demand points considering lateral transshipment. Journal of Humanitarian Logistics and Supply Chain Management, 13(4), 433-455. https://doi.org/10.1108/JHLSCM-01-2023-0005

Chen, Y., Xu, G., Feng, S., & Wang, C. (2026). Post-disaster resource redistribution and cooperation evolution based on two-layer network evolutionary games. Chaos, 36(2), 023107. https://doi.org/10.1063/5.0312287

Guo, Y., & Nishimura, E. (2026). Distribution strategy for relief supplies with consumption frequency: Under a Tokyo-area disaster scenario. Progress in Disaster Science, 31, 100639. https://doi.org/10.1016/j.pdisas.2026.100639

Hallak, J., Koyuncu, M., & Miç, P. (2019). Determining shelter locations in conflict areas by multiobjective modeling: A case study in northern Syria. International Journal of Disaster Risk Reduction, 38, 101202. https://doi.org/10.1016/j.ijdrr.2019.101202

Kamyabniya, A., Noormohammadzadeh, Z., Sauré, A., & Patrick, J. (2021). A robust integrated logistics model for age-based multi-group platelets in disaster relief operations. Transportation Research Part E: Logistics and Transportation Review, 152, 102371. https://doi.org/10.1016/j.tre.2021.102371

Lima, I. A. S., Nicacio, W., Ducatti, A. P. S., Bertazzo, T. R., & de Brito, I. (2026). Bridging standards and capacities: an institutional analysis of the 2022 flood response in the Médio Mearim region, Brazil. Disaster Prevention and Management, 35(3), 276-290. https://doi.org/10.1108/DPM-10-2025-0347

Nekooie, M. A., Attari, M., Ghaffariankolahi, A., & Rajai, Y. (2022). Risk assessment framework for the supply of water during a crisis. Proceedings of the Institution of Civil Engineers - Water Management, 176(5), 261-276. https://doi.org/10.1680/jwama.21.00072

Noyan, N., & Kahvecioglu, G. (2018). Stochastic last mile relief network design with resource reallocation. OR Spectrum, 40(1), 187-231. https://doi.org/10.1007/s00291-017-0498-7

Qezelbash-Chamak, J., Badamchizadeh, S., & Seifi, A. (2024). A fast-response mathematical programming approach for delivering disaster relief goods: an earthquake case study. Transportation Letters, 16(9), 1091-1114. https://doi.org/10.1080/19427867.2023.2270238

Rye, S., & Aktas, E. (2022). A Multi-Attribute Decision Support System for Allocation of Humanitarian Cluster Resources Based on Decision Makers' Perspective. Sustainability, 14(20), 13423. https://doi.org/10.3390/su142013423

Wang, D., Yang, K., Yang, L., & Li, S. (2024). Distributional robustness and lateral transshipment for disaster relief logistics planning under demand ambiguity. International Transactions in Operational Research, 31(3), 1736-1761. https://doi.org/10.1111/itor.13227

Wilbur, J., Clemens, F., Sweet, E., Banks, L. M., & Morrison, C. (2022). The inclusion of disability within efforts to address menstrual health during humanitarian emergencies: A systematized review. Frontiers in Water, 4, 983789. https://doi.org/10.3389/frwa.2022.983789

Yadav, D. K., & Barve, A. (2017). Analysis of socioeconomic vulnerability for cyclone-affected communities in coastal Odisha, India. International Journal of Disaster Risk Reduction, 22, 387-396. https://doi.org/10.1016/j.ijdrr.2017.02.003

**Response:**
Thank you for recommending these publications. The revised Discussion incorporates the suggested literature on inclusive humanitarian assistance, planning with incomplete operational evidence, optimization under uncertainty, and relief-resource redistribution. Thirteen publications are newly cited and included in the reference list; Hallak et al. (2019), which was already cited in the Introduction and listed in the references, is retained. The revised passages are quoted below.

"Research on older Syrian refugees in Lebanon identifies unmet needs and gaps in age-inclusive humanitarian assistance, including access to suitable bathing facilities. A systematized review of menstrual health in emergencies identifies limited participation by women and girls with disabilities and barriers to accessible WASH facilities. Household-based vulnerability research in coastal Odisha also identifies toilet provision and shelter distance among factors relevant to disaster vulnerability (Al Omari et al., 2024; Wilbur et al., 2022; Yadav & Barve, 2017)."
(Page 29, Lines 613–620)

"Humanitarian decision-support research combines historical needs estimates with decision-maker preferences and resource-allocation optimization when real-time data are unavailable. Emergency-water planning also combines disruption scenarios with spatial risk zoning to identify support and supply locations. An institutional study of flood response in Brazil identifies information asymmetries and fragmented coordination as constraints on implementing humanitarian standards (Lima et al., 2026; Nekooie et al., 2022; Rye & Aktas, 2022)."
(Page 32, Lines 670–676)

"Formal optimization offers complementary ways to represent uncertainty: integrated platelet logistics models use robust optimization, while last-mile relief network design uses two-stage stochastic programming to address accessibility and equitable distribution. Distributionally robust relief planning also combines lateral transshipment with demand ambiguity and reports mitigation of the optimizer's curse relative to traditional stochastic programming. These approaches do not support a blanket claim that a descriptive heuristic is inherently protected against errors in uncertain inputs (Kamyabniya et al., 2021; Noyan & Kahvecioğlu, 2018; Wang et al., 2024)."
(Pages 32–33, Lines 690–697)

"Humanitarian prepositioning models already combine demand-point priorities, road vulnerability and lateral transshipment. Other relief-delivery models link two-stage stochastic location and inventory decisions to routing models that exclude unavailable links. Progressive supply models carry unused resources forward and use transshipment to address imbalances in unmet demand across shelters. Two-layer evolutionary-game research examines a different aspect of redistribution, namely how incentives and interactions between shelters and affected people shape cooperation (Anvari et al., 2023; Chen et al., 2026; Guo & Nishimura, 2026; Qezelbash-Chamak et al., 2024)."
(Page 34, Lines 720–727)
