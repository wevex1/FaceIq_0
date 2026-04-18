from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Mapping

from .geometry import (
    Point,
    acute_angle_between_lines,
    angle_degrees,
    angle_from_vertical,
    horizontal_distance,
    midpoint,
    safe_divide,
    signed_distance_to_line,
    vertical_distance,
)
from .landmarks import ExtractedFace


GROUP_LABELS = {
    "facial_thirds": "Facial Thirds",
    "face_shape": "Face Shape",
    "eyes_and_brows": "Eyes and Brows",
    "nose_frontal": "Nose Metrics",
    "mouth_lips": "Mouth and Lips",
    "jaw_chin_frontal": "Jaw and Chin",
    "upper_face_profile": "Upper Face Profile",
    "profile_convexity": "Profile Convexity",
    "nose_profile": "Nose Profile",
    "lips_profile": "Lips Profile",
}


UNSUPPORTED_METRICS = [
    "eyebrow_low_setedness",
    "ipsilateral_alar_angle",
    "deviation_of_iaa_and_jfa",
    "cupid_bow_depth",
    "mouth_corner_position",
    "ear_protrusion_angle",
    "ear_protrusion_ratio",
    "neck_width_frontal",
    "orbital_vector",
    "z_angle",
    "facial_depth_to_height_ratio",
    "interior_midface_projection_angle",
    "anterior_facial_depth",
    "frankfort_tip_angle",
    "nasal_tip_angle",
    "holdaway_h_line_position",
    "recession_relative_to_frankfort_plane",
    "gonial_angle",
    "mandibular_plane_angle",
    "ramus_to_mandible_ratio",
    "gonion_to_mouth_line",
    "submental_angle",
]


@dataclass
class MetricResult:
    key: str
    label: str
    group: str
    view: str
    value: float
    unit: str
    formula: str
    ideal_min: float | None = None
    ideal_max: float | None = None
    interpretation: str = ""
    notes: list[str] = field(default_factory=list)
    status: str = "no_reference"

    def to_dict(self) -> dict:
        return asdict(self)


def _status_for(metric: MetricResult) -> str:
    if metric.ideal_min is None or metric.ideal_max is None:
        return "no_reference"
    if metric.value < metric.ideal_min:
        return "below_ideal"
    if metric.value > metric.ideal_max:
        return "above_ideal"
    return "within_ideal"


def _metric(
    *,
    key: str,
    label: str,
    group: str,
    view: str,
    value: float | None,
    unit: str,
    formula: str,
    ideal_min: float | None = None,
    ideal_max: float | None = None,
    interpretation: str = "",
    notes: Iterable[str] | None = None,
) -> MetricResult | None:
    if value is None:
        return None
    result = MetricResult(
        key=key,
        label=label,
        group=group,
        view=view,
        value=round(value, 3),
        unit=unit,
        formula=formula,
        ideal_min=ideal_min,
        ideal_max=ideal_max,
        interpretation=interpretation,
        notes=list(notes or []),
    )
    result.status = _status_for(result)
    return result


def _tilt_positive_when_outer_corner_is_higher(inner: Point, outer: Point) -> float:
    from math import atan2, degrees

    rise = inner.y - outer.y
    run = max(abs(inner.x - outer.x), 1e-6)
    return degrees(atan2(rise, run))


def _normalize_signed_distance(value: float | None, scale: float) -> float | None:
    if value is None or scale <= 1e-8:
        return None
    return (value / scale) * 100.0


def _direction_normalized_distance(point: Point, line_a: Point, line_b: Point, direction_sign: int, scale: float) -> float | None:
    raw = signed_distance_to_line(point, line_a, line_b)
    if raw is None:
        return None
    return _normalize_signed_distance(raw * direction_sign, scale)


def analyze_face_pair(front_face: ExtractedFace, side_face: ExtractedFace) -> dict:
    front_metrics = _front_metrics(front_face.points)
    side_metrics = _side_metrics(side_face.points)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_reference": "research_Facial_Ratio.md",
        "front": {
            "pose_score": front_face.pose_score,
            "warnings": front_face.warnings,
            "groups": _group_metrics(front_metrics),
            "supported_metric_count": len(front_metrics),
        },
        "side": {
            "pose_score": side_face.pose_score,
            "warnings": side_face.warnings,
            "groups": _group_metrics(side_metrics),
            "supported_metric_count": len(side_metrics),
        },
        "summary": {
            "supported_metric_count": len(front_metrics) + len(side_metrics),
            "unsupported_metrics": UNSUPPORTED_METRICS,
        },
    }


def _group_metrics(metrics: list[MetricResult]) -> list[dict]:
    grouped: dict[str, list[MetricResult]] = defaultdict(list)
    for metric in metrics:
        grouped[metric.group].append(metric)

    output: list[dict] = []
    for key, label in GROUP_LABELS.items():
        items = grouped.get(key)
        if not items:
            continue
        output.append(
            {
                "key": key,
                "label": label,
                "metrics": [metric.to_dict() for metric in items],
            }
        )
    return output


def _front_metrics(points: Mapping[str, Point]) -> list[MetricResult]:
    metrics: list[MetricResult] = []
    face_width = horizontal_distance(points["zy_l"], points["zy_r"])
    total_face_height = vertical_distance(points["glabella"], points["menton"])
    nasion_to_menton = vertical_distance(points["nasion"], points["menton"])
    nose_to_chin = vertical_distance(points["subnasale"], points["menton"])
    midface_height = vertical_distance(points["nasion"], points["subnasale"])
    philtrum_height = vertical_distance(points["subnasale"], points["ls"])
    eye_width_left = horizontal_distance(points["ex_l"], points["en_l"])
    eye_width_right = horizontal_distance(points["ex_r"], points["en_r"])
    avg_eye_width = (eye_width_left + eye_width_right) / 2.0
    intercanthal_width = horizontal_distance(points["en_l"], points["en_r"])
    interpupillary_width = horizontal_distance(points["pupil_l"], points["pupil_r"])
    nose_width = horizontal_distance(points["al_l"], points["al_r"])
    mouth_width = horizontal_distance(points["ch_l"], points["ch_r"])

    metrics.extend(
        filter(
            None,
            [
                _metric(
                    key="top_third",
                    label="Top Third",
                    group="facial_thirds",
                    view="front",
                    value=safe_divide(vertical_distance(points["glabella"], points["nasion"]) * 100.0, total_face_height),
                    unit="% face height",
                    formula="(glabella-nasion) / (glabella-menton) * 100",
                    ideal_min=30.0,
                    ideal_max=36.0,
                    interpretation="Higher values indicate a relatively longer upper third / forehead.",
                ),
                _metric(
                    key="middle_third",
                    label="Middle Third",
                    group="facial_thirds",
                    view="front",
                    value=safe_divide(midface_height * 100.0, total_face_height),
                    unit="% face height",
                    formula="(nasion-subnasale) / (glabella-menton) * 100",
                    ideal_min=28.0,
                    ideal_max=32.0,
                    interpretation="Higher values indicate a relatively longer midface.",
                ),
                _metric(
                    key="lower_third",
                    label="Lower Third",
                    group="facial_thirds",
                    view="front",
                    value=safe_divide(nose_to_chin * 100.0, total_face_height),
                    unit="% face height",
                    formula="(subnasale-menton) / (glabella-menton) * 100",
                    ideal_min=33.0,
                    ideal_max=38.0,
                    interpretation="Higher values indicate a longer lower face / chin segment.",
                ),
                _metric(
                    key="face_width_to_height_ratio",
                    label="Face Width-to-Height Ratio",
                    group="face_shape",
                    view="front",
                    value=safe_divide(face_width, vertical_distance(points["nasion"], points["ls"])),
                    unit="ratio",
                    formula="bizygomatic width / (nasion-labrale superius)",
                    ideal_min=1.6,
                    ideal_max=1.95,
                    interpretation="Higher values indicate a broader and/or shorter upper face.",
                ),
                _metric(
                    key="total_facial_width_to_height_ratio",
                    label="Total Facial Width-to-Height Ratio",
                    group="face_shape",
                    view="front",
                    value=safe_divide(face_width, nasion_to_menton),
                    unit="ratio",
                    formula="bizygomatic width / (nasion-menton)",
                    ideal_min=1.2,
                    ideal_max=1.45,
                    interpretation="Higher values indicate a wider face relative to total height.",
                ),
                _metric(
                    key="midface_ratio",
                    label="Midface Ratio",
                    group="face_shape",
                    view="front",
                    value=safe_divide(midface_height, nose_to_chin),
                    unit="ratio",
                    formula="(nasion-subnasale) / (subnasale-menton)",
                    ideal_min=0.9,
                    ideal_max=1.1,
                    interpretation="Values above 1.0 indicate a longer midface than lower face.",
                ),
                _metric(
                    key="one_eye_apart_test",
                    label="One-Eye-Apart Test",
                    group="eyes_and_brows",
                    view="front",
                    value=safe_divide(interpupillary_width, avg_eye_width),
                    unit="ratio",
                    formula="interpupillary distance / average eye width",
                    ideal_min=0.9,
                    ideal_max=1.1,
                    interpretation="Higher values suggest wider-set eyes.",
                ),
                _metric(
                    key="eye_separation_ratio",
                    label="Eye Separation Ratio",
                    group="eyes_and_brows",
                    view="front",
                    value=safe_divide(intercanthal_width * 100.0, face_width),
                    unit="% face width",
                    formula="intercanthal distance / bizygomatic width * 100",
                    ideal_min=45.0,
                    ideal_max=50.0,
                    interpretation="Higher percentages indicate greater inner-eye separation relative to facial width.",
                ),
                _metric(
                    key="eye_aspect_ratio",
                    label="Eye Aspect Ratio",
                    group="eyes_and_brows",
                    view="front",
                    value=safe_divide(
                        avg_eye_width,
                        (
                            vertical_distance(points["eye_top_l"], points["eye_bot_l"])
                            + vertical_distance(points["eye_top_r"], points["eye_bot_r"])
                        )
                        / 2.0,
                    ),
                    unit="ratio",
                    formula="average eye width / average eye height",
                    ideal_min=3.0,
                    ideal_max=3.5,
                    interpretation="Higher values indicate longer, narrower eyes.",
                ),
                _metric(
                    key="lateral_canthal_tilt",
                    label="Lateral Canthal Tilt",
                    group="eyes_and_brows",
                    view="front",
                    value=(
                        _tilt_positive_when_outer_corner_is_higher(points["en_l"], points["ex_l"])
                        + _tilt_positive_when_outer_corner_is_higher(points["en_r"], points["ex_r"])
                    )
                    / 2.0,
                    unit="degrees",
                    formula="average tilt of each eye corner line relative to horizontal",
                    ideal_min=-2.0,
                    ideal_max=8.0,
                    interpretation="Positive values mean the lateral canthus sits higher than the medial canthus.",
                ),
                _metric(
                    key="eyebrow_tilt",
                    label="Eyebrow Tilt",
                    group="eyes_and_brows",
                    view="front",
                    value=(
                        _tilt_positive_when_outer_corner_is_higher(points["brow_inner_l"], points["brow_outer_l"])
                        + _tilt_positive_when_outer_corner_is_higher(points["brow_inner_r"], points["brow_outer_r"])
                    )
                    / 2.0,
                    unit="degrees",
                    formula="average tilt of each brow segment relative to horizontal",
                    ideal_min=7.0,
                    ideal_max=15.0,
                    interpretation="Higher values indicate a more elevated or arched brow tail.",
                ),
                _metric(
                    key="brow_length_to_face_width_ratio",
                    label="Brow Length to Face Width Ratio",
                    group="eyes_and_brows",
                    view="front",
                    value=safe_divide(
                        (
                            horizontal_distance(points["brow_inner_l"], points["brow_outer_l"])
                            + horizontal_distance(points["brow_inner_r"], points["brow_outer_r"])
                        )
                        / 2.0,
                        face_width,
                    ),
                    unit="ratio",
                    formula="average brow length / bizygomatic width",
                    ideal_min=0.7,
                    ideal_max=0.8,
                    interpretation="Lower values indicate short brows relative to facial width.",
                ),
                _metric(
                    key="intercanthal_nasal_width_ratio",
                    label="Intercanthal-Nasal Width Ratio",
                    group="nose_frontal",
                    view="front",
                    value=safe_divide(intercanthal_width, nose_width),
                    unit="ratio",
                    formula="intercanthal distance / alare width",
                    ideal_min=0.9,
                    ideal_max=1.1,
                    interpretation="Values above 1.0 indicate the eyes are spaced wider than the nose base.",
                ),
                _metric(
                    key="nose_bridge_to_width_ratio",
                    label="Nose Bridge to Width Ratio",
                    group="nose_frontal",
                    view="front",
                    value=safe_divide(vertical_distance(points["nasion"], points["pronasale"]), nose_width),
                    unit="ratio",
                    formula="(nasion-pronasale) / alare width",
                    ideal_min=2.4,
                    ideal_max=3.2,
                    interpretation="Higher values indicate a longer or narrower nose.",
                ),
                _metric(
                    key="nose_tip_position",
                    label="Nose Tip Position",
                    group="nose_frontal",
                    view="front",
                    value=_normalize_signed_distance(
                        signed_distance_to_line(points["pronasale"], points["nasion"], points["menton"]),
                        face_width,
                    ),
                    unit="% face width",
                    formula="signed distance of pronasale from the nasion-menton midline",
                    interpretation="Values farther from zero indicate greater nose-tip deviation from the midline.",
                    notes=["Positive/negative direction depends on image orientation."],
                ),
                _metric(
                    key="lower_to_upper_lip_ratio",
                    label="Lower-to-Upper Lip Ratio",
                    group="mouth_lips",
                    view="front",
                    value=safe_divide(vertical_distance(points["ls"], points["li"]), philtrum_height),
                    unit="ratio",
                    formula="(labrale superius-labrale inferius) / (subnasale-labrale superius)",
                    ideal_min=1.1,
                    ideal_max=1.7,
                    interpretation="Higher values indicate a fuller or longer lower lip relative to the upper lip.",
                ),
                _metric(
                    key="interpupillary_mouth_width_ratio",
                    label="Interpupillary-Mouth Width Ratio",
                    group="mouth_lips",
                    view="front",
                    value=safe_divide(mouth_width, interpupillary_width),
                    unit="ratio",
                    formula="mouth width / interpupillary distance",
                    ideal_min=0.75,
                    ideal_max=1.05,
                    interpretation="Lower values indicate a relatively narrow mouth.",
                ),
                _metric(
                    key="chin_to_philtrum_ratio",
                    label="Chin to Philtrum Ratio",
                    group="mouth_lips",
                    view="front",
                    value=safe_divide(vertical_distance(points["subnasale"], points["pogonion"]), philtrum_height),
                    unit="ratio",
                    formula="(subnasale-pogonion) / (subnasale-labrale superius)",
                    ideal_min=1.8,
                    ideal_max=2.4,
                    interpretation="Higher values indicate a longer chin-lower face segment relative to the philtrum.",
                ),
                _metric(
                    key="mouth_width_to_nose_width",
                    label="Mouth Width to Nose Width",
                    group="mouth_lips",
                    view="front",
                    value=safe_divide(mouth_width, nose_width),
                    unit="ratio",
                    formula="mouth width / nose width",
                    ideal_min=1.3,
                    ideal_max=1.7,
                    interpretation="Higher values indicate the mouth is wide relative to the nasal base.",
                ),
                _metric(
                    key="jaw_frontal_angle",
                    label="Jaw Frontal Angle",
                    group="jaw_chin_frontal",
                    view="front",
                    value=angle_degrees(points["go_l"], points["pogonion"], points["go_r"]),
                    unit="degrees",
                    formula="angle(gonion left - pogonion - gonion right)",
                    ideal_min=92.0,
                    ideal_max=100.0,
                    interpretation="Lower angles trend squarer; higher angles trend softer or more tapered.",
                ),
                _metric(
                    key="lower_third_proportion",
                    label="Lower Third Proportion",
                    group="jaw_chin_frontal",
                    view="front",
                    value=safe_divide(nose_to_chin * 100.0, nasion_to_menton),
                    unit="% lower face",
                    formula="(subnasale-menton) / (nasion-menton) * 100",
                    ideal_min=33.0,
                    ideal_max=38.0,
                    interpretation="Higher values indicate the lower third occupies more of the visible face height.",
                ),
            ],
        )
    )
    return metrics


def _side_metrics(points: Mapping[str, Point]) -> list[MetricResult]:
    metrics: list[MetricResult] = []
    face_height = vertical_distance(points["glabella"], points["pogonion"]) or 1.0
    direction_sign = 1 if points["pronasale"].x >= points["pogonion"].x else -1

    metrics.extend(
        filter(
            None,
            [
                _metric(
                    key="upper_forehead_slope",
                    label="Upper Forehead Slope",
                    group="upper_face_profile",
                    view="side",
                    value=angle_from_vertical(points["glabella"], points["trichion"]),
                    unit="degrees",
                    formula="angle from vertical of the glabella-trichion segment",
                    ideal_min=0.0,
                    ideal_max=10.0,
                    interpretation="Higher values indicate a more sloped forehead contour.",
                ),
                _metric(
                    key="browridge_inclination_angle",
                    label="Browridge Inclination Angle",
                    group="upper_face_profile",
                    view="side",
                    value=angle_from_vertical(points["glabella"], midpoint(points["brow_apex_l"], points["brow_apex_r"])),
                    unit="degrees",
                    formula="angle from vertical of the glabella-brow apex segment",
                    ideal_min=8.0,
                    ideal_max=18.0,
                    interpretation="Higher values indicate a more prominent sloping brow ridge.",
                ),
                _metric(
                    key="nasofrontal_angle",
                    label="Nasofrontal Angle",
                    group="upper_face_profile",
                    view="side",
                    value=angle_degrees(points["glabella"], points["nasion"], points["pronasale"]),
                    unit="degrees",
                    formula="angle(glabella - nasion - pronasale)",
                    ideal_min=115.0,
                    ideal_max=130.0,
                    interpretation="Lower values indicate a flatter forehead-to-nose transition.",
                ),
                _metric(
                    key="facial_convexity_glabella",
                    label="Facial Convexity (Glabella)",
                    group="profile_convexity",
                    view="side",
                    value=angle_degrees(points["glabella"], points["subnasale"], points["pogonion"]),
                    unit="degrees",
                    formula="angle(glabella - subnasale - pogonion)",
                    ideal_min=165.0,
                    ideal_max=175.0,
                    interpretation="Lower values indicate a more convex profile.",
                ),
                _metric(
                    key="facial_convexity_nasion",
                    label="Facial Convexity (Nasion)",
                    group="profile_convexity",
                    view="side",
                    value=angle_degrees(points["nasion"], points["subnasale"], points["pogonion"]),
                    unit="degrees",
                    formula="angle(nasion - subnasale - pogonion)",
                    ideal_min=155.0,
                    ideal_max=170.0,
                    interpretation="Lower values indicate stronger profile convexity through the midface.",
                ),
                _metric(
                    key="total_facial_convexity",
                    label="Total Facial Convexity",
                    group="profile_convexity",
                    view="side",
                    value=angle_degrees(points["glabella"], points["pronasale"], points["pogonion"]),
                    unit="degrees",
                    formula="angle(glabella - pronasale - pogonion)",
                    ideal_min=135.0,
                    ideal_max=150.0,
                    interpretation="Lower values indicate more anterior nasal projection relative to forehead and chin.",
                ),
                _metric(
                    key="nose_tip_rotation_angle",
                    label="Nose Tip Rotation Angle",
                    group="nose_profile",
                    view="side",
                    value=angle_from_vertical(points["subnasale"], points["pronasale"]),
                    unit="degrees",
                    formula="angle from vertical of the subnasale-pronasale segment",
                    ideal_min=18.0,
                    ideal_max=28.0,
                    interpretation="Higher values indicate a more rotated or upturned tip line.",
                ),
                _metric(
                    key="nasal_projection",
                    label="Nasal Projection",
                    group="nose_profile",
                    view="side",
                    value=_normalize_signed_distance(
                        abs(signed_distance_to_line(points["pronasale"], points["nasion"], points["pogonion"]) or 0.0),
                        face_height,
                    ),
                    unit="% face height",
                    formula="distance of pronasale from the nasion-pogonion facial plane",
                    interpretation="Higher values indicate greater forward nasal projection.",
                ),
                _metric(
                    key="nasolabial_angle",
                    label="Nasolabial Angle",
                    group="nose_profile",
                    view="side",
                    value=angle_degrees(points["pronasale"], points["subnasale"], points["ls"]),
                    unit="degrees",
                    formula="angle(pronasale - subnasale - labrale superius)",
                    ideal_min=105.0,
                    ideal_max=120.0,
                    interpretation="Lower values indicate a more acute columella-lip angle.",
                ),
                _metric(
                    key="nasomental_angle",
                    label="Nasomental Angle",
                    group="nose_profile",
                    view="side",
                    value=angle_degrees(points["nasion"], points["pronasale"], points["pogonion"]),
                    unit="degrees",
                    formula="angle(nasion - pronasale - pogonion)",
                    ideal_min=120.0,
                    ideal_max=132.0,
                    interpretation="Lower values indicate stronger nose prominence relative to the chin.",
                ),
                _metric(
                    key="nasofacial_angle",
                    label="Nasofacial Angle",
                    group="nose_profile",
                    view="side",
                    value=acute_angle_between_lines(points["glabella"], points["pogonion"], points["nasion"], points["pronasale"]),
                    unit="degrees",
                    formula="acute angle between the glabella-pogonion facial plane and the nasion-pronasale line",
                    ideal_min=30.0,
                    ideal_max=40.0,
                    interpretation="Higher values indicate the nose projects more strongly away from the facial plane.",
                ),
                _metric(
                    key="mentolabial_angle",
                    label="Mentolabial Angle",
                    group="lips_profile",
                    view="side",
                    value=angle_degrees(points["ls"], points["li"], points["pogonion"]),
                    unit="degrees",
                    formula="angle(labrale superius - labrale inferius - pogonion)",
                    ideal_min=110.0,
                    ideal_max=140.0,
                    interpretation="Lower values indicate a deeper mentolabial fold.",
                ),
                _metric(
                    key="upper_lip_e_line_position",
                    label="Upper Lip E-Line Position",
                    group="lips_profile",
                    view="side",
                    value=_direction_normalized_distance(
                        points["ls"],
                        points["pronasale"],
                        points["pogonion"],
                        direction_sign,
                        face_height,
                    ),
                    unit="% face height",
                    formula="signed distance of labrale superius from the pronasale-pogonion E-line",
                    interpretation="Values farther from zero indicate greater upper-lip prominence or retrusion relative to the E-line.",
                    notes=["Sign is normalized for face direction, but still depends on 2D image pose."],
                ),
                _metric(
                    key="lower_lip_e_line_position",
                    label="Lower Lip E-Line Position",
                    group="lips_profile",
                    view="side",
                    value=_direction_normalized_distance(
                        points["li"],
                        points["pronasale"],
                        points["pogonion"],
                        direction_sign,
                        face_height,
                    ),
                    unit="% face height",
                    formula="signed distance of labrale inferius from the pronasale-pogonion E-line",
                    interpretation="Values farther from zero indicate greater lower-lip prominence or retrusion relative to the E-line.",
                    notes=["Sign is normalized for face direction, but still depends on 2D image pose."],
                ),
                _metric(
                    key="upper_lip_s_line_position",
                    label="Upper Lip S-Line Position",
                    group="lips_profile",
                    view="side",
                    value=_direction_normalized_distance(
                        points["ls"],
                        points["subnasale"],
                        points["pogonion"],
                        direction_sign,
                        face_height,
                    ),
                    unit="% face height",
                    formula="signed distance of labrale superius from the subnasale-pogonion S-line",
                    interpretation="Values farther from zero indicate greater upper-lip prominence or retrusion relative to the S-line.",
                    notes=["Sign is normalized for face direction, but still depends on 2D image pose."],
                ),
                _metric(
                    key="lower_lip_s_line_position",
                    label="Lower Lip S-Line Position",
                    group="lips_profile",
                    view="side",
                    value=_direction_normalized_distance(
                        points["li"],
                        points["subnasale"],
                        points["pogonion"],
                        direction_sign,
                        face_height,
                    ),
                    unit="% face height",
                    formula="signed distance of labrale inferius from the subnasale-pogonion S-line",
                    interpretation="Values farther from zero indicate greater lower-lip prominence or retrusion relative to the S-line.",
                    notes=["Sign is normalized for face direction, but still depends on 2D image pose."],
                ),
            ],
        )
    )
    return metrics
