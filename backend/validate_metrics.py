from __future__ import annotations

from app.geometry import Point
from app.landmarks import ExtractedFace
from app.research_metrics import analyze_face_pair


def build_front_face() -> ExtractedFace:
    points = {
        "trichion": Point(100, 0),
        "glabella": Point(100, 0),
        "nasion": Point(100, 40),
        "pronasale": Point(100, 60),
        "subnasale": Point(100, 80),
        "ls": Point(100, 90),
        "li": Point(100, 105),
        "pogonion": Point(100, 120),
        "menton": Point(100, 120),
        "zy_l": Point(40, 70),
        "zy_r": Point(160, 70),
        "go_l": Point(60, 112),
        "go_r": Point(140, 112),
        "al_l": Point(88, 72),
        "al_r": Point(112, 72),
        "ex_l": Point(68, 50),
        "en_l": Point(88, 50),
        "en_r": Point(112, 50),
        "ex_r": Point(132, 50),
        "eye_top_l": Point(78, 46),
        "eye_bot_l": Point(78, 54),
        "eye_top_r": Point(122, 46),
        "eye_bot_r": Point(122, 54),
        "pupil_l": Point(78, 50),
        "pupil_r": Point(122, 50),
        "brow_outer_l": Point(66, 38),
        "brow_inner_l": Point(90, 42),
        "brow_apex_l": Point(78, 36),
        "brow_outer_r": Point(134, 38),
        "brow_inner_r": Point(110, 42),
        "brow_apex_r": Point(122, 36),
        "ch_l": Point(82, 98),
        "ch_r": Point(118, 98),
    }
    return ExtractedFace(view="front", points=points, image_width=200, image_height=140, pose_score=0.99, warnings=[])


def build_side_face() -> ExtractedFace:
    points = {
        "trichion": Point(48, 6),
        "glabella": Point(56, 28),
        "nasion": Point(62, 40),
        "pronasale": Point(102, 62),
        "subnasale": Point(88, 76),
        "ls": Point(84, 84),
        "li": Point(82, 97),
        "pogonion": Point(78, 120),
        "menton": Point(78, 120),
        "brow_apex_l": Point(58, 35),
        "brow_apex_r": Point(60, 34),
        "zy_l": Point(52, 74),
        "zy_r": Point(84, 76),
        "ex_l": Point(70, 50),
        "en_l": Point(74, 50),
        "ex_r": Point(70, 50),
        "en_r": Point(74, 50),
    }
    return ExtractedFace(view="side", points=points, image_width=200, image_height=140, pose_score=0.92, warnings=[])


def metric_lookup(groups: list[dict], key: str) -> float:
    for group in groups:
        for metric in group["metrics"]:
            if metric["key"] == key:
                return metric["value"]
    raise KeyError(key)


if __name__ == "__main__":
    result = analyze_face_pair(build_front_face(), build_side_face())

    front_groups = result["front"]["groups"]
    side_groups = result["side"]["groups"]

    assert abs(metric_lookup(front_groups, "top_third") - 33.333) < 0.01
    assert abs(metric_lookup(front_groups, "middle_third") - 33.333) < 0.01
    assert abs(metric_lookup(front_groups, "lower_third") - 33.333) < 0.01
    assert abs(metric_lookup(front_groups, "face_width_to_height_ratio") - 2.4) < 0.01
    assert abs(metric_lookup(front_groups, "eye_aspect_ratio") - 2.5) < 0.01
    assert abs(metric_lookup(side_groups, "nasolabial_angle") - 161.565) < 0.05
    assert abs(metric_lookup(side_groups, "nasofacial_angle") - 47.741) < 0.05

    print("Validation passed.")
