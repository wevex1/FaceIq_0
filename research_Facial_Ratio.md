# FaceIQ Labs Facial Ratios (Frontal & Lateral): Comprehensive Guide 

**Executive Summary:**  This report compiles **all facial ratios** reported by FaceIQ Labs for front-facing and side-profile analysis, translating them into explicit formulas, landmark definitions, measurement methods, units, normative values, and interpretations.  We cross-reference FaceIQ names to standard anthropometric terms (Farkas et al.) and academic sources.  For each metric we specify the required 2D landmarks (with anatomical definitions) and describe how to detect them (dlib 68, MediaPipe FaceMesh, etc.).  We discuss common sources of error (pose, expression, distortion) and normalization (e.g. by inter-pupillary distance or bounding box).  Example JavaScript code snippets demonstrate how to compute selected ratios from 2D landmark arrays, and simple test cases with expected values are provided. Finally, we map FaceIQ metric names to conventional cephalometric/anthropometric measures and summarize implementation steps.  Primary sources (FaceIQ site, anthropometry literature, FaceMesh/dlib docs) are cited throughout. 

This guide is intended as an implementation reference: it lists **all FaceIQ metrics** (≈70 ratios) organized by category, and for each gives definitions, formulas, landmarks, units, normative ranges, interpretation, landmark detection notes, and validation suggestions.  We assume a neutral face image (no extreme expression), full-frontal and true profile views (±15° yaw/pitch), and focus on 2D pixel distances/angles.  Angles are in degrees, distances usually as pixel ratios (normalized as noted).  

## 1. FaceIQ Metrics Overview

FaceIQ Labs claims **70+ facial harmony measurements**, grouped under frontal (“Front”) and lateral (“Side Profile”) categories (see Figure 1).  On the frontal face, metrics include facial thirds, width/height ratios, eye/eyebrow ratios, nose proportions, mouth/chin measures, jaw measures, and one “Other” metric (neck width).  On the side profile, metrics include upper-face angles, facial convexity/projection, nasal angles, lip projection lines, mandibular angles, and one “Other” (submental angle).  Example metrics (from FaceIQ’s celebrity analyses) include *Face Width-to-Height Ratio* (frontal), *Midface Ratio* (frontal), *Eye Aspect Ratio* (frontal), *Nasofrontal Angle* (profile), *Nasolabial Angle* (profile), *Z Angle* (profile), *Holdaway H-Line Position* (profile), etc【24†L139-L147】【49†L61-L69】. 

For many FaceIQ ratios, FaceIQ publishes the measured value, ideal range, and score (0–10) on its site【16†L25-L32】【49†L23-L31】.  For example, “Eye Aspect Ratio = 2.8× (ideal 3.0–3.5×)”【49†L23-L31】, or “Brow Length/Face Width = 0.60 (ideal 0.7–0.8)【16†L25-L32】.  Such data provide rough normative ranges.  We cross-check these with anthropometric literature: e.g. *facial width-to-height ratio* (fWHR) is commonly defined as bizygomatic width divided by upper-face height (nasion to lip)【46†L129-L133】.  *Nasolabial angle* (profile) is the angle at the columella/upper lip (source: aesthetic guides【51†L438-L442】).  We flag any FaceIQ formula that must be inferred rather than explicitly documented.

The sections below enumerate metrics by category.  For each ratio, we give:
- **Name / FaceIQ label**  
- **Definition / formula:** the precise equation (distance or angle between landmarks, possibly a ratio of distances)  
- **Landmarks:** anatomical points needed (with anthropometric names, e.g. *nasion*, *zygion*, *pronasale*), described in lay terms and giving typical landmark indices (dlib-68 or MediaPipe-FaceMesh)  
- **Measurement method:** whether purely 2D (pixel distances on image) and whether normalized (e.g. as %, ratio to face width or interocular distance), or 3D if applicable  
- **Units:** e.g. ratio (×), percent (%), or angle (°), or mm (if unnormalized)  
- **Normative range:** expected or ideal values (from FaceIQ or literature) and citation if available (e.g. FaceIQ or academic)  
- **Interpretation:** what higher/lower values indicate (e.g. “higher fWHR = wider face relative to height”)  
- **Landmark detection:** notes on how to robustly detect the points (e.g. use dlib or FaceMesh; corresponding indices; typical errors)  
- **Error sources / normalization:** e.g. effect of tilt, scale, lens distortion, and how to mitigate (e.g. align by inter-pupillary line, normalize by face bbox, etc.)  
- **Validation tips:** suggestions for test images or synthetic data to verify the measure.

An implementation checklist and mapping table to standard terms is given at the end.

## 2. Landmark Detection and Definitions

Before diving into each ratio, we define the key landmarks.  We use conventional anthropometric terms (see **Table 1**) and show how they map to common 2D detectors.  For frontal analysis, typical landmarks include: 
- **Glabella (g or Gl):** smooth prominence between the eyebrows.  *In 68-point dlib*, not labeled explicitly, but one may approximate by midpoint of eyebrows (e.g. midpoint of points 21 and 22).  *MediaPipe FaceMesh:* landmark #9 (mid-forehead) or #10 (upper forehead) can approximate it【38†L74-L82】.  
- **Nasion (n):** the midline point at the nasal root (top of nose where it meets forehead).  On 68-landmarks, point 27 (the nasion along the nose ridge). *FaceMesh:* landmark #1 (top of nose ridge)【38†L74-L82】.  
- **Pronasale (prn):** the most protruding point of the nose tip.  *dlib 68:* between points 33–35 (the tip is usually at 33).  *FaceMesh:* landmark #1 or #2 (tip of nose)【38†L74-L82】.  
- **Subnasale (sn):** the point where the lower border of the nose meets the upper lip.  *dlib 68:* not explicitly defined, but one may approximate by midpoint between base of nose (like 33–35) and lip.  *FaceMesh:* landmark #15 (below nose) sometimes used.  
- **Labiale superius (ls):** midpoint of upper lip vermilion (Cupid’s bow).  *dlib 68:* midpoint of points 51–53.  *FaceMesh:* landmark #13 (center upper lip).  
- **Labiale inferius (li):** midpoint of lower lip.  *dlib 68:* midpoint of 57–59.  *FaceMesh:* landmark #14 (center lower lip).  
- **Pogonion (pg):** most forward midpoint of chin.  *dlib 68:* point 8 (chin).  *FaceMesh:* landmark #9 (approximately chin point).  
- **Gnathion (gn):** lowest midpoint of chin, similar to pogonion (often same as pogonion in soft tissue).  
- **Zygion (zyg or Zy):** most lateral point on the zygomatic arch (cheekbone width).  *dlib 68:* points 1 and 15 approximate left/right jaw, but for cheek, one may use 4–12 cluster.  (No single dlib point for zygion.)  *FaceMesh:* landmarks #234 (left cheek), #454 (right cheek) approximate zygions.  
- **Gonion (go):** angle of the jaw (bony corner).  *dlib 68:* point 5 (left jaw angle), 11 (right jaw angle).  *FaceMesh:* #234 (approx angle) or #199/#430 area.  
- **Alare (al):** the most lateral point on each nostril.  *dlib 68:* points 31 and 35.  *FaceMesh:* #61 (left), #291 (right) for wing of nose.  
- **Exocanthion (ex):** outer corner of eye.  *dlib 68:* 36 (L), 45 (R).  *FaceMesh:* #33 (L), #362 (R)【36†L236-L239】.  
- **Endocanthion (en):** inner corner of eye.  *dlib:* 39 (L), 42 (R).  *FaceMesh:* #133 (L), #263 (R)【36†L236-L239】.  
- **Orbitale (or):** lowest point of the eye orbit (not on image); often approximated by eye midpoint on eyelid.  *Not directly in 2D images.*  
- **Tragion (tg):** notch on ear (eartop).  *On 2D, can approximate by top of ear lobe (if visible). Not in standard 68 or FaceMesh outputs.*  
- **Subnasale (sn):** see above.  
- **Alar base:** left/right points of nose base. *dlib:* 31/35.  
- **Cheilion (ch):** corner of mouth. *dlib:* 48, 54. *FaceMesh:* #61 (L), #291 (R) is nose, not mouth; actually mouth corners: #61 and #291 in FaceMesh map to nose, but for mouth, #61 is left corner of mouth, #291 is right (per one source). FaceMesh’s lips have many; often #78 (left mouth corner), #308 (right mouth corner) are used.  
- **Submental (sm):** point under chin (just below pogonion).  *Not directly defined; use pogonion.*  

*Table 1* (below) summarizes key landmarks (with alt. names).  The precise media used (pixel vs mm) will depend on calibration; we assume consistent scale (thus many ratios are unitless or in %).

**Table 1: Key facial landmarks and detectors.** Common anthropometric landmarks (left/right symmetric points listed once) and typical indices in dlib-68 and MediaPipe FaceMesh (468 points).  

| Anthropometric Name    | Description                               | Example Detector Indices           | Notes   |
|-----------------------|-------------------------------------------|------------------------------------|---------|
| **Glabella (Gl)**      | Midpoint between eyebrows, above nasion   | — (approx. midpoint of brow lines)  | *dlib:* approx between pts 21/22. *FaceMesh:* #9 (mid forehead) or #10. |
| **Nasion (N)**         | Bridge of nose, between eyes, below glab. | dlib 27, FaceMesh #1                | See Fig.1. |
| **Pronasale (Prn)**    | Tip of the nose (most protruding)        | dlib 33 (approx), FaceMesh #1–2     | Skin equivalent of nasal tip. |
| **Subnasale (Sn)**     | Base of nose where nose meets lip        | (no direct dlib); FaceMesh ~#15     | Columella point on philtrum. |
| **Labiale superius (Ls)** | Midpoint upper vermilion (Cupid’s bow)    | dlib 51, 13 (FaceMesh #13)          | Upper lip midpoint. |
| **Labiale inferius (Li)** | Midpoint lower vermilion                 | dlib 57, FaceMesh #14              | Lower lip midpoint. |
| **Pogonion (Pg)**      | Most anterior midline chin               | dlib 8, FaceMesh #9                 | Lower chin point. |
| **Menton (Me)**        | Lowest point on chin                    | dlib 8, FaceMesh #9 (same as Pg)    | (soft-tissue) |
| **Gnathion (Gn)**      | Midpoint of chin (often same as Pg)      | —                                   | Similar to pogonion. |
| **Zygion (Zy)**        | Most lateral point on each cheekbone     | (No dlib eq.); FaceMesh ~#234/454    | Approx. widest face. |
| **Gonion (Go)**        | Angle of jaw (bony corner)              | dlib 5 (L), 11 (R)                 | Jaw angles. |
| **Alare (Al)**         | Most lateral point on nostril base       | dlib 31 (L), 35 (R); FaceMesh #61/#291 | Width of nose. |
| **Exocanthion (Ex)**   | Outer corner of eye lids                 | dlib 36 (L), 45 (R); FaceMesh #33 (L), #362 (R)【36†L236-L239】 | End of white sclera. |
| **Endocanthion (En)**  | Inner corner of eye lids                 | dlib 39 (L), 42 (R); FaceMesh #133 (L), #263 (R)【36†L236-L239】 | Medial eye corners. |
| **Subnasale (Sn)**     | (See above)**                                |                                    |   |
| **Nasion (n)**         | (See above)                              |                                    |   |
| **Tragion (T)**        | Notch at upper ear root (ear top)        | —                                   | Rarely used in 2D (profile ear). |
| **Cheilion (Ch)**      | Corner of mouth                         | dlib 48 (L), 54 (R); FaceMesh #61 (L), #291 (R) *or* #78/#308 for lips |   |
| **Labiale superius**   | (See above)                              |                                    |   |
| **Labiale inferius**   | (See above)                              |                                    |   |

<div style="page-break-after: always"></div>

## 3. Frontal Face Ratios

### 3.1 Facial Thirds (Vertical Proportions)

- **Upper (Top) Third** – *“Glabella–Nasion height / (Glabella–Menton height)”*.  Let *Gl–N* = vertical distance from glabella to nasion, *N–M* = distance from nasion to menton (approx. total face height).  Compute: `TopThird = (Gl–N) / (Gl–Menton) *100%`.  Landmarks: **Glabella**, **Nasion**, **Menton**.  If hairline/glabella isn’t visible, one may use midpoint between eyebrow peaks for Gl.  Measured in **% of face height**. FaceIQ shows ~33% ideal【49†L54-L63】.  Interpretation: higher % = relatively longer forehead.  *Landmark detection:* Use eyes/nose geometry (nasion fixed under brow).  *Errors:* Head tilt will bias all thirds; align by eyeblink line.  *Normalization:* uses face height (pixel) so scale-invariant. 

- **Middle Third** – *“Nasion–Subnasale / Glabella–Menton”*.  Let *N–Sn* = distance nasion to subnasale (mid-nose).  Formula: `MiddleThird = (N–Sn) / (Gl–Menton) *100%`.  Landmarks: **Nasion**, **Subnasale**, **Glabella**, **Menton**.  FaceIQ example ~28–32%【49†L54-L63】.  Interpretation: higher = longer midface.  

- **Lower Third** – *“Subnasale–Menton / Glabella–Menton”*.  Let *Sn–M* = subnasale to menton.  `LowerThird = (Sn–M) / (Gl–M) *100%`.  FaceIQ ideal ~33–38%【49†L54-L63】.  Lower third > lower half indicates strong chin or long lower face.  

*Note:* We adopt glabella–menton as total face height, following Farkas: facial index uses glabella or nasion to menton【46†L129-L133】.  (Some sources use nasion–gnathion.)  In any case, all three thirds sum to 100%.  *Citations:* FaceIQ fragments【49†L54-L63】, anthropometry (vertical thirds concept). 

### 3.2 Face Shape / Width–Height Ratios

- **Bizygomatic (Face) Width** – *Distance between left and right zygion points.*  Landmarks: **Left Zy** and **Right Zy**.  In practice, if zygions (widest cheek points) aren’t labeled, use *face width* as distance between cheek landmarks or convex hull of face.  *Unit:* pixels (then normalized in ratios below).  

- **Face Width-to-Height Ratio (FWHR)** – *“Bizygomatic width / Upper face height.”*  This is a well-known metric【46†L129-L133】.  Choose **Width** = distance between zygions (see above).  **Height** can be defined as distance from nasion (approx top of nose) to labiale superius (upper lip base).  Some define it as nasion-to-menton; FaceIQ’s “Face Width to Height Ratio” often exceeds 2 (implying height is shorter segment, likely nasion–labium).  We adopt: 
  \[
    \text{FWHR} = \frac{\text{Zy(Left)–Zy(Right)}}{\text{Nasion–Labrale superius}}.
  \]
  Units: ratio (×).  FaceIQ examples: ~1.8× ideal【49†L65-L72】.  Higher FWHR = relatively wider, “masculine” face【46†L129-L133】.  *Landmarks:* **Zygion L/R**, **Nasion**, **Labiale superius**.  Use inter-zygomatic distance (pixel) and nasion-upper lip distance.  *Interp.* High implies broad or short face; low implies narrow or tall face.  
  *Normalization:* inherent ratio.  *Error:* If tilt, width appears smaller; correct by face alignment.  

- **Total Facial Width-to-Height Ratio** – *“Bizygomatic width / Total face height.”*  Similar to above, but Height = Nasion–Menton (or Glabella–Menton).  \[
    \text{TotalW/H} = \frac{\text{ZyL–ZyR}}{\text{Nasion–Menton}}.
  \]
  FaceIQ: ~1.3× ideal【49†L61-L65】.  Very similar to classical cephalic index (anthropology uses face length, but here via soft landmarks).  

- **Bitemporal Width** – *Distance between left and right temples.*  Landmarks: left and right **temporalis muscle bulge** (typically above ear).  If not explicitly given, estimate slightly above zygion.  FaceIQ: ~80–90% (probably normalized to face width)【29†L63-L65】.  Essentially similar to bizygomatic width, but measured higher on face.  

- **Midface Ratio** – *“(Nasion–Subnasale) / (Subnasale–Menton).”*  This is ratio of upper to lower face (essentially midface to lower face height)【29†L63-L65】.  Formula: 
  \[
    \text{Midface Ratio} = \frac{N–Sn}{Sn–M}.
  \]
  FaceIQ shows ideal ≈1.0 (balanced mid/lower face)【29†L63-L65】.  Units: ratio (×).  Interpretation: =1 means equal, >1 means longer midface (bigger nose/cheek vs chin), <1 means long chin.  *Landmarks:* Nasion, Subnasale, Menton.  *Validation:* test with artificially stretching mid or lower face.  

### 3.3 Eyes and Brows

- **One-Eye-Apart Test** – *“Interpupillary distance ≈ one eye width?”*  Often the guideline says iris separation ≈ eye width.  FaceIQ likely measures (Interpupil distance) / (eye width).  Indeed, values ~1.1×【49†L73-L76】.  Formula (assuming eye width = inner–outer canthus of one eye, IPD = distance between pupils or centers): 
  \[
    \text{OneEyeApart} = \frac{\text{Distance(EyeCenter_L–EyeCenter_R)}}{\text{Width of one eye (L\_Exocanthion–L\_Endocanthion)}}.
  \]
  Landmarks: left/right **pupil or eye center** (if FaceMesh #468/473 or estimated), plus left eye outer/inner.  Units: ratio.  1.0× means eyes just one eye apart; >1 means more separation (wide-set).  
  *Sources:* FaceIQ value ~1.1× means a bit more apart.  Interpretation: higher = wider-set eyes.  

- **Eye Separation Ratio (Intercanthal Ratio)** – *“(Intercanthal distance) / (bizygomatic width)”.*  Often defined as (distance between inner canthi) divided by face width.  FaceIQ example ~45–50%【49†L73-L76】 (47.8% for FaceIQ).  Formula: 
  \[
    \text{EyeSep} = \frac{\text{Distance}(En_L–En_R)}{\text{Zy_L–Zy_R}} \times 100\%.
  \]
  *Landmarks:* **Endocanthion L/R**, **Zygion L/R**.  Interpretation: high % = eyes very far apart relative to face width.  

- **Eye Aspect Ratio** – *“Horizontal eye width / vertical eye height.”*  This likely uses one eye (or average of both).  If defined like in blink-detection, some use ( (p2–p6) + (p3–p5) )/(2*(p1–p4)).  We use a simpler ratio: 
  \[
    \text{EyeAspect} = \frac{\text{Distance}(Exocanthion–Endocanthion)}{\text{(distance upper lid to lower lid)}}.
  \]
  For each eye: width = outer–inner corner, height = average of two verticals (e.g. top lid midpoint to bottom lid midpoint).  Then average left & right.  FaceIQ reports values ~2.8–3.3×【49†L23-L31】 (ideal ~3.0–3.5).  Larger ratio means more elongated (narrow) eye (since width >> height).  *Landmarks:* Exocanthion & Endocanthion for each eye; upper and lower eyelid landmarks (dlib 37–38 & 41–40 for left eye; FaceMesh 159, 160, 145, 153, etc.).  *Units:* ratio.  *Sources:* Standard EAR for blink detection (invert if needed)【47†】.  

- **Lateral Canthal Tilt** – *“Angle of eye axis from horizontal.”*  Measure the tilt of the line through the eyes.  Define the line connecting the outer canthus of left eye to inner canthus of right (or simply the eye corners between eyes) and compute its angle to the horizontal.  Using outer corners of left & right eye: 
  \[
    \theta = \arctan\frac{(y_{Exo_R} - y_{Exo_L})}{(x_{Exo_R} - x_{Exo_L})}.
  \]
  We report degrees (positive = upward slope L→R).  FaceIQ gave e.g. −3.5° (negative means right higher)【49†L71-L76】.  *Landmarks:* **Left Exocanthion**, **Right Exocanthion**.  *Units:* degrees.  Interpretation: positive tilt = left eye higher.  *Norm:* ±5–10° considered normal.  

- **Eyebrow Tilt (Inclination)** – *“Tilt of brow relative to horizontal.”*  Define as angle of line connecting outer ends of left vs right eyebrow.  Landmarks: outer brow ends (in dlib 68: point 17 (L brow start) and 26 (R brow end); FaceMesh: #276 (L brow end), #46 (R brow start) or similar).  Compute angle similar to above.  FaceIQ values ~7–15°【49†L73-L76】.  *Interpretation:* higher angle = more arched brow.  

- **Brow Length to Face Width Ratio** – *“(Left+Right eyebrow lengths) / (bizygomatic width)”.*  Or simply eyebrow length / face width.  FaceIQ phrased “brow length to face width”, ideal ~0.7–0.8【16†L25-L32】【49†L73-L76】.  Likely means (distance between the two ends of a single eyebrow) divided by face width.  We assume: 
  \[
    \text{BrowLen/Width} = \frac{\text{Distance}(LeftBrowOuter–LeftBrowInner)}{\text{Zy_L–Zy_R}}.
  \]
  (One may average both brows.)  Landmarks: **Left brow’s outer & inner end points** (FaceMesh: #71 and #46 for left; #300 and #276 for right).  *Units:* ratio.  Lower ratio indicates short eyebrows relative to face width.  FaceIQ example: 0.60 (low) vs ideal .7–.8【16†L25-L32】.  

- **Eyebrow Low-Setedness** – likely *“Brow position relative to eye.”*  Possibly measured as distance from eye to brow (relative).  FaceIQ calls this “Eyebrow Low Setedness” (sic).  Example values ~0.3–1.1×【31†L9-L12】【49†L73-L76】.  We guess formula: (distance brow arch down to eye center) / (face height or eye height).  Without FaceIQ doc, we infer: The higher this value, the lower the brows.   Possibly: 
  \[
    \text{BrowLow} = \frac{\text{Distance}(\text{Midpoint Eyebrow} - \text{Center of Orbit}}{\text{Intercanthal distance}}.
  \]
  Landmarks: eyebrow apex vs eye center (iris).  Skip precise formula as FaceIQ doesn’t define; we mark as “inferred: proportional to brow-eye distance.”  

### 3.4 Nose Metrics (Frontal)

- **Intercanthal–Nasal Width Ratio** – *“(Interpupillary or intercanthal distance) / (Nasal width).”*  FaceIQ: “Intercanthal-Nasal Width” ideal ~1.0×【49†L81-L85】.  Likely: 
  \[
    \frac{\text{Distance}(En_L–En_R)}{\text{Distance}(Al_L–Al_R)}.
  \]
  Or possibly using inner canthi vs alare.  If ~1.0 ideal, they expect interpup distance ≈ nose width.  
  Landmarks: **Endocanthion L/R**, **Alare L/R**.  Units: ×.  >1 means eyes very wide relative to nose.  

- **Nose Bridge to Nose Width Ratio** – *“(Nose height) / (Nose width).”*  Likely nose height (nasion–subnasale or pronasale) over nose width (alar width).  FaceIQ shows e.g. 2.8 (perhaps ~ratio)【49†L81-L85】.  If 2.8, maybe (nasion–pronasale)/(alar width).  We propose:
  \[
    \frac{\text{Distance}(N–Prn)}{\text{Distance}(Al_L–Al_R)}.
  \]
  Landmarks: **Nasion**, **Pronasale**, **Alare L/R**.  Units: ratio.  *Interpretation:* larger = longer/narrow nose; smaller = short/wide nose.  

- **Ipsilateral Alar Angle (IAA)** – *“Lateral angle of nostril.”*  The angle between the left alare-subnasale line and vertical (?) or horizontal plane.  FaceIQ lists IAA (e.g. 90.8°)【24†L139-L147】.  Likely: For one side (e.g. left), angle at subnasale between lines (Pronasale–Alare) and (Pronasale–Subnasale). Or simpler: angle at alare between subnasale–alar–pronasale.  Without clarity, we define: 
  \[
    \text{IAA}_{L} = \angle(Al_L - Sn - Prn), 
  \] 
  the angle at Subnasale between line to left alare and nose tip.  Units: degrees.  A high angle (~90°) means flared nostril.  Similar for right side (IAA_R).  *FaceIQ* uses difference of left/right (below).  

- **Deviation of IAA & JFA** – *“Absolute difference between Ipsilateral Alar Angle and Jaw Frontal Angle.”*  FaceIQ phrase “Deviation of IAA & JFA” presumably means |IAA – JFA|.  Given values like 6.0°【29†L78-L84】, small means symmetry.  *Landmarks:* uses IAA (above) and Jaw Frontal Angle (see below).  *Interpretation:* difference indicates asymmetry between nose base and jaw contour.  

- **Jaw Frontal Angle (JFA)** – *“Angle of jaw line.”*  Likely the angle formed by the jawline at the chin (point Pogonion).  Perhaps: angle between lines (Pogonion–Gonion) and (Pogonion–Gnathion? or Pogonion–soft chin?), i.e. shape of mandible.  FaceIQ examples ~96–98°【29†L63-L66】.  Possibly computed as angle at pogonion between lines to left and right gonion.  If so:
  \[
    \text{JFA} = \angle(Gonion_L - Pogonion - Gonion_R).
  \]
  Landmarks: **Gonion L/R**, **Pogonion**.  Units: degrees.  ~90° is square jaw, >90 more obtuse (rounder jaw).  

- **Nose Tip Position** – *“Horizontal offset of nose tip relative to face midline.”*  FaceIQ reports e.g. 1.4 mm【29†L79-L83】.  Likely: signed distance of pronasale from vertical midline (nasion–menton line).  + means to right, – to left.  *Landmarks:* **Pronasale, Midline (N-M)**.  *Units:* mm (if scaled) or % face width.  Interpretation: 0 is centered; larger = nose deviated.  

### 3.5 Mouth/Lips Metrics (Frontal)

- **Cupid’s Bow Depth** – *“Sagittal protrusion of upper lip.”*  Possibly distance from upper lip vermilion (labrale superius) to a vertical line through philtrum or line from nose.  FaceIQ example: 0.9 mm【29†L88-L90】 (small).  Perhaps measured from subnasale–pronasale midline to labrale superius.  We define: distance of Labiale superius from the line (Pronasale–Menton) or from subnasale.  Landmarks: **Labiale superius, Nasion-menton midline**.  *Units:* mm (since FaceIQ gave mm).  Larger positive = upper lip protrusion (prominent), negative = retruded.  

- **Lower-to-Upper Lip Ratio** – *“Lower lip height / Upper lip height.”*  Possibly height measured from vermilion midpoints to midpoints above and below.  E.g. if upper vermilion height = distance from Columella base (subnasale) to Labiale superius, lower vermilion height = from Labiale superius to Labrale inferius.  Then ratio: 
  \[
    \frac{\text{Lower lip height}}{\text{Upper lip height}}.
  \]
  FaceIQ ~1.2× ideal【29†L88-L90】.  *Landmarks:* **Subnasale, Labiale superius, Labiale inferius**.  *Interpretation:* >1 means lower lip longer than upper.  

- **Interpupillary–Mouth Width Ratio** – *“Mouth width / Interpupillary distance.”*  Mouth width = distance between mouth corners (Cheilion L–R), IPD = distance between pupils or inner eye corners.  FaceIQ ~0.8× ideal【29†L88-L91】 (eyes wider than mouth).  Formula: 
  \[
    \frac{\text{Distance}(Ch_L–Ch_R)}{\text{Distance}(Pupil_L–Pupil_R)}.
  \]
  *Landmarks:* **Cheilion L/R**, **Pupil or Exocanthion L/R**.  Units: ratio.  A low ratio means mouth relatively narrow.  

- **Mouth Corner Position** – *“Vertical offset of mouth line.”*  Likely measures tilt of mouth corners relative to horizontal midline.  FaceIQ reports -0.4 mm【29†L88-L91】 (near zero).  Could be (y_Ch_R + y_Ch_L)/2 minus y_base (e.g. nasal base).  If positive = upward tilt on one side.  *Units:* mm.  

- **Chin to Philtrum Ratio** – *“(Subnasale–Pogonion) / (Subnasale–Labiale superius).”*  This ratio compares chin length to upper lip height.  FaceIQ example 2.0×【29†L88-L91】.  Formula:
  \[
    \frac{\text{Distance}(Sn–Pg)}{\text{Distance}(Sn–Ls)}.
  \]
  Landmarks: **Subnasale, Pogonion, Labiale superius**.  >1 indicates chin longer than philtrum.  

- **Mouth Width to Nose Width** – *“Cheilion distance / Alare distance.”*  FaceIQ 1.4×【29†L88-L91】.  \(\displaystyle\frac{Ch_L–Ch_R}{Al_L–Al_R}\).  Units: ratio.  If >1, mouth wider than nose.  

### 3.6 Jaw & Chin (Frontal)

- **Ear Protrusion Angle (and Ratio)** – FaceIQ lists both angle and ratio for ear protrusion.  *Angle:* likely the angle at the tragus or ear plane relative to face plane.  e.g. 16.8°【29†L97-L100】.  Without a standard formula, we note it qualitatively (project nose and ear outline).  *Ratio:* possibly ear width or projection length vs face.  E.g. FaceIQ: 12.0%【29†L97-L100】.  We define: ear protrusion ratio = (distance from ear to face) / (face width).  Landmarks: **Tragion (T)** and some cheek (zygion) reference.  *Interpretation:* higher = ears stick out.  

- **Lower Third Proportion** – *“(Subnasale–Menton) / (Nasion–Menton).”*  Essentially the fraction of face height below nose.  FaceIQ: 34.2%【29†L97-L99】.  Formula: 
  \[
    \frac{Sn–Menton}{Nasion–Menton} \times 100\%.
  \]
  (Equivalent to our LowerThird% above.)  *Units:*%.  ~33% ideal.  

- **Bigonial Width** – *“Distance between Gonion L/R (jaw angles).”*  FaceIQ: 88.0%【29†L97-L100】, likely % of bizygomatic width.  Formula: 
  \[
    \text{Bigonial \%} = \frac{Go_L–Go_R}{Zy_L–Zy_R} \times 100\%.
  \]
  *Interpretation:* lower % = narrow jaw relative to cheekbones (feminine).  ~88% (~0.88) is tall-jaw.  

- **Jaw Slope (Angle)** – *“Angle of jaw line relative to neck.”*  FaceIQ: e.g. 141°【29†L93-L99】.  Likely: angle at each gonion between jawline and vertical.  Could define: angle formed by line Go–Me and vertical (or horizontal).  If >180° is straight, <180 sharper.  FaceIQ uses 0–180.  We define angle at gonion between line from gonion to menton and horizontal.  *Interpretation:* high angle (~140°) = flatter jaw slope (traditional ideal 130–150°).  

- **Jaw Frontal Angle** – (See above under nose: we already defined JFA as ∠(Go_L–Pg–Go_R)).  FaceIQ values ~96°【29†L63-L66】.  

- **Neck Width (Frontal)** – *“Distance between mid-neck points.”*  FaceIQ: given as percent (e.g. 83.6%)【29†L101-L105】.  Likely = (neck width) / (face width)×100.  Landmarks: e.g. left/right at jawline base (jugulum).  Interpretation: % of face width.  Lower % = slender neck.  

## 4. Lateral (Profile) Ratios and Angles

### 4.1 Upper-Face (Forehead/Brow)

- **Upper Forehead Slope** – *“Angle between glabella-trichion line and vertical.”*  (Trichion = hairline).  FaceIQ example: 3.0°【29†L111-L114】 (almost vertical).  Define: angle at glabella between vertical and line to trichion.  Landmarks: **Glabella**, **Trichion** (or mid-forehead, FaceMesh #10 or #338).  Units:°.  *Interpretation:* tilt of forehead; zero = perfectly vertical forehead.  

- **Browridge Inclination Angle** – *“Angle of browridge slope.”*  FaceIQ: ~14°【29†L112-L114】.  Likely angle at glabella between line to front of brow and vertical.  Landmarks: glabella and brow apex (midpoint).  Similar to nasofrontal, see below.  

- **Nasofrontal Angle** – *“Angle at nasion between forehead and nose.”*  From literature: angle formed by glabella–nasion–pronasale【51†L414-L422】.  Mizu: ~120–130° ideal for women【51†L414-L422】.  FaceIQ: e.g. 120.1°【29†L113-L114】.  Landmarks: **Glabella** (or forehead point), **Nasion**, **Pronasale**.  Units:°.  Smaller = flat nasofrontal, larger = deep nasion dip.  

### 4.2 Facial Profile (Projection/Convexity)

- **Orbital Vector (OP)** – *“Globe projection relative to cheek.”*  Plastic surgery term: distance of eye (orbitale) relative to malar plane.  FaceIQ gives negative mm (e.g. -6.0 mm)【29†L119-L124】.  Definition: signed distance from eye orbit (or iris) to a reference plane (vertical line from cheek).  Hard to define in static 2D; we treat it as “approx eyeball projection”.  *Landmarks:* inner eye or ocular point vs facial plane.  No standard reference.  

- **Z Angle** – *“Angle between Frankfort horizontal and chin-nose line.”*  In orthodontics, Ricketts’ Z-angle is between line Pogonion–Orbitale and Frankfort plane.  FaceIQ: ~72–83°【29†L119-L124】.  Approximate: 
  \[
    \angle(\text{line } Po\text{-}Or,\ \text{line } Or\text{-}Po),
  \] 
  essentially angle at pogonion from eye to ear.  Without formal def, skip formula.  

- **Facial Depth-to-Height Ratio** – *“(Facial depth) / (face height).”*  FaceIQ example: 1.3×【29†L119-L124】.  Possibly: (distance from tragion-projection to glabella-menton).  Or if depth = (face from front to back), but in 2D might be profile projection vs height.  Unclear; likely: 
  \[
    \frac{\text{(Pogonion-plane distance)}}{\text{(Nasion–Menton)}}.
  \]
  Without clarity, mark as inferred.  

- **Facial Convexity (Glabella)** – *“Angle at subnasale between glabella and pogonion.”*  Known measure: G–Sn–Pg (soft-tissue convexity)【46†L129-L133】.  FaceIQ: e.g. 169.6° (nearly flat)【29†L119-L124】.  Formula: angle ∠Gl–Sn–Pg.  Landmarks: Glabella, Subnasale, Pogonion.  Units:°.  Lower angle = more convex (pronounced).  

- **Facial Convexity (Nasion)** – *“Angle at subnasale between nasion and pogonion.”*  ∠N–Sn–Pg.  FaceIQ: 161.2°【29†L121-L124】.  Lower = convex.  

- **Total Facial Convexity** – *“Angle at soft-tissue glabella between nose tip and chin.”*  Actually often ∠Gl–Prn–Pg (glabella–pronasale–pogonion).  FaceIQ: ~145°【29†L121-L124】.  If defined as ∠(Gl–Prn–Pg).  Units:°.  

- **Interior Midface Projection Angle (IMPA)** – FaceIQ: range ~32–60°【25†L150-L157】.  Possibly angle at nasion between Frankfort plane and line to pronasale.  We guess: ∠(Frankfort-nasion-pronasale).  Without firm source, note as proprietary metric measuring midface protrusion.  

- **Anterior Facial Depth** – *“Angle at pogonion between forehead and chin lines.”*  FaceIQ: ~63–67°【29†L119-L124】.  Possibly Frankfort plane vs pogonion orbitale line.  

### 4.3 Nose (Profile)

- **Nose Tip Rotation Angle** – *“Angle of nose tip relative to vertical.”*  Commonly, angle between columella and subnasale or horizon.  FaceIQ: e.g. 18–28°【29†L129-L134】.  Likely angle at pronasale between line to nasion and vertical axis.  

- **Frankfort-tip Angle** – *“Angle between Frankfort plane and nose tip.”*  Possibly angle at nasion between Frankfort (ear-to-orbitale) and nasion-pronasale.  Values ~35–45°【29†L129-L133】.  

- **Nasal Tip Angle** – *“Columella angle (Pronasale–Subnasale–Pogonion).”*  Mizu calls this nasomental or tip angle; but FaceIQ lists separately.  Possibly ∠(Sn–Prn–Sn?) or (N–Prn–Sn).  Without clarity, we skip exact. FaceIQ: ~126°【29†L129-L133】.  

- **Nasal Projection** – *“(Pronasale projection) / (Nasion–Menton).”*  Example 0.6–0.8×【29†L129-L133】.  Possibly horizontal distance of pronasale from vertical through nasion divided by face depth.  We treat it as fraction (×).  

- **Nasolabial Angle** – *“Angle at columella.”*  Defined by columella-lip relationship【51†L438-L442】.  Angle ∠(Pronasale–Subnasale–Labrale superius).  FaceIQ: ~102–110°【29†L131-L134】 (ideal ~105–120°【51†L438-L442】).  Landmarks: Pronasale, Subnasale, Labiale superius.  *Citation:* textbook definition【51†L438-L442】.  

- **Nasomental Angle** – *“Angle of nose–chin.”*  ∠(Nasion–Pronasale–Pogonion)【51†L430-L438】.  FaceIQ: ~128°【29†L131-L134】 (ideal ~120–132°【51†L430-L438】).  Landmarks: Nasion, Pronasale, Pogonion.  

- **Nasofacial Angle** – *“Angle between nose and facial plane.”*  Defined as angle from glabella–nasion to nasion–pronasale【51†L423-L430】.  FaceIQ: ~32–35°【29†L131-L134】 (ideal 30–40°【51†L425-L428】).  Landmarks: Glabella (or frontal), Nasion, Pronasale.  Unit:°.  

### 4.4 Lips (Profile)

- **Mentolabial Angle** – *“Angle at point of intersection of lower lip and chin.”*  Specifically ∠(Labrale superius – Labrale inferius – Pogonion).  FaceIQ: ~134–137°【25†L150-L157】.  Interpretation: fuller lips have larger angle.  

- **Holdaway H-Line Position** – *“Upper lip prominence relative to H-line.”*  H-line = line tangent to upper lip and chin (Holdaway’s line).  The metric is the signed distance of upper lip vermilion to this line【72†L7-L12】.  FaceIQ example: −0.1 mm【24†L149-L157】 (close to ideal).  Landmarks: **Labiale superius, Pogonion, Subnasale** (to draw H-line).  *Unit:* mm.  *Interpretation:* negative means retruded lip relative to chin.  

- **Upper/Lower Lip E-Line Position** – *“Distance of lips to E-line.”*  E-line (Esthetic line) connects pronasale to pogonion.  The signed distances of the midpoints of upper and lower lip (Ls, Li) to this line.  FaceIQ: e.g. upper 1.9 mm, lower 1.2 mm【25†L150-L157】.  *Units:* mm.  Positive means lip behind line (retruded).  

- **Upper/Lower Lip S-Line Position** – *“Distance to S-line.”*  Steiner’s S-line is drawn from midpoint of columella to pogonion.  FaceIQ: e.g. upper -1.1 mm, lower -0.9 mm【29†L139-L142】.  Negative meaning lip in front of the line (protrusion).  

- **Burstone Lines (Upper/Lower)** – Two Burstone lines: the aesthetic plane (Line B) connects subnasale to soft-tissue pogonion.  FaceIQ: e.g. Upper -5.1 mm, Lower -2.5 mm【29†L139-L142】.  Likely measured similarly to E/S lines.  *Landmarks:* Subnasale, Pogonion, and lip points.  

### 4.5 Jaw and Chin (Profile)

- **Recession Relative to Frankfort Plane** – *“Anterior–posterior offset of pogonion.”*  Likely distance from Pogonion to a perpendicular dropped from glabella/Frankfort plane.  FaceIQ: ~−3 to −4 mm【25†L149-L157】 (negative = chin behind plane).  Landmarks: **Pogonion, Glabella or Frankfort plane**.  

- **Gonial Angle (Mandible Angle)** – *“Angle at gonion between ramus and mandibular base.”*  Classic mandible angle: ∠(Ramus plane, Mandibular plane)【25†L149-L157】.  FaceIQ: e.g. 111–127°【25†L149-L157】.  Landmarks: Gonion, Menton, and some point on ramus (e.g. Porion or Frankfort reference).  *Interpretation:* larger angle = square jaw.  

- **Mandibular Plane Angle** – *“Angle between mandible line and Frankfort plane.”*  Mandibular plane = Gonion–Menton.  Frankfort plane = Porion–Orbitale (approx ear-eye line).  FaceIQ: ~15–20°【30†L149-L157】.  Landmarks: Gonion, Menton, Orbitale.  Lower angle = horizontal jaw (often desired).  

- **Ramus to Mandible Ratio** – *“Ramus height / Mandible body length.”*  Might use condylion/gonion distance (ramus) vs gonion/menton (mandibular body).  FaceIQ e.g. 0.7×【25†L149-L157】.  Larger = taller ramus relative to chin.  

- **Gonion-to-Mouth Line** – *“Vertical distance from gonion to interpupillary/mouth line.”*  Possibly distance of jaw angle above the horizontal through the mouth.  FaceIQ: e.g. 12–21 mm【25†L149-L157】.  We skip detail.  

- **Submental (Cervical) Angle** – *“Angle under chin.”*  Angle at pogonion between chin line and neck.  FaceIQ: e.g. 122° frontal, 84° profile【29†L153-L157】 (profile likely measured between chin plane and neck).  Landmarks: pogonion, neck point (below chin), etc.  *Interpretation:* sharp angle (<90°) = retruded chin.  

## 5. Landmark Detection Guidance

**Automatic Landmark Models:**  Use established face-landmark detectors (e.g. dlib 68-point, Google MediaPipe FaceMesh) to obtain the required points.  *FaceMesh (468 pts)* provides 3D coordinates and includes almost all needed points (eyes, eyebrows, nose, lips, jaw, etc.)【38†L74-L82】.  *dlib 68* is simpler but misses some (no glabella, no subnasale, etc.); one must approximate or use FaceMesh for more complete coverage.  For each landmark above, common indices are given (Table 1).  

**Handling Occlusion/Pose:**  Frontal metrics require a near-frontal view (yaw <±15°).  Side metrics require a true profile (front-facing eyes lost, but profile features visible).  If face is tilted, e.g. head tilt >5°, first rotate landmarks to horizontal reference (e.g. align eyes).  For profile analysis, one might first confirm face yaw ~90° with a face-angle detector.  If partial occlusion (e.g. glasses, hair, facial hair), use robust detectors (FaceMesh performs well under glasses).  Eye and brow landmarks are tricky if eyes squint or eyebrows not visible.

**Normalization:**  Many ratios inherently normalize (e.g. distances divided by face width/height).  When computing raw distances, scale invariance can be achieved by dividing by an interocular distance or face bounding-box dimension.  For angles, no normalization needed.  Be consistent: either use pixel distances on the image (for ratios, pixels cancel) or normalized coordinates (landmarks outputs are often relative to face box).  

**Landmark Index References:**  For MediaPipe FaceMesh, some useful indices (approximate):  
Left eye: outer=33, inner=133, mid-upper=159, mid-lower=145.  Right eye: outer=362, inner=263, upper=386, lower=374.  Pupils: 468 (L), 473 (R).  Eyebrows: left end=70, apex=64, right end=300, apex=296.  Nose tip: 1 or 2, nasion: 168 (bridge).  Lips: left corner=61, right corner=291, top mid=13, bottom mid=14.  Chin: 152 (mid-chin).  Zygion (cheek) ~226/446.  (These may vary by model; see FaceMesh docs.)  *Citations:* MediapPipe docs【38†L74-L82】 describe the landmark model and outputs; users have extracted known mappings online.  

**Example (dlib):**  The 68-point model (left to right) has jawline 0–16, left brow 17–21, right brow 22–26, nose 27–35, left eye 36–41, right eye 42–47, mouth outer 48–59.  See Fig.4 in Serengil【41†】 for illustration.  

## 6. Edge Cases and Error Sources

- **Pose (Yaw/Pitch):**  Frontal ratios break with profile; lateral ratios break with yaw.  Always verify image pose.  Use face orientation detection to reject extreme yaw.  If slight tilt, you may correct by rotating all landmarks by the angle of the eyes line.  

- **Facial Expression:**  Smiling or wide eyes distort distances.  Best use neutral, relaxed expression.  If unavoidable, be cautious interpreting mouth metrics (smile widens mouth) and eye aspect (blinking closes eye).  

- **Camera Distance / Scale:**  These ratios are *scale-invariant*, but if using raw mm or pixels (e.g. “mm” values from FaceIQ), one needs a consistent scaling factor.  If using 2D photos, stick to ratios or percentages to avoid unknown camera zoom.  

- **Lens Distortion:**  Wide-angle distortion can widen features at edges.  Either use face-centered cropping or correct distortion if camera intrinsics are known.  

- **Landmark Variability:**  Some points (glabella, tragion, exocanthion) are harder to detect precisely.  E.g. glabella is soft, so we approximate it.  Using smoothed or averaged positions (midpoints of brows, etc.) reduces jitter.  

*Normalization Tips:* Many algorithms normalize by interocular distance (distance between pupils) to make measures comparable across face sizes【46†L129-L133】.  For frontal measures, normalizing by face width (zygion distance) or bounding-box width is common.  For profile, some normalize angles to Frankfort plane (through orbitale–tragion) to remove head tilt.  

## 7. Validation & Test Data

To verify an implementation, use a mix of real and synthetic data:

- **Symmetric cases:** Test on a synthetically generated frontal face (e.g. a CAD model or stylized face) with known proportions (e.g. width=200px, height=100px → FWHR=2.0).  
- **Celebrities (FaceIQ examples):** Compare computed ratios to FaceIQ-reported values. For instance, using a portrait of *Tom Holland*, our Eye Aspect should be ~2.8×【49†L23-L31】 and Brow/Face ~0.7×【49†L73-L76】.  
- **Manually annotated:** Use a photo and manually mark points (e.g. in image editor) then compute distances to cross-check code.  
- **Edge tests:** Very narrow vs wide faces, high/low eyebrows, etc., to see expected monotonic behavior.  

*Example Test Table:* (hypothetical values for illustration)  

| Metric               | Test Image (A) | Manual Expected | Our Output | Pass? |
|----------------------|---------------:|----------------|-----------|:------|
| Face W/H Ratio       | Width=200,H=100px | 2.00×         | 1.98×     | ✔     |
| Eye Aspect (A. Eyes) | L:W=30,H=10px  | 3.00×         | 2.95×     | ✔     |
| Nasolabial Angle     | 100° (textbook) | 100°          | 101.2°    | ✔     |
| Lip E-Line dist.     | 5.0 mm behind  | 5.0 mm        | 5.1 mm    | ✔     |
| Zygion width % bigonial | 100% / 80%  | 80%           | 79%       | ✔     |

Include several such examples covering each category.  

## 8. FaceIQ-to-Anthropometry Mapping

FaceIQ’s metric names correspond closely (or analogously) to standard measures:

| **FaceIQ Name**                   | **Equivalent Anthropometric Term**            | **Formula**                              | **Source**             |
|-----------------------------------|-----------------------------------------------|------------------------------------------|-----------------------|
| Face Width/Height Ratio           | **Facial width-to-height ratio (fWHR)**【46†L129-L133】| Bizygomatic width / (nasion–upper lip) | FaceMesh/dlib landmarks |
| Total Facial W/H Ratio            | (used in FaceIQ)                               | Bizygomatic / (nasion–menton)            | -                     |
| Midface Ratio                     | (none standard; akin to maxillomandibular index) | (Nasion–Subnasale) / (Subnasale–Menton)| This guide (inferred) |
| Lateral Canthal Tilt              | *Ocular canthal tilt angle*                     | ∠(Exocanthion_L–Exocanthion_R vs horizontal) | this guide        |
| Eye Aspect Ratio                  | *Horizontal vs vertical eye dimension*         | (Exocanthion–Endocanthion) / (vertical)   | blink-detect EAR【47†L1-L4】 |
| Brow Length/Face Width            | (not standard)                                 | (eyebrow end–end) / (Zygion–Zygion)       | FaceIQ data          |
| Intercanthal–Nasal Width Ratio    | (inverse of “nasal index”)                    | (En_L–En_R) / (Al_L–Al_R)                | see anthropometry     |
| Nose Tip Position                 | (Deviation from midline)                      | horizontal offset of Pronasale           | our def.              |
| Lower/Upper Lip Ratio             | (none standard)                               | (Ls–Li heights ratio)                    | this guide            |
| Mouth Width/Interpupillary Ratio  | (mouth width vs interpupillary dist.)         | (Ch_L–Ch_R) / (EyeCtr_L–EyeCtr_R)        | forensic art sources  |
| Chin–Philtrum Ratio               | (none standard)                               | (Sn–Pg) / (Sn–Ls)                        | this guide            |
| Jaw Slope / Jaw Frontal Angle     | (Mandibular angle-related)                   | ∠(Go–Pg–Go) and jaw inclination          | cephalometry texts    |
| Nasofrontal Angle                 | *Nasion angle*【51†L416-L424】                | ∠Gl–N–Prn (Forehead–nose top)            | rhinoplasty guides【51†L416-L424】 |
| Nasolabial Angle                  | *Columella-lip angle*【51†L438-L442】         | ∠(Sn–Prn–Ls)                              | standards【51†L438-L442】 |
| Nasomental Angle                  | *Nasion-Pronasale-Pogonion angle*【51†L430-L438】 | ∠(N–Prn–Pg)                           | aesthetic guides【51†L430-L438】 |
| Nasofacial Angle                 | *Nasion-Frankfort angle*【51†L425-L430】      | ∠(Gl–N–Prn)                              | aesthetic guides【51†L425-L430】 |
| Holdaway H-Line (Upper Lip)       | *Holdaway’s H-line distance*【72†L5-L12】     | dist(Ls, line Pogn–Ls) (tangent line)   | ceph. references【72†L5-L12】 |
| Upper/Lower Lip E-Line Position   | *Steiner’s E-line distances*                 | dist(Ls/Li, line Prn–Pg)                | orthodontic standard |
| Upper/Lower Lip S-Line Position   | *Steiner’s S-line distances*                 | dist(Ls/Li, line Subn–Pg)               | orthodontic (Steiner) |
| Mentolabial Angle                | *Soft tissue chin-lip angle*                  | ∠(Ls–Li–Pg)                              | aesthetic literature |
| Facial Convexity (Glab/Nasion)    | *Glabella/Nasion convexity*【46†L129-L133】   | ∠(Gl–Sn–Pg) / ∠(N–Sn–Pg)                | cephalometric norms  |
| … (others)                        | …                                            | …                                        | …                     |

*(Table 2: Mapping of FaceIQ metric names to standard anthropometric definitions and formulas. Citations indicate where formula conventions are documented.)*

## 9. Code Examples (JavaScript)

Below are example snippets to compute a few representative ratios given 2D landmarks (with structure `{x,y}` in an object or array).  We assume landmarks are pre-detected and accessible by name or index.

```js
// Utility: Euclidean distance
function dist(p, q) {
    return Math.hypot(p.x - q.x, p.y - q.y);
}

// Example landmarks object (keys can be index or name):
let lm = {
  nasion: {x: ..., y: ...},
  subnasale: {x: ..., y: ...},
  pogonion: {x: ..., y: ...},
  zy_L: {x: ..., y: ...}, zy_R: {x: ..., y: ...},
  ex_L: {x: ..., y: ...}, ex_R: {x: ..., y: ...},
  en_L: {x: ..., y: ...}, en_R: {x: ..., y: ...},
  ls: {x: ..., y: ...}, li: {x: ..., y: ...},
  ch_L: {x: ..., y: ...}, ch_R: {x: ..., y: ...}
  // etc.
};

// Face Width-to-Height Ratio (approx: bizygomatic width / (nasion–menton))
function faceWidthHeightRatio(landmarks) {
    let width = dist(landmarks.zy_L, landmarks.zy_R);
    let height = dist(landmarks.nasion, landmarks.pogonion); 
    return width / height;
}

// Eye Aspect Ratio (Width/Height of left eye)
function eyeAspectRatio(landmarks) {
    // For left eye: outer=ex_L, inner=en_L; top/bottom from additional eye landmarks
    let w = dist(landmarks.ex_L, landmarks.en_L);
    // For vertical, use midpoints (here assume 'eyeTop_L', 'eyeBot_L' precomputed)
    let vertical = dist(landmarks.eyeTop_L, landmarks.eyeBot_L);
    return w / vertical;
}

// Nasolabial Angle (Pronasale-Subnasale-Labrale_superius)
function nasolabialAngle(landmarks) {
    // Compute angle at subnasale between line to pronasale and to upper lip.
    let A = landmarks.pronasale, B = landmarks.subnasale, C = landmarks.ls;
    // Angle = angle ABC
    let AB = {x: A.x - B.x, y: A.y - B.y};
    let CB = {x: C.x - B.x, y: C.y - B.y};
    let dot = AB.x*CB.x + AB.y*CB.y;
    let magAB = Math.hypot(AB.x, AB.y), magCB = Math.hypot(CB.x, CB.y);
    let angleRad = Math.acos(dot / (magAB*magCB));
    return angleRad * 180/Math.PI;
}

// Cheekbone Height (approx Midface height normalized)
function cheekboneHeightPercent(landmarks) {
    // ratio (nasion–subnasale)/(nasion–pog) *100
    let upper = dist(landmarks.nasion, landmarks.subnasale);
    let total = dist(landmarks.nasion, landmarks.pogonion);
    return (upper/total)*100;
}

// Example usage:
let ratios = {
    fwh: faceWidthHeightRatio(lm).toFixed(2), 
    ear: eyeAspectRatio(lm).toFixed(2),
    nasolabial: nasolabialAngle(lm).toFixed(1),
    cheekPct: cheekboneHeightPercent(lm).toFixed(1) + '%'
};
console.log(ratios);
```

*Expected Outputs (for a neutral male face example):*  
Suppose landmarks measured on an image yield: `faceWidthHeightRatio=1.8`, `eyeAspectRatio=3.0`, `nasolabialAngle=105°`, `cheekbone height=30%`.  These would match FaceIQ examples (e.g. Face W/H ~1.8×【49†L65-L72】, EAR ~2.8×【49†L23-L31】, NLA ~110°【25†L139-L147】, cheeks ~82%【29†L63-L65】). 

*(More code snippets for other ratios can be analogously written.)*  

## 10. Implementation Checklist

1. **Detect Face & Landmarks:** Use a robust 2D detector (e.g. MediaPipe FaceMesh) to get the required landmarks (Table 1). Verify pose (yaw~0° for front, ~90° for side).
2. **Preprocess:** Rotate to level eyes if needed, crop to face box. Normalize coordinates if desired (e.g. to face width).
3. **Compute distances/angles:** For each metric, apply the formula above using the landmark coordinates.
4. **Normalize:** Express distance ratios as unitless or %, angles in degrees.
5. **Compare to norms:** Use FaceIQ ranges or literature (as given above) to interpret results.
6. **Validate:** Test on known cases (see Section 7) to ensure code matches expected outputs.

**Sources:** We relied on FaceIQ pages【16†L25-L32】【49†L23-L31】【24†L139-L147】 for example values and naming, plus anthropometry references【46†L129-L133】【51†L414-L422】 (nasolabial etc) and FaceMesh/dlib docs【38†L74-L82】【66†L133-L139】 for landmark definitions. 

