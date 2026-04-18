from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    z: float = 0.0


def average_point(points: Iterable[Point]) -> Point:
    pts = list(points)
    if not pts:
        raise ValueError("average_point() requires at least one point.")
    return Point(
        x=sum(point.x for point in pts) / len(pts),
        y=sum(point.y for point in pts) / len(pts),
        z=sum(point.z for point in pts) / len(pts),
    )


def distance(a: Point, b: Point) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def horizontal_distance(a: Point, b: Point) -> float:
    return abs(a.x - b.x)


def vertical_distance(a: Point, b: Point) -> float:
    return abs(a.y - b.y)


def midpoint(a: Point, b: Point) -> Point:
    return Point((a.x + b.x) / 2.0, (a.y + b.y) / 2.0, (a.z + b.z) / 2.0)


def safe_divide(numerator: float, denominator: float) -> float | None:
    if abs(denominator) < 1e-8:
        return None
    return numerator / denominator


def angle_degrees(a: Point, b: Point, c: Point) -> float | None:
    abx, aby = a.x - b.x, a.y - b.y
    cbx, cby = c.x - b.x, c.y - b.y
    mag_ab = math.hypot(abx, aby)
    mag_cb = math.hypot(cbx, cby)
    if mag_ab < 1e-8 or mag_cb < 1e-8:
        return None
    cosine = (abx * cbx + aby * cby) / (mag_ab * mag_cb)
    cosine = max(-1.0, min(1.0, cosine))
    return math.degrees(math.acos(cosine))


def line_angle_degrees(a: Point, b: Point) -> float:
    return math.degrees(math.atan2(b.y - a.y, b.x - a.x))


def acute_angle_between_lines(a1: Point, a2: Point, b1: Point, b2: Point) -> float:
    first = line_angle_degrees(a1, a2)
    second = line_angle_degrees(b1, b2)
    delta = abs(first - second) % 180.0
    return min(delta, 180.0 - delta)


def angle_from_vertical(a: Point, b: Point) -> float:
    angle = abs(line_angle_degrees(a, b))
    return abs(90.0 - angle)


def signed_distance_to_line(point: Point, line_a: Point, line_b: Point) -> float | None:
    denominator = distance(line_a, line_b)
    if denominator < 1e-8:
        return None
    return (
        (line_b.x - line_a.x) * (line_a.y - point.y)
        - (line_a.x - point.x) * (line_b.y - line_a.y)
    ) / denominator
