"""Render the robot STEP assembly to PNG images (needs cadquery-ocp, numpy, matplotlib)."""
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS


def load_triangles(path, deflection=0.8):
    reader = STEPControl_Reader()
    if reader.ReadFile(path) != IFSelect_RetDone:
        raise SystemExit(f"cannot read STEP file: {path}")
    reader.TransferRoots()
    shape = reader.OneShape()
    BRepMesh_IncrementalMesh(shape, deflection, False, 0.5, True)
    tris = []
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        face = TopoDS.Face(exp.Current())
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face, loc)
        if tri is not None:
            trsf = loc.Transformation()
            pts = np.array([[p.X(), p.Y(), p.Z()] for p in
                            (tri.Node(i).Transformed(trsf) for i in range(1, tri.NbNodes() + 1))])
            rev = face.Orientation() == TopAbs_REVERSED
            for i in range(1, tri.NbTriangles() + 1):
                a, b, c = tri.Triangle(i).Get()
                tris.append(pts[[a - 1, c - 1, b - 1]] if rev else pts[[a - 1, b - 1, c - 1]])
        exp.Next()
    return np.array(tris)


def render(tris, elev, azim, out, title):
    light = np.array([0.4, -0.5, 0.75])
    light /= np.linalg.norm(light)
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    shade = 0.35 + 0.65 * np.abs(n @ light)
    base = np.array([0.55, 0.68, 0.85])
    colors = np.clip(shade[:, None] * base, 0, 1)

    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection="3d")
    ax.add_collection3d(Poly3DCollection(tris, facecolors=colors, edgecolors="none"))
    lo, hi = tris.reshape(-1, 3).min(0), tris.reshape(-1, 3).max(0)
    c, r = (lo + hi) / 2, (hi - lo).max() / 2
    ax.set_xlim(c[0] - r, c[0] + r)
    ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim, vertical_axis="y")
    ax.set_axis_off()
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    plt.close(fig)


def main():
    step = sys.argv[1] if len(sys.argv) > 1 else "robot_assembly.step"
    tris = load_triangles(step)
    print(f"{len(tris)} triangles")
    lo, hi = tris.reshape(-1, 3).min(0), tris.reshape(-1, 3).max(0)
    print("bounding box (mm):", np.round(hi - lo, 1))
    render(tris, 15, -60, "robot_front.png", "Robot assembly, front")
    render(tris, 15, 120, "robot_back.png", "Robot assembly, back")
    render(tris, 0, -90, "robot_side.png", "Robot assembly, side")


if __name__ == "__main__":
    main()
