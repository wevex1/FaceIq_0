from __future__ import annotations

from dataclasses import dataclass

from .geometry import Point, average_point, horizontal_distance, midpoint, signed_distance_to_line, vertical_distance


class LandmarkExtractionError(RuntimeError):
    """Raised when the backend cannot extract a usable face mesh."""


@dataclass
class ExtractedFace:
    view: str
    points: dict[str, Point]
    image_width: int
    image_height: int
    pose_score: float
    warnings: list[str]


class FaceMeshExtractor:
    """Lazy MediaPipe extractor so pure-Python validation can run without native deps."""

    POINT_MAP: dict[str, tuple[int, ...]] = {
        "trichion": (10,),
        "glabella": (66, 107, 296, 336),
        "nasion": (168,),
        "pronasale": (1,),
        "subnasale": (2,),
        "ls": (13,),
        "li": (14,),
        "pogonion": (152,),
        "menton": (152,),
        "zy_l": (234,),
        "zy_r": (454,),
        "go_l": (172,),
        "go_r": (397,),
        "al_l": (129,),
        "al_r": (358,),
        "ex_l": (33,),
        "en_l": (133,),
        "en_r": (263,),
        "ex_r": (362,),
        "eye_top_l": (159,),
        "eye_bot_l": (145,),
        "eye_top_r": (386,),
        "eye_bot_r": (374,),
        "pupil_l": (468,),
        "pupil_r": (473,),
        "brow_outer_l": (70,),
        "brow_inner_l": (55,),
        "brow_apex_l": (65,),
        "brow_outer_r": (300,),
        "brow_inner_r": (285,),
        "brow_apex_r": (295,),
        "ch_l": (61,),
        "ch_r": (291,),
    }

    def __init__(self) -> None:
        self._face_mesh = None

    def _ensure_face_mesh(self):
        if self._face_mesh is not None:
            return self._face_mesh

        try:
            import mediapipe as mp
        except ImportError as exc:
            raise LandmarkExtractionError(
                "MediaPipe is not installed. Create the backend venv and install backend/requirements.txt."
            ) from exc

        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(
                model_asset_path="../../models/face_landmarker.task"
            ),
            num_faces=1,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )

        self._face_mesh = mp.tasks.vision.FaceLandmarker.create_from_options(options)
        return self._face_mesh

    def extract(self, image_bytes: bytes, view: str) -> ExtractedFace:
        try:
            import cv2
            import numpy as np
            import mediapipe as mp
        except ImportError as exc:
            raise LandmarkExtractionError(
                "OpenCV or NumPy is not installed. Create the backend venv and install backend/requirements.txt."
            ) from exc

        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if frame is None:
            raise LandmarkExtractionError(f"The {view} image could not be decoded.")

        height, width = frame.shape[:2]
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        results = self._ensure_face_mesh().detect(mp_image)

        if not results.face_landmarks:
            raise LandmarkExtractionError(
                f"No face mesh was detected in the {view} image. Use a well-lit, neutral {view} photo."
            )

        raw_landmarks = results.face_landmarks[0]
        if len(raw_landmarks) < 468:
            raise LandmarkExtractionError(
                f"The detected {view} face mesh is incomplete. Try a sharper image with the full face visible."
            )

        def point(index: int) -> Point:
            lm = raw_landmarks[index]
            return Point(x=lm.x * width, y=lm.y * height, z=lm.z * width)

        extracted_points: dict[str, Point] = {}
        for name, indices in self.POINT_MAP.items():
            usable_points = [point(index) for index in indices if index < len(raw_landmarks)]
            if usable_points:
                extracted_points[name] = average_point(usable_points)

        if "pupil_l" not in extracted_points:
            extracted_points["pupil_l"] = midpoint(extracted_points["ex_l"], extracted_points["en_l"])
        if "pupil_r" not in extracted_points:
            extracted_points["pupil_r"] = midpoint(extracted_points["ex_r"], extracted_points["en_r"])

        pose_score, warnings = self._score_pose(extracted_points, view)
        return ExtractedFace(
            view=view,
            points=extracted_points,
            image_width=width,
            image_height=height,
            pose_score=pose_score,
            warnings=warnings,
        )

    def _score_pose(self, points: dict[str, Point], view: str) -> tuple[float, list[str]]:
        if view == "front":
            return self._score_front_pose(points)
        return self._score_side_pose(points)

    def _score_front_pose(self, points: dict[str, Point]) -> tuple[float, list[str]]:
        warnings: list[str] = []
        face_width = horizontal_distance(points["zy_l"], points["zy_r"]) or 1.0
        face_height = vertical_distance(points["glabella"], points["menton"]) or 1.0
        left_eye_width = horizontal_distance(points["ex_l"], points["en_l"])
        right_eye_width = horizontal_distance(points["ex_r"], points["en_r"])
        avg_eye_width = max((left_eye_width + right_eye_width) / 2.0, 1e-6)
        eye_width_asymmetry = abs(left_eye_width - right_eye_width) / avg_eye_width
        eye_level_offset = abs(points["pupil_l"].y - points["pupil_r"].y) / face_height
        nose_center_offset = abs(points["pronasale"].x - midpoint(points["zy_l"], points["zy_r"]).x) / face_width

        if eye_width_asymmetry > 0.18:
            warnings.append("Front image looks rotated; eye widths differ more than expected for a frontal photo.")
        if eye_level_offset > 0.04:
            warnings.append("Front image appears tilted; eye level is not horizontal enough for stable ratios.")
        if nose_center_offset > 0.10:
            warnings.append("Front image may not be centered; the nose tip is noticeably off the facial midline.")

        score = max(0.0, 1.0 - (eye_width_asymmetry * 1.6 + eye_level_offset * 4.0 + nose_center_offset * 2.2))
        return round(score, 3), warnings

    def _score_side_pose(self, points: dict[str, Point]) -> tuple[float, list[str]]:
        warnings: list[str] = []
        face_height = vertical_distance(points["glabella"], points["menton"]) or 1.0
        face_width = horizontal_distance(points["zy_l"], points["zy_r"]) or 1.0
        eye_width_ratio = (
            horizontal_distance(points["ex_l"], points["en_l"]) + horizontal_distance(points["ex_r"], points["en_r"])
        ) / (2.0 * face_width)
        nose_projection = abs(signed_distance_to_line(points["pronasale"], points["glabella"], points["pogonion"]) or 0.0)
        nose_projection_ratio = nose_projection / face_height

        if eye_width_ratio > 0.14:
            warnings.append("Side image still looks fairly frontal; a truer profile view will improve profile angles.")
        if nose_projection_ratio < 0.08:
            warnings.append("Side image has weak lateral separation; the face may not be turned enough for profile analysis.")

        score = max(0.0, 1.0 - (eye_width_ratio * 3.2 + max(0.0, 0.10 - nose_projection_ratio) * 4.5))
        return round(score, 3), warnings
