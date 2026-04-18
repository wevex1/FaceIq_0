"""
FaceIQ Facial Ratio Analyzer — Full Implementation
Based on: research_Facial_Ratio.md (FaceIQ Labs comprehensive guide)
Implements ALL 70+ facial ratios described in the document.
"""

import math
import numpy as np
import mediapipe as mp
import cv2
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict


# ─── MediaPipe FaceMesh landmark indices ─────────────────────────────────────
MP_INDICES = {
    # Eyes (outer/inner corners)
    "ex_L": 33,    "ex_R": 263,
    "en_L": 133,   "en_R": 362,
    # Eyelids (top/bottom midpoints)
    "eye_top_L": 159, "eye_bot_L": 145,
    "eye_top_R": 386, "eye_bot_R": 374,
    # Iris centres (requires refine_landmarks=True)
    "pupil_L": 468, "pupil_R": 473,
    # Eyebrows
    "brow_out_L": 70,  "brow_in_L": 107, "brow_apex_L": 63,
    "brow_out_R": 300, "brow_in_R": 336, "brow_apex_R": 293,
    # Nose
    "nasion": 168,      # bridge
    "pronasale": 1,     # tip
    "subnasale": 2,     # base of nose/above upper lip
    "al_L": 218,        # left alare
    "al_R": 438,        # right alare
    # Lips / Mouth
    "ls": 13,   "li": 14,
    "ch_L": 61, "ch_R": 291,
    # Upper/lower lip additional points
    "upper_lip_top": 0,
    "lower_lip_bot": 17,
    # Jaw / Chin
    "pogonion": 152,
    "go_L": 172, "go_R": 397,
    # Cheekbones
    "zy_L": 234, "zy_R": 454,
    # Forehead
    "glabella": 9,
    "trichion": 10,
    # Temples
    "temp_L": 162, "temp_R": 389,
    # Philtrum
    "philtrum_top": 164,
    # Neck approximation (below chin)
    "neck_L": 207, "neck_R": 427,
    # Mid-cheek (for ear protrusion reference)
    "cheek_L": 116, "cheek_R": 345,
    # Additional jaw points
    "jaw_L": 58,  "jaw_R": 288,
    # Nose bridge mid-point
    "nose_bridge": 6,
    # Columella
    "columella_L": 129, "columella_R": 358,
}


@dataclass
class RatioResult:
    name: str
    value: float
    ideal_min: Optional[float]
    ideal_max: Optional[float]
    unit: str
    score: float
    interpretation: str
    category: str


@dataclass
class AnalysisOutput:
    success: bool
    error: Optional[str] = None
    image_type: str = ""
    ratios: List[RatioResult] = field(default_factory=list)
    landmark_count: int = 0


# ─── Maths utilities ──────────────────────────────────────────────────────────

def dist(p1, p2) -> float:
    if p1 is None or p2 is None:
        return 0.0
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def angle_at_vertex(A, B, C) -> float:
    """Angle in degrees at vertex B in triangle A-B-C."""
    if A is None or B is None or C is None:
        return 0.0
    BA = (A[0] - B[0], A[1] - B[1])
    BC = (C[0] - B[0], C[1] - B[1])
    dot = BA[0]*BC[0] + BA[1]*BC[1]
    mag = math.hypot(*BA) * math.hypot(*BC)
    if mag == 0:
        return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, dot / mag))))


def signed_dist_to_line(point, line_start, line_end) -> float:
    """Signed perpendicular distance from point to line."""
    if point is None or line_start is None or line_end is None:
        return 0.0
    dx = line_end[0] - line_start[0]
    dy = line_end[1] - line_start[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return 0.0
    return (dy*(point[0]-line_start[0]) - dx*(point[1]-line_start[1])) / length


def line_angle_to_horizontal(p1, p2) -> float:
    """Angle of line p1→p2 relative to horizontal, in degrees."""
    if p1 is None or p2 is None:
        return 0.0
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.degrees(math.atan2(-dy, dx))   # flip y (image coords)


def midpoint(p1, p2):
    if p1 is None or p2 is None:
        return None
    return ((p1[0]+p2[0])/2, (p1[1]+p2[1])/2)


def score_from_range(value: float, ideal_min: float, ideal_max: float,
                     tolerance: float = 0.3) -> float:
    if ideal_min is None or ideal_max is None:
        return 5.0
    mid = (ideal_min + ideal_max) / 2.0
    half = (ideal_max - ideal_min) / 2.0
    if half == 0:
        return 10.0 if abs(value - mid) < 1e-9 else 5.0
    if ideal_min <= value <= ideal_max:
        deviation = abs(value - mid) / half
        return 10.0 - 2.0 * deviation
    outer = min(abs(value - ideal_min), abs(value - ideal_max))
    max_outer = tolerance * (ideal_max - ideal_min)
    penalty = min(1.0, outer / max(max_outer, 1e-9))
    return max(0.0, 8.0 - 8.0 * penalty)


# ─── Landmark extraction ──────────────────────────────────────────────────────

def extract_landmarks(image_bgr: np.ndarray,
                      refine: bool = True) -> Optional[Dict]:
    mp_face_landmarker = mp.tasks.vision.FaceLandmarker
    h, w = image_bgr.shape[:2]
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    options = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(
            model_asset_path="../../models/face_landmarker.task"
        ),
        num_faces=1,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
    )

    with mp_face_landmarker.create_from_options(options) as fm:
        res = fm.detect(mp_image)

    if not res.face_landmarks:
        return None

    raw = res.face_landmarks[0]

    def px(idx: int) -> Tuple[float, float]:
        lm = raw[idx]
        return (lm.x * w, lm.y * h)

    named: Dict[str, Tuple[float, float]] = {}
    for name, idx in MP_INDICES.items():
        try:
            named[name] = px(idx)
        except IndexError:
            pass

    return named


# ─── FRONTAL RATIOS (40+ metrics) ────────────────────────────────────────────

def compute_frontal_ratios(lm: Dict) -> List[RatioResult]:
    results: List[RatioResult] = []

    def add(name, val, imin, imax, unit, interp, cat):
        if val is None or not math.isfinite(val):
            return
        s = score_from_range(val, imin, imax)
        results.append(RatioResult(
            name=name, value=round(val, 3),
            ideal_min=imin, ideal_max=imax,
            unit=unit, score=round(s, 1),
            interpretation=interp, category=cat,
        ))

    def p(k): return lm.get(k)

    nasion    = p("nasion")
    pogonion  = p("pogonion")
    subnasale = p("subnasale")
    glabella  = p("glabella")
    zy_l      = p("zy_L"); zy_r = p("zy_R")
    en_l      = p("en_L"); en_r = p("en_R")
    ex_l      = p("ex_L"); ex_r = p("ex_R")
    ls        = p("ls");   li   = p("li")
    ch_l      = p("ch_L"); ch_r = p("ch_R")
    al_l      = p("al_L"); al_r = p("al_R")
    go_l      = p("go_L"); go_r = p("go_R")
    brow_ol   = p("brow_out_L"); brow_il = p("brow_in_L")
    brow_or   = p("brow_out_R"); brow_ir = p("brow_in_R")
    brow_al   = p("brow_apex_L"); brow_ar = p("brow_apex_R")
    eye_top_l = p("eye_top_L"); eye_bot_l = p("eye_bot_L")
    eye_top_r = p("eye_top_R"); eye_bot_r = p("eye_bot_R")
    pronasale = p("pronasale")
    pupil_l   = p("pupil_L"); pupil_r = p("pupil_R")
    temp_l    = p("temp_L"); temp_r = p("temp_R")
    neck_l    = p("neck_L"); neck_r = p("neck_R")
    cheek_l   = p("cheek_L"); cheek_r = p("cheek_R")
    trichion  = p("trichion")
    philtrum  = p("philtrum_top")
    ul_top    = p("upper_lip_top")
    ll_bot    = p("lower_lip_bot")

    face_h = dist(nasion, pogonion)
    face_w = dist(zy_l, zy_r)

    # ═══════════════════════════════════════════════════════════════════════════
    # 1. FACIAL THIRDS
    # ═══════════════════════════════════════════════════════════════════════════
    cat = "Facial Thirds"
    if glabella and nasion and subnasale and pogonion:
        gl_me = dist(glabella, pogonion)
        if gl_me > 0:
            top = dist(glabella, nasion) / gl_me * 100
            mid = dist(nasion, subnasale) / gl_me * 100
            low = dist(subnasale, pogonion) / gl_me * 100
            add("Upper Third", top, 28, 38, "%",
                "Forehead height as % of total face height. ~33% is the classical ideal.", cat)
            add("Middle Third", mid, 28, 36, "%",
                "Midface height (nasion to subnasale) as % of total face. ~33% ideal.", cat)
            add("Lower Third", low, 30, 38, "%",
                "Lower face height (subnasale to chin) as % of total. ~33% ideal.", cat)
            # Upper:Lower ratio
            if low > 0:
                add("Upper-to-Lower Third Ratio", top / low, 0.85, 1.15, "×",
                    "Balance between forehead and lower face. 1.0 = perfect symmetry.", cat)
            # Mid:Lower ratio
            if low > 0:
                add("Mid-to-Lower Third Ratio", mid / low, 0.80, 1.10, "×",
                    "Midface to lower face balance. 1.0 = harmonious proportion.", cat)

    # ═══════════════════════════════════════════════════════════════════════════
    # 2. FACE SHAPE & WIDTH/HEIGHT RATIOS
    # ═══════════════════════════════════════════════════════════════════════════
    cat = "Face Shape"
    if face_w > 0 and ls and nasion:
        upper_h = dist(nasion, ls)
        if upper_h > 0:
            add("Face Width-to-Height Ratio (FWHR)", face_w / upper_h, 1.6, 2.0, "×",
                "Bizygomatic width / nasion-to-upper-lip. Higher = broader face.", cat)
    if face_w > 0 and face_h > 0:
        add("Total Facial Width/Height Ratio", face_w / face_h, 1.2, 1.5, "×",
            "Overall face width vs nasion-to-chin height. ~1.3× is balanced.", cat)
    if nasion and subnasale and pogonion:
        upper_m = dist(nasion, subnasale)
        lower_m = dist(subnasale, pogonion)
        if lower_m > 0:
            add("Midface Ratio", upper_m / lower_m, 0.85, 1.15, "×",
                "Nasion-subnasale vs subnasale-chin. 1.0 = balanced mid and lower face.", cat)
    if temp_l and temp_r and face_w > 0:
        add("Bitemporal Width", dist(temp_l, temp_r) / face_w * 100, 78, 92, "%",
            "Temple width as % of bizygomatic width.", cat)
    if go_l and go_r and face_w > 0:
        add("Bigonial Width", dist(go_l, go_r) / face_w * 100, 75, 90, "%",
            "Jaw angle width as % of cheekbone width. Lower = more tapered jaw.", cat)
    if face_w > 0 and face_h > 0:
        # Facial index (height / width × 100 — classic anthropology)
        add("Facial Index", face_h / face_w * 100, 75, 90, "%",
            "Face height / width × 100. 75–85 = mesoprosopic (average); >90 = leptoprosopic (narrow).", cat)

    # ═══════════════════════════════════════════════════════════════════════════
    # 3. EYES & BROWS
    # ═══════════════════════════════════════════════════════════════════════════
    cat = "Eyes & Brows"
    # Eye Aspect Ratio (average both eyes)
    if ex_l and en_l and eye_top_l and eye_bot_l and ex_r and en_r and eye_top_r and eye_bot_r:
        w_l = dist(ex_l, en_l); h_l = dist(eye_top_l, eye_bot_l)
        w_r = dist(ex_r, en_r); h_r = dist(eye_top_r, eye_bot_r)
        if h_l > 0 and h_r > 0:
            ear = (w_l / h_l + w_r / h_r) / 2
            add("Eye Aspect Ratio", ear, 2.8, 3.5, "×",
                "Eye width / height. 2.8–3.5 = almond-shaped. Lower = rounder eyes.", cat)
        # Left/Right symmetry
        if h_l > 0 and h_r > 0:
            sym = min(w_l/h_l, w_r/h_r) / max(w_l/h_l, w_r/h_r) * 100
            add("Eye Symmetry", sym, 90, 100, "%",
                "Left vs right eye aspect ratio similarity. 100% = perfectly symmetric eyes.", cat)

    # Eye Separation Ratio
    if en_l and en_r and face_w > 0:
        add("Eye Separation Ratio", dist(en_l, en_r) / face_w * 100, 38, 50, "%",
            "Inner eye span as % of face width. ~44% is the classical ideal.", cat)

    # One-Eye-Apart Test
    if ex_l and en_l and ex_r and en_r:
        c_l = pupil_l if pupil_l else midpoint(ex_l, en_l)
        c_r = pupil_r if pupil_r else midpoint(ex_r, en_r)
        ipd = dist(c_l, c_r)
        eye_w_l = dist(ex_l, en_l)
        if eye_w_l > 0:
            add("One-Eye-Apart Test", ipd / eye_w_l, 0.9, 1.2, "×",
                "Interpupillary distance / one eye width. ~1.0 = classical 'one eye apart' rule.", cat)

    # Lateral Canthal Tilt
    if ex_l and ex_r:
        add("Lateral Canthal Tilt", line_angle_to_horizontal(ex_l, ex_r), -5, 5, "°",
            "Eye axis angle. Positive = upward cant (hunter eyes). Ideal near 0°.", cat)

    # Brow Tilt
    if brow_ol and brow_or:
        add("Eyebrow Tilt", abs(line_angle_to_horizontal(brow_ol, brow_or)), 5, 20, "°",
            "Eyebrow inclination. Mild upward arch (5–20°) is considered attractive.", cat)

    # Brow Length / Face Width
    if brow_ol and brow_il and face_w > 0:
        blen = (dist(brow_ol, brow_il) + (dist(brow_or, brow_ir) if brow_or and brow_ir else dist(brow_ol, brow_il))) / 2
        add("Brow Length / Face Width", blen / face_w, 0.65, 0.80, "×",
            "Eyebrow length as ratio of face width. 0.70–0.80 is ideal; lower = short brows.", cat)

    # Brow Height (distance from brow apex to eye)
    if brow_al and ex_l and en_l and eye_top_l:
        eye_ctr_l = midpoint(ex_l, en_l)
        brow_eye_dist = dist(brow_al, eye_top_l)
        eye_h = dist(eye_top_l, eye_bot_l) if eye_bot_l else 1
        if eye_h > 0:
            add("Eyebrow Height (L)", brow_eye_dist / eye_h, 0.5, 1.5, "×",
                "Distance from brow apex to upper eyelid, normalised by eye height. Lower = closer brows.", cat)

    # Brow Arch (inner-to-apex rise)
    if brow_il and brow_al:
        arch = abs(brow_il[1] - brow_al[1])
        brow_len_l = dist(brow_il, brow_ol) if brow_ol else dist(brow_il, brow_al) * 2
        if brow_len_l > 0:
            add("Brow Arch Height Ratio", arch / brow_len_l, 0.1, 0.3, "×",
                "Vertical rise of brow arch / brow length. Higher = more peaked, dramatic arch.", cat)

    # Intercanthal width / eye width ratio (Golden ratio check)
    if en_l and en_r and ex_l and en_l:
        ic = dist(en_l, en_r)
        ew = dist(ex_l, en_l)
        if ew > 0:
            add("Intercanthal / Eye Width", ic / ew, 0.9, 1.1, "×",
                "Inner eye span vs one eye width. ~1.0 aligns with the 'one eye apart' golden rule.", cat)

    # ═══════════════════════════════════════════════════════════════════════════
    # 4. NOSE (FRONTAL)
    # ═══════════════════════════════════════════════════════════════════════════
    cat = "Nose (Frontal)"
    # Intercanthal / Nasal Width
    if en_l and en_r and al_l and al_r:
        add("Intercanthal / Nasal Width Ratio", dist(en_l, en_r) / dist(al_l, al_r), 0.85, 1.15, "×",
            "Inner eye span vs alar width. ~1.0 = nose as wide as eye spacing (ideal harmony).", cat)

    # Nose Bridge / Width Ratio
    if nasion and pronasale and al_l and al_r:
        nw = dist(al_l, al_r)
        if nw > 0:
            add("Nose Bridge / Width Ratio", dist(nasion, pronasale) / nw, 2.2, 3.2, "×",
                "Nose height vs width. Higher = narrow prominent nose; lower = wide flat nose.", cat)

    # Nasal Width % of Face Width
    if al_l and al_r and face_w > 0:
        add("Nasal Width / Face Width", dist(al_l, al_r) / face_w * 100, 22, 28, "%",
            "Nose width as % of face width. Classical ideal ~25%.", cat)

    # Nose Tip Deviation (from midline)
    if pronasale and nasion and pogonion and face_w > 0:
        dev = abs(signed_dist_to_line(pronasale, nasion, pogonion))
        add("Nose Tip Deviation", dev / face_w * 100, 0, 2, "%",
            "Lateral offset of nose tip from face midline. Ideal = 0 (centred).", cat)

    # Ipsilateral Alar Angle (IAA) — angle at subnasale
    if al_l and subnasale and pronasale:
        iaa_l = angle_at_vertex(al_l, subnasale, pronasale)
        add("Ipsilateral Alar Angle (Left)", iaa_l, 80, 100, "°",
            "Angle at subnasale between left ala and nose tip. ~90° = well-defined nostril.", cat)
    if al_r and subnasale and pronasale:
        iaa_r = angle_at_vertex(al_r, subnasale, pronasale)
        add("Ipsilateral Alar Angle (Right)", iaa_r, 80, 100, "°",
            "Angle at subnasale between right ala and nose tip. ~90° = well-defined nostril.", cat)

    # IAA left-right symmetry
    if al_l and al_r and subnasale and pronasale:
        iaa_l = angle_at_vertex(al_l, subnasale, pronasale)
        iaa_r = angle_at_vertex(al_r, subnasale, pronasale)
        dev_iaa = abs(iaa_l - iaa_r)
        add("IAA Left-Right Deviation", dev_iaa, 0, 5, "°",
            "Asymmetry between left and right alar angles. Lower = more symmetric nose.", cat)

    # Jaw Frontal Angle
    if go_l and pogonion and go_r:
        add("Jaw Frontal Angle", angle_at_vertex(go_l, pogonion, go_r), 80, 100, "°",
            "Angle at chin between jaw lines. ~90° = well-defined square chin.", cat)

    # Nose Height / Face Height
    if nasion and subnasale and face_h > 0:
        add("Nose Height / Face Height", dist(nasion, subnasale) / face_h * 100, 28, 35, "%",
            "Vertical nose span as % of face height. ~33% aligns with the middle facial third.", cat)

    # ═══════════════════════════════════════════════════════════════════════════
    # 5. MOUTH & LIPS (FRONTAL)
    # ═══════════════════════════════════════════════════════════════════════════
    cat = "Mouth & Lips"
    # Lower / Upper Lip Ratio
    if subnasale and ls and li:
        upper_h = dist(subnasale, ls)
        lower_h = dist(ls, li)
        if upper_h > 0:
            add("Lower / Upper Lip Ratio", lower_h / upper_h, 1.0, 1.4, "×",
                "Lower lip height vs upper lip height. ~1.2× = fuller lower lip (classical ideal).", cat)

    # Mouth Width / IPD
    if ch_l and ch_r:
        mw = dist(ch_l, ch_r)
        c_l = pupil_l if pupil_l else (midpoint(ex_l, en_l) if ex_l and en_l else None)
        c_r = pupil_r if pupil_r else (midpoint(ex_r, en_r) if ex_r and en_r else None)
        if c_l and c_r:
            ipd2 = dist(c_l, c_r)
            if ipd2 > 0:
                add("Mouth Width / Interpupillary Distance", mw / ipd2, 0.75, 0.90, "×",
                    "Mouth width vs eye spacing. ~0.8× is the classical proportion.", cat)

    # Mouth Width / Nose Width
    if ch_l and ch_r and al_l and al_r:
        nw = dist(al_l, al_r)
        if nw > 0:
            add("Mouth Width / Nose Width", dist(ch_l, ch_r) / nw, 1.3, 1.6, "×",
                "Mouth width vs nose width. ~1.4× is proportionate.", cat)

    # Mouth Width / Face Width
    if ch_l and ch_r and face_w > 0:
        add("Mouth Width / Face Width", dist(ch_l, ch_r) / face_w * 100, 40, 50, "%",
            "Mouth width as % of face width. ~45% is balanced.", cat)

    # Chin / Philtrum Ratio
    if subnasale and pogonion and ls:
        phil = dist(subnasale, ls)
        if phil > 0:
            add("Chin / Philtrum Ratio", dist(subnasale, pogonion) / phil, 1.7, 2.3, "×",
                "Subnasale-chin vs philtrum. ~2.0× is harmonious lower face.", cat)

    # Philtrum Width (distance between columella base points)
    if subnasale and ls and face_w > 0:
        phil_h = dist(subnasale, ls)
        add("Philtrum Height / Face Height", phil_h / face_h * 100 if face_h > 0 else 0, 8, 14, "%",
            "Philtrum length as % of face height. Shorter = more youthful.", cat)

    # Mouth Corner Position (tilt relative to horizontal)
    if ch_l and ch_r:
        tilt = line_angle_to_horizontal(ch_l, ch_r)
        add("Mouth Corner Tilt", tilt, -3, 3, "°",
            "Horizontal alignment of mouth corners. Negative = downturned corners.", cat)

    # Vermilion Height (upper lip body)
    if ls and ul_top:
        uv_h = dist(ls, ul_top)
        if face_h > 0:
            add("Upper Vermilion Height / Face Height", uv_h / face_h * 100, 3, 7, "%",
                "Upper lip vermilion height as % of face. Higher = fuller upper lip.", cat)

    # Lower Lip / Chin Ratio
    if li and pogonion and ls:
        ll_h = dist(li, ls)
        chin_h = dist(li, pogonion)
        if chin_h > 0:
            add("Lower Lip / Chin Height Ratio", ll_h / chin_h, 0.4, 0.7, "×",
                "Lower lip vs chin height. Higher = prominent lower lip relative to chin.", cat)

    # ═══════════════════════════════════════════════════════════════════════════
    # 6. JAW & CHIN (FRONTAL)
    # ═══════════════════════════════════════════════════════════════════════════
    cat = "Jaw & Chin"
    # Lower Third Proportion
    if subnasale and pogonion and nasion and face_h > 0:
        add("Lower Third Proportion", dist(subnasale, pogonion) / face_h * 100, 30, 38, "%",
            "Lower face from subnasale to chin as % of total face. ~33% ideal.", cat)

    # Jaw Slope Angle
    if go_l and pogonion and go_r:
        dx_l = abs(pogonion[0] - go_l[0]); dy_l = abs(pogonion[1] - go_l[1])
        dx_r = abs(go_r[0] - pogonion[0]); dy_r = abs(go_r[1] - pogonion[1])
        ang_l = math.degrees(math.atan2(dy_l, dx_l)) if dx_l > 0 else 90
        ang_r = math.degrees(math.atan2(dy_r, dx_r)) if dx_r > 0 else 90
        add("Jaw Slope Angle", (ang_l + ang_r) / 2, 20, 40, "°",
            "Inclination of jawline from horizontal. Higher = steeper, more angular jaw.", cat)

    # Chin Width / Face Width
    if go_l and go_r and face_w > 0:
        add("Bigonial / Bizygomatic Ratio", dist(go_l, go_r) / face_w, 0.75, 0.90, "×",
            "Jaw width / cheekbone width. Lower ratio = more tapered (feminine) jaw.", cat)

    # Face Taper (zygion width vs gonion width difference)
    if zy_l and zy_r and go_l and go_r:
        taper = (dist(zy_l, zy_r) - dist(go_l, go_r))
        face_w_ref = dist(zy_l, zy_r)
        if face_w_ref > 0:
            add("Face Taper Index", taper / face_w_ref * 100, 8, 20, "%",
                "Cheekbone vs jaw width difference as % of face width. Higher = more V-shaped face.", cat)

    # Neck Width
    if neck_l and neck_r and face_w > 0:
        add("Neck Width / Face Width", dist(neck_l, neck_r) / face_w * 100, 55, 75, "%",
            "Neck width as % of face width. Lower = slender neck relative to face.", cat)

    # Chin Height / Lower Third
    if li and pogonion and subnasale:
        chin_h = dist(li, pogonion)
        lower3 = dist(subnasale, pogonion)
        if lower3 > 0:
            add("Chin Height / Lower Third", chin_h / lower3 * 100, 40, 55, "%",
                "Chin height (below lower lip) as % of lower third. Ideal chin is ~50% of lower third.", cat)

    # Gonion height (jaw angle height relative to face)
    if go_l and go_r and nasion and pogonion and face_h > 0:
        go_mid_y = (go_l[1] + go_r[1]) / 2
        pog_y = pogonion[1]
        nas_y = nasion[1]
        go_from_top = (go_mid_y - nas_y) / face_h * 100
        add("Gonion Position (% from nasion)", go_from_top, 70, 85, "%",
            "Jaw angle vertical position as % down from nasion. Lower % = higher jaw angles.", cat)

    return results


# ─── PROFILE RATIOS (30+ metrics) ────────────────────────────────────────────

def compute_profile_ratios(lm: Dict) -> List[RatioResult]:
    results: List[RatioResult] = []

    def add(name, val, imin, imax, unit, interp, cat):
        if val is None or not math.isfinite(val):
            return
        s = score_from_range(val, imin, imax)
        results.append(RatioResult(
            name=name, value=round(val, 3),
            ideal_min=imin, ideal_max=imax,
            unit=unit, score=round(s, 1),
            interpretation=interp, category=cat,
        ))

    def p(k): return lm.get(k)

    nasion    = p("nasion")
    glabella  = p("glabella")
    subnasale = p("subnasale")
    pronasale = p("pronasale")
    ls        = p("ls");  li = p("li")
    pogonion  = p("pogonion")
    go_l      = p("go_L"); go_r = p("go_R")
    ex_l      = p("ex_L"); ex_r = p("ex_R")
    trichion  = p("trichion")
    temp_l    = p("temp_L")
    zy_l      = p("zy_L")
    brow_al   = p("brow_apex_L")
    al_l      = p("al_L")
    ch_l      = p("ch_L")
    ll_bot    = p("lower_lip_bot")

    face_h = dist(nasion, pogonion)

    # ═══════════════════════════════════════════════════════════════════════════
    # 1. UPPER FACE / FOREHEAD (PROFILE)
    # ═══════════════════════════════════════════════════════════════════════════
    cat = "Upper Face (Profile)"
    # Upper Forehead Slope
    if glabella and trichion:
        slope = abs(line_angle_to_horizontal(glabella, trichion))
        # Convert to angle from vertical
        vert_angle = abs(90 - slope)
        add("Upper Forehead Slope", vert_angle, 0, 10, "°",
            "Tilt of forehead from vertical. ~0° = perfectly upright forehead.", cat)

    # Browridge Inclination
    if glabella and brow_al:
        brow_inc = abs(line_angle_to_horizontal(glabella, brow_al))
        add("Browridge Inclination", brow_inc, 8, 20, "°",
            "Angle of browridge slope. Higher = more pronounced brow ridge prominence.", cat)

    # Nasofrontal Angle (glabella-nasion-pronasale)
    if glabella and nasion and pronasale:
        add("Nasofrontal Angle", angle_at_vertex(glabella, nasion, pronasale), 115, 135, "°",
            "Forehead-nose junction angle. ~125° = smooth balanced transition. <115° = deep set nasion.", cat)

    # Forehead Height / Face Height
    if glabella and nasion and face_h > 0:
        fh_h = dist(glabella, nasion)
        add("Forehead Height / Face Height", fh_h / face_h * 100, 28, 38, "%",
            "Forehead segment as % of total face. ~33% is the ideal upper third.", cat)

    # ═══════════════════════════════════════════════════════════════════════════
    # 2. FACIAL CONVEXITY / PROJECTION
    # ═══════════════════════════════════════════════════════════════════════════
    cat = "Facial Convexity"
    if glabella and subnasale and pogonion:
        add("Facial Convexity (Glabella)", angle_at_vertex(glabella, subnasale, pogonion), 160, 175, "°",
            "Profile angle at subnasale. ~180° = flat profile; lower = more convex/protruding face.", cat)

    if nasion and subnasale and pogonion:
        add("Facial Convexity (Nasion)", angle_at_vertex(nasion, subnasale, pogonion), 155, 175, "°",
            "Profile convexity from nasion. Lower = more convex face profile.", cat)

    if glabella and pronasale and pogonion:
        add("Total Facial Convexity", angle_at_vertex(glabella, pronasale, pogonion), 130, 155, "°",
            "Overall profile curvature. ~145° is harmonious balance between brow, nose and chin.", cat)

    # Anterior Facial Depth (horizontal projection)
    if nasion and pogonion and face_h > 0:
        horiz = abs(nasion[0] - pogonion[0])
        add("Anterior Facial Depth Ratio", horiz / face_h, 0.15, 0.35, "×",
            "Horizontal projection of chin relative to nasion, normalised by face height.", cat)

    # Facial Depth / Height (profile projection vs height)
    if glabella and pogonion and nasion and face_h > 0:
        depth = dist(glabella, pogonion)
        add("Facial Depth / Height Ratio", depth / face_h, 1.1, 1.4, "×",
            "Diagonal face depth vs face height. ~1.3× indicates well-projected profile.", cat)

    # Z Angle (angle between Frankfort plane approx and chin-to-nose line)
    if ex_l and pogonion and pronasale:
        z_ang = angle_at_vertex(ex_l, pogonion, pronasale)
        add("Z Angle", z_ang, 70, 85, "°",
            "Ricketts' Z-angle. ~80° is the aesthetic ideal. Lower = retruded chin.", cat)

    # Interior Midface Projection (nasion-pronasale angle from vertical)
    if nasion and pronasale:
        dx = pronasale[0] - nasion[0]
        dy = abs(pronasale[1] - nasion[1])
        if dy > 0:
            impa = math.degrees(math.atan2(abs(dx), dy))
            add("Interior Midface Projection Angle", impa, 15, 35, "°",
                "Nose projection angle from vertical. Higher = more protruding nose in profile.", cat)

    # ═══════════════════════════════════════════════════════════════════════════
    # 3. NOSE (PROFILE)
    # ═══════════════════════════════════════════════════════════════════════════
    cat = "Nose (Profile)"
    # Nasolabial Angle
    if pronasale and subnasale and ls:
        add("Nasolabial Angle", angle_at_vertex(pronasale, subnasale, ls), 95, 115, "°",
            "Columella-lip angle. ~105° feminine ideal; ~95° masculine ideal.", cat)

    # Nasomental Angle
    if nasion and pronasale and pogonion:
        add("Nasomental Angle", angle_at_vertex(nasion, pronasale, pogonion), 120, 132, "°",
            "Nose-to-chin angle. ~128° is the classic aesthetic ideal.", cat)

    # Nasofacial Angle (nose projection from facial plane)
    if glabella and nasion and pronasale:
        nfa = angle_at_vertex(glabella, nasion, pronasale)
        proj = 180 - nfa
        add("Nasofacial Angle", proj, 28, 42, "°",
            "Nose projection from facial plane. 30–40° is classical rhinoplasty ideal.", cat)

    # Nasal Projection Ratio
    if nasion and pronasale and face_h > 0:
        add("Nasal Projection Ratio", dist(nasion, pronasale) / face_h, 0.55, 0.75, "×",
            "Nose length (bridge to tip) as fraction of face height. ~0.65× is proportionate.", cat)

    # Nose Tip Rotation Angle (from horizontal)
    if subnasale and pronasale:
        tip_ang = line_angle_to_horizontal(subnasale, pronasale)
        add("Nose Tip Rotation Angle", tip_ang, 15, 30, "°",
            "Upward rotation of nose tip. 15–30° is ideal. <15° = drooping; >30° = overly upturned.", cat)

    # Nasal Tip Angle (N-Prn-Sn)
    if nasion and pronasale and subnasale:
        add("Nasal Tip Angle", angle_at_vertex(nasion, pronasale, subnasale), 70, 100, "°",
            "Sharpness of nasal tip. Higher = more obtuse (bulbous) tip; lower = more refined tip.", cat)

    # Frankfort-Tip Angle (approx: horizontal vs nasion-to-tip)
    if ex_l and nasion and pronasale:
        ft_ang = angle_at_vertex(ex_l, nasion, pronasale)
        add("Frankfort-Tip Angle", ft_ang, 30, 45, "°",
            "Angle between eye level and nose bridge-to-tip line. ~35–40° is balanced.", cat)

    # Nasal Bridge Inclination (nasion to tip vs vertical)
    if nasion and pronasale:
        dx = abs(pronasale[0] - nasion[0])
        dy = abs(pronasale[1] - nasion[1])
        if dy > 0:
            bridge_inc = math.degrees(math.atan2(dx, dy))
            add("Nasal Bridge Inclination", bridge_inc, 20, 40, "°",
                "Angle of nose bridge from vertical. Higher = more curved/projected bridge.", cat)

    # ═══════════════════════════════════════════════════════════════════════════
    # 4. LIPS (PROFILE)
    # ═══════════════════════════════════════════════════════════════════════════
    cat = "Lips (Profile)"
    # E-Line (Pronasale → Pogonion)
    if pronasale and pogonion and ls and li and face_h > 0:
        e_upper = signed_dist_to_line(ls, pronasale, pogonion)
        e_lower = signed_dist_to_line(li, pronasale, pogonion)
        add("Upper Lip E-Line Position", e_upper / face_h * 100, -3, 3, "%",
            "Upper lip position relative to E-line. Negative = behind (retruded); positive = in front.", cat)
        add("Lower Lip E-Line Position", e_lower / face_h * 100, -5, 2, "%",
            "Lower lip position relative to E-line. Negative = behind; positive = protrusive.", cat)

    # S-Line (Subnasale → Pogonion)
    if subnasale and pogonion and ls and li and face_h > 0:
        s_upper = signed_dist_to_line(ls, subnasale, pogonion)
        s_lower = signed_dist_to_line(li, subnasale, pogonion)
        add("Upper Lip S-Line Position", s_upper / face_h * 100, -3, 3, "%",
            "Upper lip relative to Steiner's S-line. Negative = retruded.", cat)
        add("Lower Lip S-Line Position", s_lower / face_h * 100, -3, 3, "%",
            "Lower lip relative to Steiner's S-line.", cat)

    # Burstone Line (Subnasale → Pogonion, measuring lip to line)
    if subnasale and pogonion and ls and li and face_h > 0:
        b_upper = signed_dist_to_line(ls, subnasale, pogonion)
        b_lower = signed_dist_to_line(li, subnasale, pogonion)
        add("Upper Lip Burstone Position", b_upper / face_h * 100, -4, 0, "%",
            "Upper lip to Burstone line. Negative = retruded; ideal is slightly behind the line.", cat)
        add("Lower Lip Burstone Position", b_lower / face_h * 100, -4, 0, "%",
            "Lower lip to Burstone line. Both lips should be at or slightly behind.", cat)

    # Holdaway H-Line (tangent to upper lip and chin)
    if ls and pogonion and subnasale and face_h > 0:
        # H-line approximated as pogonion → upper lip
        h_dist = signed_dist_to_line(subnasale, ls, pogonion)
        add("Holdaway H-Line Position", h_dist / face_h * 100, -1, 1, "%",
            "Upper lip prominence relative to H-line (Holdaway). Near 0 = ideal lip-chin balance.", cat)

    # Mentolabial Angle
    if ls and li and pogonion:
        add("Mentolabial Angle", angle_at_vertex(ls, li, pogonion), 120, 150, "°",
            "Chin-lip sulcus angle. ~134° ideal. Lower = deep sulcus; higher = flat (weak chin).", cat)

    # Upper / Lower Lip Projection (each vs profile vertical)
    if ls and subnasale and nasion:
        u_proj = signed_dist_to_line(ls, nasion, pogonion) if pogonion else 0
        if face_h > 0:
            add("Upper Lip Projection", u_proj / face_h * 100, -2, 4, "%",
                "Upper lip forward projection relative to face plane. Positive = protrusive.", cat)

    # ═══════════════════════════════════════════════════════════════════════════
    # 5. JAW & CHIN (PROFILE)
    # ═══════════════════════════════════════════════════════════════════════════
    cat = "Jaw & Chin (Profile)"
    # Mandibular Plane Angle
    if go_l and pogonion:
        mpa = abs(line_angle_to_horizontal(go_l, pogonion))
        add("Mandibular Plane Angle", mpa, 10, 25, "°",
            "Jaw floor inclination from horizontal. Lower = more horizontal jaw (often more aesthetic).", cat)

    # Gonial Angle
    if nasion and go_l and pogonion:
        add("Gonial Angle", angle_at_vertex(nasion, go_l, pogonion), 100, 130, "°",
            "Jaw angle. ~115° is balanced. >130° = open bite / weak jaw profile.", cat)

    # Ramus / Mandible Ratio
    if go_l and pogonion and nasion:
        ramus = dist(nasion, go_l)
        mandible = dist(go_l, pogonion)
        if mandible > 0:
            add("Ramus / Mandible Ratio", ramus / mandible, 0.6, 0.9, "×",
                "Ramus height vs mandible body. ~0.75× is balanced jaw structure.", cat)

    # Chin Projection (horizontal offset of pogonion vs nasion)
    if nasion and pogonion and face_h > 0:
        horiz_offset = (pogonion[0] - nasion[0])
        add("Chin Projection vs Nasion", horiz_offset / face_h * 100, -5, 5, "%",
            "Horizontal chin offset from nasion vertical. Negative = recessed chin.", cat)

    # Chin Height / Lower Face
    if li and pogonion and subnasale and face_h > 0:
        chin_h = dist(li, pogonion)
        lower3 = dist(subnasale, pogonion)
        if lower3 > 0:
            add("Chin Height / Lower Third (Profile)", chin_h / lower3 * 100, 40, 55, "%",
                "Chin height (below lower lip) as % of lower face. ~50% = balanced chin.", cat)

    # Submental / Cervical Angle (angle under chin)
    if subnasale and pogonion and go_l:
        sub_ang = angle_at_vertex(subnasale, pogonion, go_l)
        add("Submental Angle", sub_ang, 100, 140, "°",
            "Chin-neck angle. ~120° ideal. Lower (<90°) = recessed chin; higher = double chin.", cat)

    # Gonion-to-Mouth Distance
    if go_l and ch_l and face_h > 0:
        gm_dist = dist(go_l, ch_l)
        add("Gonion-to-Mouth Distance", gm_dist / face_h * 100, 15, 30, "%",
            "Distance from jaw angle to mouth corner, normalised by face height.", cat)

    # Recession relative to Frankfort vertical (eye to pogonion)
    if ex_l and pogonion and face_h > 0:
        recess = (pogonion[0] - ex_l[0])
        add("Chin Recession vs Eye Vertical", recess / face_h * 100, -8, 2, "%",
            "Chin position relative to vertical dropped from outer eye. Negative = behind (recessed).", cat)

    return results


# ─── Main analysis entry point ────────────────────────────────────────────────

def analyze_image(image_bytes: bytes, image_type: str) -> AnalysisOutput:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return AnalysisOutput(success=False, error="Could not decode image.", image_type=image_type)

    landmarks = extract_landmarks(img, refine=True)
    if landmarks is None:
        return AnalysisOutput(success=False,
                              error="No face detected. Ensure the face is clearly visible and well-lit.",
                              image_type=image_type)

    if image_type == "frontal":
        ratios = compute_frontal_ratios(landmarks)
    else:
        ratios = compute_profile_ratios(landmarks)

    return AnalysisOutput(
        success=True,
        image_type=image_type,
        ratios=ratios,
        landmark_count=len(landmarks),
    )
