"""Cut the board's far end without stretching its photo texture or bevels."""

import math
import pathlib

# OpenUSD comes from the independent USD/Isaac environment.
# pylint: disable=import-error
from pxr import Gf, Usd, UsdGeom

# pylint: enable=import-error

ROOT = "/WoodBoard"
MESH = ROOT + "/Visuals/Board"


def clip_face(vertices: list, cut: float) -> list:
    """Clip a polygon at +X, interpolating position, UV and normal together."""
    result = []
    for previous, current in zip(vertices[-1:] + vertices[:-1], vertices):
        previous_inside = previous[0][0] <= cut
        current_inside = current[0][0] <= cut
        if previous_inside != current_inside:
            fraction = (cut - previous[0][0]) / (current[0][0] - previous[0][0])
            result.append(
                tuple(a + fraction * (b - a) for a, b in zip(previous, current))
            )
        if current_inside:
            result.append(current)
    return result


# Mesh attributes, material subsets and the cap share one topology pass.
# pylint: disable-next=too-many-locals
def cut_mesh(mesh: UsdGeom.Mesh, width: float) -> None:
    """Retain the -X joining end and close the new +X cut with edge material."""
    source_points = mesh.GetPointsAttr().Get()
    indices = mesh.GetFaceVertexIndicesAttr().Get()
    counts = mesh.GetFaceVertexCountsAttr().Get()
    uv = UsdGeom.PrimvarsAPI(mesh).GetPrimvar("st")
    assert uv.GetInterpolation() == UsdGeom.Tokens.faceVarying
    assert not uv.IsIndexed() and set(counts) == {3}
    source_uv = uv.Get()
    source_normals = mesh.GetNormalsAttr().Get()
    assert mesh.GetNormalsInterpolation() == UsdGeom.Tokens.faceVarying
    subsets = UsdGeom.Subset.GetAllGeomSubsets(mesh)
    owners = {
        face: subset.GetPrim().GetName()
        for subset in subsets
        for face in subset.GetIndicesAttr().Get()
    }
    assert len(owners) == len(counts)
    low = min(point[0] for point in source_points)
    high = max(point[0] for point in source_points)
    assert 0 < width < high - low
    cut, offset = low + width, -(low + width / 2)
    points, faces, texture, normals, point_ids = [], [], [], [], {}
    groups = {subset.GetPrim().GetName(): [] for subset in subsets}

    def triangle(vertices, material):
        groups[material].append(len(faces) // 3)
        for point, texcoord, normal in vertices:
            key = tuple(round(component, 8) for component in point)
            if key not in point_ids:
                point_ids[key] = len(points)
                points.append(Gf.Vec3f(point[0] + offset, point[1], point[2]))
            faces.append(point_ids[key])
            texture.append(Gf.Vec2f(texcoord))
            normals.append(Gf.Vec3f(normal.GetNormalized()))

    for face in range(len(counts)):
        vertices = [
            (
                Gf.Vec3d(source_points[indices[i]]),
                Gf.Vec2d(source_uv[i]),
                Gf.Vec3d(source_normals[i]),
            )
            for i in range(face * 3, face * 3 + 3)
        ]
        polygon = clip_face(vertices, cut)
        for index in range(1, len(polygon) - 1):
            triangle([polygon[0], polygon[index], polygon[index + 1]], owners[face])

    # Retain every boundary vertex, including diagonal intersections, so the
    # cap shares all cut edges rather than introducing T-junctions.
    boundary = [Gf.Vec3d(*key) for key in point_ids if abs(key[0] - cut) < 1e-7]
    boundary.sort(key=lambda point: math.atan2(point[2], point[1]))
    center = Gf.Vec3d(cut, 0, 0)
    normal = Gf.Vec3d(1, 0, 0)
    for previous, current in zip(boundary, boundary[1:] + boundary[:1]):
        triangle(
            [
                (point, Gf.Vec2d(point[1] / 0.018 + 0.5, point[2] / 2.5 + 0.5), normal)
                for point in (center, previous, current)
            ],
            "Estimated_Edges",
        )
    mesh.GetPointsAttr().Set(points)
    mesh.GetFaceVertexCountsAttr().Set([3] * (len(faces) // 3))
    mesh.GetFaceVertexIndicesAttr().Set(faces)
    mesh.GetNormalsAttr().Set(normals)
    uv.Set(texture)
    mesh.GetExtentAttr().Set(
        [
            Gf.Vec3f(*(min(point[i] for point in points) for i in range(3))),
            Gf.Vec3f(*(max(point[i] for point in points) for i in range(3))),
        ]
    )
    for subset in subsets:
        subset.GetIndicesAttr().Set(groups[subset.GetPrim().GetName()])


def build(source: pathlib.Path, width: float) -> pathlib.Path:
    """Author a small referenced variant, sharing the original materials."""
    output = source.with_name(f"wood_board_{width:g}m.usda")
    stage = Usd.Stage.CreateNew(str(output))
    body = stage.DefinePrim(ROOT, "Xform")
    body.GetReferences().AddReference(source.name)
    stage.SetDefaultPrim(body)
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    UsdGeom.SetStageUpAxis(stage, "Z")
    cut_mesh(UsdGeom.Mesh(stage.GetPrimAtPath(MESH)), width)
    stage.GetPrimAtPath(ROOT + "/Collision/Box").GetAttribute("xformOp:scale").Set(
        Gf.Vec3f(width, 0.018, 2.5)
    )
    stage.GetRootLayer().customLayerData = {
        "source": source.name,
        "width_m": width,
        "method": "Cut +X end; retain source UVs; centered mesh and box collider",
    }
    stage.GetRootLayer().Save()
    return output
