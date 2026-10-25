# Public finite-element reference methods

This document reproduces the complete Supplementary finite-element methods, S-FE1–S-FE9, from the final Supplementary information dated 26 October 2026, including Supplementary Tables S19–S21. It documents the openly shared reference engineering implementation and its retained local evidence. The unchanged 9,000-row learning table retains `reference_stroke_mm`; these reference cases do not replace that table or establish 9,000 independently traceable native FE labels. The numerical source correspondence and its limits are stated in S-FE9.

The compact [Supplementary Software 1 archive](Supplementary_Software_1.zip), its [package README](PACKAGE_README.md), and the machine-readable [reference cases](reference_cases.csv) provide the accompanying source and evidence. The package's reproduction levels and omitted dependencies are specified in S-FE8 and the package README.

The text below is a transcription of the final supplement. Its statements about actions performed “in this revision” describe that manuscript revision, not subsequent repository publication.

## Supplementary finite-element methods

These methods describe the separately traceable local reference implementation, RECT3D004 with the v002 CHAB3–Voce card and B mesh. The retained native continuation variant is RESTART\_AUTOREF\_SUPPORT\_PRECISION\_V003; review policy V004 audits that numerical variant. Accepted execution, physical admissibility, completed sampled search and formal dataset qualification are distinct statuses. The reviewed records retain formal qualification as false.

### S-FE1. Coordinates, geometry and discretization

The longitudinal, loading and width directions were denoted x, y and z. The quarter domain was x ∈ [0,135] mm, y ∈ [−h/2,h/2] and z ∈ [0,b/2]. Reflection reconstructed the negative-x and negative-z halves. The constraints were u\_x = 0 on x = 0 and u\_z = 0 on z = 0; thickness was not treated as a symmetry direction. This assumption excludes asymmetric bending, twisting and symmetry-breaking instabilities.

The selected B mesh used a maximum longitudinal spacing of 1 mm, 14 elements across the full thickness and four across the half-width. Longitudinal partitions explicitly included x = 0, 50, 130 and 135 mm. Thus, the fixed pre-bend locations and evaluation endpoints were meshed independently of the variable corrective support location. For the retained 270 mm geometry, the quarter model contained 10200 workpiece nodes and 7560 solid elements. The number of surface contact elements depended on the corrective geometry; the representative production case documented in S-FE7 contained 868 contact elements. The solid formulation was SOLID185 with KEYOPT(2)=2, corresponding to enhanced strain. ANSYS SOLID185 element reference: <https://ansyshelp.ansys.com/public/Views/Secured/corp/v261/en/ans_elem/Hlp_E_SOLID185.html>.

The nominal baseline was b = 35 mm, h = 8 mm, corrective span = 260 mm, corrective punch/support radii = 10 mm, and pre-bend stroke = 15.6934 mm. These baseline values are distinct from the latest local production design. That design varied b over 31–35 mm, h over 7.25–7.75 mm, corrective span over 220–240 mm, both corrective radii over 12–18 mm, and pre-bend stroke over 12–12.5 mm. Its prospective 3000-input pool was a six-dimensional randomized Latin hypercube with seed 20261016, canonicalized to six decimal places; a separate seed, 20261017, assigned 80 development and 20 locked-holdout conditions within each block of 100 before FE execution. These are local design settings, not evidence that 3000 cases or the target 1000 accepted conditions were completed. The accepted subset is selected by tolerance and admissibility and is therefore not a full Latin hypercube.

### S-FE2. Material law, parameters and calibration

The material card combined isotropic elasticity with the three-component Chaboche model and a Voce nonlinear isotropic law. In standard small-elastic-strain notation, the hardening contribution to the yield radius was σ\_y(p) = σ\_0 + Q[1 − exp(−βp)], and the total backstress was the sum of three components. The uniaxial virgin monotonic hardening tangent used in the parameter constraint was

H(p) = Σ\_i C\_i exp(−γ\_i p) + Qβ exp(−βp).

Here p is accumulated equivalent plastic strain, distinct from instantaneous total axial strain, and β denotes the Voce rate parameter stored as b in the material JSON. The linear term in the Voce material card was zero. The tabulated values below are the retained fitted parameters; the native material card rounds them to approximately 12 significant digits.

**Supplementary Table S19 Constitutive parameters**

| Quantity | Value | Unit |
| --- | --- | --- |
| E | 204401 | MPa |
| ν | 0.253 | dimensionless |
| σ\_0 | 1000.1213668403026 | MPa |
| C\_1 | 236278.0570552386 | MPa |
| γ\_1 | 555.5730030586104 | inverse strain |
| C\_2 | 25656.4098946357 | MPa |
| γ\_2 | 14.347742213928159 | inverse strain |
| C\_3 | 774.2071951163114 | MPa |
| γ\_3 | 14.34495784479529 | inverse strain |
| Q | −561.1625195016677 | MPa |
| β | 307.6347863460539 | inverse strain |

The initial material state assumed zero plastic strain, zero accumulated p and zero backstresses; full initial internal-variable fields were not experimentally measured. E and ν were fixed rather than jointly refitted. KPZ histories were retained chronologically until the first point with |true strain| > 0.02, excluding that point and subsequent records. For KPS05, true strain was calculated as ln(1 + ε\_eng), with engineering strain converted from percent, and the supplied sigmaVC was used as true stress without an additional stress conversion. A fixed-E elastic-origin correction of 0.0001097623662161949 was subtracted from true strain. It was estimated from 21 KPS05 points below 525 MPa as the mean of true strain minus stress/E. The retained corrected-strain prefix contained 136 points and ended before the first corrected true strain above 0.02.

Each of the four calibration specimens received equal total squared-error weight; points within a specimen were weighted equally. The objective was the sum, over specimens, of the mean squared stress residual divided by (1000 MPa)^2. Parameter selection minimized this calibration objective among feasible converged solutions, subject to H(p) ≥ 0 for 0 ≤ p ≤ 0.12, with a continuous interval-minimum check. The saved minimum tangent was approximately 0.00107561 MPa at p ≈ 0.00373692. This constraint concerns the virgin monotonic axial response; it is not a proof of general multiaxial stability, parameter uniqueness or residual-stress accuracy. The held-out specimens were not used for selection. The model is a local CHAB3–Voce identification from the public records, not the original dataset authors' constitutive model.

### S-FE3. Contact and boundary conditions

The four tool roles in the quarter model were the pre-bending head at x = 50 mm, the pre-bending support at x = 130 mm, the corrective support at x = L/2 and the corrective punch at x = 0. Their mirrored counterparts formed the full fixture. TARGE170 defined rigid analytic cylinders, while CONTA174 covered the corresponding workpiece surface patches. Contact used KEYOPT(2)=1, KEYOPT(4)=2 and KEYOPT(10)=2: penalty enforcement, nodal detection normal to the target, and iterative contact-stiffness updating. Coulomb friction was μ = 0.15. The FKN and FTOLN factors were 0.1 and 0.001. The FTOLN factor is a contact algorithm setting and is distinct from the separately checked absolute penetration screen. ANSYS CONTA174 element reference: <https://ansyshelp.ansys.com/public/Views/Secured/corp/v261/en/ans_elem/Hlp_E_CONTA174.html>.

Tool pilot nodes were constrained in all degrees of freedom except for their prescribed y motion; roller rotations were fixed. A UY-only COMBIN14 spring connected one material node near x = 130 mm, y = 0, z = 0 to a fixed coincident auxiliary node. Its quarter-model stiffness was 0.01 N mm−1. No hard y constraint was applied to the workpiece, and gravity was neglected. Vertical tool reactions were multiplied by four to recover the symmetric full-domain force. Four times a quarter-model reaction-vector norm was used only as a conservative release-check quantity; it was not interpreted as the full assembly's vector resultant.

The pre-bend top contact patch covered x = 25–90 mm and its bottom support patch covered x = 95–135 mm. The corrective top patch extended a distance max(35 mm, 1.5R\_s) on either side of x = L/2, clipped to the quarter-domain limits. The corrective bottom patch extended from x = 0 to min(60 mm,L/2). These are surface contact domains, not extra geometric restraints.

### S-FE4. Loading, complete unloading and independent continuations

The prescribed sequence comprised 11 static load steps. The load-step coordinate is a monotonically increasing static load parameter, not elapsed physical time. The same material and deformed configuration were retained throughout. The initial corrective tools were placed 100 mm away from the undeformed surfaces. After the pre-bend tools were fully withdrawn, their deformed surface nodes and the analytic cylinder geometry determined the first-contact support and punch positions. For a cylinder of radius R centred at x\_t, the candidate support centre was max[y\_n + sqrt(R² − (x\_n − x\_t)²)] on the deformed top nodes within the cylinder projection; the punch centre was the corresponding minimum with the negative square-root sign on bottom nodes. The corrective stroke s was added to that punch position.

**Supplementary Table S20 Loading and unloading sequence**

| Load step | Motion | Retained state |
| --- | --- | --- |
| 1 | Pre-bend heads move downward by the configured pre-bend stroke | A: pre-bend peak |
| 2 | Pre-bend heads return to their original y position in fine unloading increments | — |
| 3 | Pre-bend heads move upward to their release position | — |
| 4 | Pre-bend supports move downward by 1 mm | — |
| 5 | Pre-bend supports continue downward to their release position | B: fully unloaded pre-bend |
| 6 | Corrective supports and punch move to the first nodal-contact positions computed from B | C0: initial corrective contact |
| 7 | Corrective punch moves upward by s from its contact position | C: corrective peak |
| 8 | Corrective punch returns to 1 mm below its contact position | — |
| 9 | Corrective punch continues to its release position | — |
| 10 | Corrective supports move upward by 1 mm | — |
| 11 | Corrective supports continue to their release position | D: final fully unloaded state |

The current selected configuration used a release distance of 47.3868 mm; this fixed value was retained when pre-bend stroke varied within the latest production design. The normal loaded displacement increment was at most 0.15 mm, and the fine unloading increment was at most 0.1 mm. Each remote, unloaded withdrawal leg used two nominal substeps. The initial/minimum substep count for a ramp was max[2,ceil(|travel|/increment)], with an automatic-substepping upper count max(500,10 times the initial count). Displacement loading was ramped.

An independent C0 calculation was performed for each physical condition. Corrective candidates for that condition restored its multiframe restart state, rather than importing a residual shape with reset plastic variables. The retained native branch explicitly restored the full-precision contact-position parameters and reasserted the support displacement before correction. This numerical variant was audited against limited cold-start/restart controls, including zero and 12 mm corrective strokes; the successful comparisons do not establish equivalence for every geometry or stroke.

### S-FE5. Solver settings and extraction

The local reference executions used Mechanical APDL 2026 R1 (release 261), with four CPU cores. These are documented local execution settings, not an inferred specification of the laboratory server used for the 9000-row table. Static large-deformation analysis used NLGEOM, automatic substepping, an unsymmetric Newton–Raphson formulation, up to 75 equilibrium iterations per substep, and force and moment convergence commands CNVTOL,F,,0.001,2,1 and CNVTOL,M,,0.001,2,1.

The continuation variant additionally reasserted CNVTOL,U,,1e-9,0,1 before each of steps 7–11. This uses an automatic displacement reference with a minimum reference of 1; it is not a fixed absolute 10⁻⁹ mm convergence guarantee. Actual printed displacement criteria had to remain at or below 10⁻⁷ mm. The actual corrective support position was checked against the saved full-precision target within 10⁻⁹ mm. The subsequent review policy retained automatic-reference differences as diagnostics while requiring unchanged table settings, matched completed substeps, the absolute criterion ceiling, support precision and the original physical comparison budgets.

Nodal solutions and reactions were saved at every converged substep. Elastic and plastic strain results for the workpiece were also saved at every converged substep. At A, B, C0, C and D, exported records included displacements, stress, accumulated equivalent plastic strain, total axial strain, contact quantities and individual tool reaction vectors. ERESX,NO prevented extrapolation of integration-point results before their element-node output. These copied integration-point records were checked by element/node identity and compared with independently exported extrema; they were not claimed to be integration-point spatial coordinates. Missing far-field contact output remained missing and was not replaced with zero.

### S-FE6. Residual metric, feasible-action proposal and acceptance

For a deformed cross-section S\_i, the centroid was c\_i = (∫\_S\_i x dA)/(∫\_S\_i dA). Each Q4 patch was integrated with 3 × 3 Gaussian quadrature using dA = |∂x/∂ξ × ∂x/∂η| dξ dη. The mirrored full-section centroid lay on z = 0. Let c\_− and c\_+ be the deformed centroids at the reference endpoints x = −130 and +130 mm. The reported error was

J = max\_i |(c\_i − c\_−) × (c\_+ − c\_−)| / |c\_+ − c\_−|,

over all retained reference sections in that interval. J\_B and J\_D denoted the initial and final free-state errors. The code also retained a whole-length diagnostic, which was not substituted for the fixed-260-mm measure. Peak corrective force was the maximum absolute vertical punch reaction over the corrective loading substeps, multiplied by four.

The latest local production protocol used four fixed actual anchors. Distances were Euclidean in the six-input space after division by the declared feature ranges: 10 mm for width, 2 mm for thickness, 80 mm for corrective span, 15 mm for each corrective radius and 3.6934 mm for pre-bend stroke. Ties were resolved by anchor identifier. For the nearest anchor with stroke s\_a and initial error J\_B,a, the initial proposal was

s\_prop = round\_6{ min[s\_max, max(10⁻⁶ mm, s\_a clip(J\_B/J\_B,a,0.5,1.5))] },

where s\_max = round\_6[max(8 mm,1.6u\_pre)]. J\_B was taken from the actual B state within that condition's independent C0 calculation. The selected anchor was FP0001 throughout the frozen local production design; its measured J\_B was 1.577062809551037 mm and its executed stroke was 9.116862 mm. Cases already satisfying J\_B < 1 mm were skipped rather than assigned synthetic zero-stroke labels. At most one proposed corrective branch was evaluated in this production protocol. Broader earlier pilot code can propose further strokes, but those extra proposals were not enabled by this one-candidate production setting.

The following acceptance conditions were applied before retaining a local feasible-action label:

1. An accepted solver exit, complete required output, successful parsing, consistent input/source identity and an actual final D geometry were required.

2. Accumulated equivalent plastic strain could not exceed 0.0873690726826633, and the maximum absolute total axial strain over saved converged substeps could not exceed 0.02; the code allowed 10⁻⁸ numerical slack for these two screens. These are declared usage envelopes of the calibration histories, not universal multiaxial failure limits.

3. Complete copied-field identities, extrema agreement, contact identities and the full axial-strain trajectory/checkpoint cross-check were required.

4. Available key-state contact penetration had to be finite and no greater than 0.02 mm. This was not asserted as a measurement of every contact point at every intermediate substep.

5. Each tool had to be geometrically separated in B and D, with minimum nodal radial gap >10⁻⁶ mm and four times the quarter reaction-vector norm <0.1 N. The final punch and each final vertical tool reaction were also checked against 0.1 N.

6. The actual final error had to satisfy J\_D < 1 mm, strictly. Proposed values, interpolation, solver nonconvergence and missing outputs never created labels. Converged above-tolerance or inadmissible outcomes were retained as outcomes but excluded from the accepted-action subset.

These criteria define local physical admissibility and feasibility. The recorded formal-dataset qualification flag was kept separate and remained false. Failure of the single candidate is not proof that the physical condition cannot be straightened.

### S-FE7. Executed example and distinction from historical search labels

For the actual local condition b = 31.188231 mm, h = 7.34995 mm, L = 235.856511 mm, R<sub>p</sub> = 14.61644 mm, R<sub>s</sub> = 15.605311 mm and u\_pre = 12.45066 mm, the independent pre-bend produced J\_B = 1.7452755092472956 mm. The single executed corrective stroke was 10.089285 mm, giving J\_D = 0.5448767739754917 mm. The peak corrective and pre-bend forces were 6407.085255273072 and 10158.732824846627 N. Maximum accumulated plastic strain was 0.01117746997624636, the full saved trajectory maximum absolute axial strain was 0.01147221928331019, and available key-state contact penetration reached 0.0007845001528039575 mm. All tools were verified open after unloading. The base and branch solver receipts both recorded zero error count and accepted exit; the branch contained 418 saved converged substeps. This example demonstrates the documented local calculation and feasible-action decision; it is not presented as a row from the 9000-row learning table.

The earlier completed local best-sampled searches used seven coarse strokes, refinement of observed admissible valleys, actual evaluations on both sides of proposed minima, a total bracketing resolution no larger than 0.02 mm and at most 44 candidate requests. Material-rejection boundaries received at most three additional probes. Incomplete valleys, boundary minima and brackets crossing rejected candidates prevented search acceptance. For the nominal B0001 condition, the completed search used 15 candidates and selected 14.641792 mm, with J\_D = 0.11991514155457911 mm and a two-sided bracket width of approximately 0.01 mm. The record explicitly states global\_optimum\_proven=false and retains formal qualification as false. This best-sampled definition is distinct from the later first-feasible-action policy.

### S-FE8. Reproduction levels, cases and sensitivity evidence

The three reference cases below are completed local best-sampled searches. Their selected strokes are the actual executed actions. The B0001, P0008 and R0004 input vectors (b, h, L, R<sub>p</sub>, R<sub>s</sub>, u) are respectively (35, 8, 260, 10, 10, 15.6934), (32.406311, 7.906461, 199.929494, 23.185329, 21.933325, 13.786816) and (35, 9, 260, 10, 10, 15.6934), in millimetres.

**Supplementary Table S21 Retained local best-sampled cases**

| Case | Stroke mm | Initial J mm | Final J mm | Peak force N |
| --- | --- | --- | --- | --- |
| B0001 | 14.641792 | 5.347281 | 0.119915 | 7632.580 |
| P0008 | 8.103878 | 3.465323 | 0.115181 | 9234.628 |
| R0004 | 15.238613 | 6.513006 | 0.140392 | 10037.327 |

*Values are rounded for display. Exact configurations, outcomes and search traces are retained in Supplementary Software 1. These cases are not identified as members of the 9,000-row learning table.*

Read-only re-parsing on 26 October 2026 recovered the initial and final J, peak corrective force, maximum accumulated plastic strain and maximum absolute axial total strain for each case. All 15 values equalled the archived floating-point outputs exactly. The original raw field files remained unchanged in size and modification time. This check used the large original text exports retained locally; these are omitted from the compact package, which therefore does not independently support this complete re-parsing check. The check establishes extraction repeatability, not independent rerunning of the FE solution; FE invocations and MAPDL POST invocations were both zero.

Numerical checks have different scopes. At a fixed 12-mm stroke, L3-to-L4 and L4-to-B mesh comparisons changed J by 0.00201861 and 0.00122173 mm and peak force by 0.117861% and 0.249873%. Their overall qualification remained inconclusive because selected-stroke comparisons were missing. Separate B-to-L4 local challenges around the three best-sampled cases changed selected stroke by 0.001585, 0.003139 and 0.010000 mm, with J differences 0.000621779, 0.000731760 and 0.001728414 mm. These local challenges passed their recorded budgets but did not solve a global fine-mesh optimization.

At the fixed 12-mm B-mesh stroke, time-step and contact-setting comparisons changed J by 1.86249 × 10⁻⁵ and 6.12032 × 10⁻⁵ mm; peak-force differences were 0.291199% and 0.488768%. Those overall reviews remained inconclusive. In the separate B0001 local optimal-action checks on the B mesh, time and contact changes retained the selected stroke and changed J by 4.32225 × 10⁻⁶ and 7.71423 × 10⁻⁵ mm, with peak-force changes 0.000305461% and 0.000755196%; both local checks passed. These comparisons must not be substituted for each other or described as universal convergence bounds.

Supplementary Software 1 separates three reproduction levels. First, source/evidence review uses the supplied configurations, native input snapshots, parsed results, solver receipts, search histories and SHA-256 manifest. Second, prepare\_case.py uses a bundled case and the unmodified rect\_model source with its material path redirected in memory to generate a cold-core APDL input in a new empty output directory. It does not launch the solver and refuses overwriting non-empty output. This prepare-only path was exercised with Python 3.12.14 and NumPy 2.3.5 after relocation of the package; the archived warm-run results are not asserted to equal this cold-core preparation.

Third, full native reproduction needs a licensed Mechanical APDL installation, compatible release and platform, the selected independent C0 restart state, restart and result files, complete copied-field exports and executable/path configuration. Local reference runs used release 261 (2026 R1), four cores and a Windows launcher; this does not establish the laboratory server environment. The compact archive omits multi-gigabyte result/restart binaries and large raw field text. Original controllers contain absolute paths, execution-state identities and platform-dependent launcher imports, so source snapshots require environment configuration before reuse. The compact archive alone cannot replay the archived warm branch or reconstruct 9,000 native labels. Its README and file manifest identify the included evidence and omitted dependencies.

The supplied selected-B public benchmark compares 696 observation times from one experiment. Force RMSE is 213.84028 N and peak-normalized NRMSE is 1.4366997%; computed and measured peaks are 14977.277 and 14884.1324 N. Surface-strain RMSEs at the three recorded states are 2.265 × 10⁻⁴, 1.849 × 10⁻⁴ and 1.531 × 10⁻⁴. This is a material/component-response comparison, not independent reverse-straightening validation or evidence of successful MGRE-driven actions. OPARA-derived records retain their original attribution and licence conditions; the package does not assign them a new licence.

### S-FE9. Analytical benchmark and unchanged learning-data lineage

The earlier generate\_synthetic.py labels its output an explicitly synthetic analytical toy and does not run or approximate FE. It samples six independent input variables, constructs a hand-designed positive nonlinear mean and adds artificial heteroscedastic Gaussian noise. Design seeds are 2026101601 for the 8,000 reference-domain inputs and 2026101602 for 1,000 shifted inputs; the noise and partition seeds are 2026101604 and 2026101603. The full nonlinear generator is separate from the simpler mechanical scale used by the current MGRE predictor.

The lineage audit compares both the archived earlier table and an in-memory reconstruction with the current released table: all 9,000 rows, all nine numerical fields and all partition assignments match at rtol = 10⁻¹² and atol = 10⁻¹⁰. Maximum absolute difference is 9.947598300641403 × 10⁻¹³. Current data/dataset.json has SHA-256 cb0bb4d147649378d5282b611e133f75df48e40f5e5f30af70f6813e13ff287b; the earlier dataset hash is 31514bf1ecdf78a49dc12e84cc9c64f9f920aa68abe266b15c8973bedc407d0d. Different metadata and source identifiers explain why byte hashes can differ despite numerical correspondence.

Current reproduce.py invokes the downstream fitting, table, figure and verification workflow. It does not generate target values with the old analytical script. A separate source-lineage checker reconstructs the analytical values in memory for audit only. The earlier table and generator therefore remain useful provenance artifacts and were retained. Deleting those artifacts would not change the existing learning targets or resolve their origin. No label replacement, new FE solution, model refit or publication upload was performed in this revision.
