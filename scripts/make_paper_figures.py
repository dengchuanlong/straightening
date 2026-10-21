"""Render traceable workbook figures with data provenance explicitly pending.

This script never runs a finite-element solver and never creates model metrics.
All performance panels are calculated from saved predictions or saved experiment
results. Conceptual diagrams are drawn as vector artwork, not solver screenshots.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Circle
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize
from matplotlib.text import Text
from matplotlib.lines import Line2D
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures"
COLORS = dict(blue="#0072B2", orange="#E69F00", green="#009E73", red="#D55E00",
              purple="#CC79A7", cyan="#56B4E9", grey="#66717E", dark="#1B2838")
PAL = list(COLORS.values())[:7]
FEATURES = ["width_mm", "thickness_mm", "span_mm", "punch_radius_mm",
            "support_radius_mm", "prebend_stroke_mm"]
LABELS = ["Width, $b$ (mm)", "Thickness, $h$ (mm)", "Support span, $L$ (mm)",
          "Punch radius, $R_p$ (mm)", "Support radius, $R_s$ (mm)", "Prebend peak stroke, $u$\n(mm)"]
SHORT = ["Width", "Thickness", "Span", "Punch radius", "Support radius", "Prebend"]
MANIFEST = []
FIGURE_DISPLAY_OVERRIDES = {}
FIGURE_DISPLAY_MAP_PATH = None
SUPPLEMENT_DISPLAY_IDS = {
    "S6": "S1", "S7": "S2", "S1": "S3", "S4": "S4",
    "S10": "S5", "S8": "S6", "S2": "S7", "S3": "S8",
    "S5": "S9", "S9": "S10", "S11": "S11",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10,
    "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "legend.fontsize": 7, "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": .65, "grid.linewidth": .5, "grid.alpha": .25,
    "lines.linewidth": 2.0, "savefig.dpi": 300, "svg.fonttype": "none",
    "pdf.fonttype": 42, "figure.facecolor": "white", "axes.facecolor": "white",
})


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def banner(fig, title, conceptual=False):
    def figure_heading(m):
        stable='Fig'+m.group(1)
        if stable in FIGURE_DISPLAY_OVERRIDES:
            return 'Figure '+FIGURE_DISPLAY_OVERRIDES[stable]
        return ('Supplementary Figure '+SUPPLEMENT_DISPLAY_IDS[m.group(1)]
                if m.group(1).startswith('S') else 'Figure '+m.group(1))
    title = re.sub(r"(?:Supplementary )?Figure (S?\d+)",figure_heading,title,count=1)
    fig.suptitle(title, x=.025, y=.992, ha="left", fontsize=12, fontweight="bold", color=COLORS["dark"])
    text = "Exploratory workbook analysis"
    if conceptual:
        text = "Conceptual study definitions"
    fig.text(.025, .957, text, ha="left", va="top", fontsize=7.4,
             color="#9B3800", fontweight="bold",
             bbox=dict(boxstyle="round,pad=.32", fc="#FFF2DF", ec="none"))


def panel(ax, letter, title, dx=-.12):
    ax.text(dx, 1.045, letter, transform=ax.transAxes, fontsize=11,
            fontweight="bold", va="bottom", color=COLORS["dark"])
    ax.set_title(title, loc="left", x=.055 if dx>-.10 else 0, pad=10, fontweight="bold")


def clean(ax, grid=True):
    if grid:
        ax.grid(True, zorder=0)
    ax.tick_params(length=3, width=.6)


def diagram_ax(ax):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")


def box(ax, xy, width, height, label, fc="#EAF3FA", ec=None, fs=8, bold=False):
    ec = ec or COLORS["blue"]
    patch = FancyBboxPatch(xy, width, height, boxstyle="round,pad=.01,rounding_size=.015",
                           linewidth=.9, edgecolor=ec, facecolor=fc)
    ax.add_patch(patch)
    ax.text(xy[0]+width/2, xy[1]+height/2, label, ha="center", va="center",
            fontsize=fs, fontweight="bold" if bold else "normal", color=COLORS["dark"])
    return patch


def arrow(ax, p0, p1, label=None, color=None, style="-|>", lw=1.05, fs=7.5, **kwargs):
    color = color or COLORS["grey"]
    patch = FancyArrowPatch(p0, p1, arrowstyle=style, mutation_scale=8,
                            color=color, linewidth=lw, **kwargs)
    ax.add_patch(patch)
    if label:
        p = ((p0[0]+p1[0])/2, (p0[1]+p1[1])/2)
        ax.text(p[0], p[1]+.025, label, ha="center", va="bottom", fontsize=fs, color=color)


def save(fig, number, slug, title, caption, sources, kind="main", panels=None):
    caption=caption.replace('First-seed','Seed-40').replace('first-seed','seed-40')
    if FIGURE_DISPLAY_MAP_PATH is not None:
        sources=list(sources)+[FIGURE_DISPLAY_MAP_PATH]
    OUT.mkdir(parents=True, exist_ok=True)
    stem = f"{number}_{slug}"
    png, svg = OUT / f"{stem}.png", OUT / f"{stem}.svg"
    # The manuscript embeds every figure at 6.65 inches. Clamp the nominal size
    # of visible text so the final print size is at least 8 pt after cropping.
    fig.canvas.draw()
    texts=[t for t in fig.findobj(Text) if t.get_visible() and t.get_text()]
    for _ in range(8):
        fig.canvas.draw()
        width=fig.get_tightbbox(fig.canvas.get_renderer()).width+.16
        required=8.03*width/6.65
        changed=False
        for t in texts:
            if t.get_fontsize()<required:
                t.set_fontsize(required);changed=True
        if not changed:break
    fig.canvas.draw()
    width=fig.get_tightbbox(fig.canvas.get_renderer()).width+.16
    min_print_font=min(t.get_fontsize() for t in texts)*6.65/width
    # Maintain visible rules after reduction to the document's fixed width.
    for line in fig.findobj(Line2D):
        if line.get_visible() and line.get_linestyle() not in ('None', 'none', '', ' '):
            line.set_linewidth(max(line.get_linewidth(),1.03*width/6.65))
    fig.savefig(png, dpi=300, facecolor="white", bbox_inches="tight", pad_inches=.08)
    fig.savefig(svg, facecolor="white", bbox_inches="tight", pad_inches=.08)
    plt.close(fig)
    display_id = ("Fig"+FIGURE_DISPLAY_OVERRIDES[number] if number in FIGURE_DISPLAY_OVERRIDES
                  else "Fig" + SUPPLEMENT_DISPLAY_IDS[number[3:]] if number.startswith("FigS") else number)
    MANIFEST.append(dict(id=number, display_id=display_id, kind=kind, title=title, png=str(png.relative_to(ROOT)),
        svg=str(svg.relative_to(ROOT)), caption=caption, panels=panels or [],
        provenance=[dict(path=str(Path(p).relative_to(ROOT)), sha256=digest(p)) for p in sources],
        rendering_script_sha256=digest(__file__), png_sha256=digest(png), svg_sha256=digest(svg),
        manuscript_width_inches=6.65,minimum_nominal_print_font_pt=min_print_font,
        data_origin="AUTHOR_SUPPLIED_PROVENANCE_PENDING", dpi=300,
        warning="Workbook provenance pending; numeric correspondence with earlier synthetic data. No FE validation claimed."))


def conceptual_geometry():
    fig = plt.figure(figsize=(7.2, 6.4))
    banner(fig, "Figure 1 | Study definitions and evaluation workflow", True)
    gs = fig.add_gridspec(2, 2, left=.065, right=.98, top=.89, bottom=.055,
                         wspace=.22, hspace=.38, height_ratios=[1.05, 1])
    ax = fig.add_subplot(gs[0, 0]); diagram_ax(ax)
    panel(ax, "a", "3D rectangular-bar correction", -.03)
    # Oblique vector projection of a curved rectangular bar; deliberately not an FE mesh.
    x = np.linspace(.08, .86, 50)
    z = .57 - .14*(1-((x-.47)/.39)**2)
    front = np.column_stack([x, z])
    back = front + [.075, .09]
    ax.fill_between(x, z-.05, z, color="#B6DDF1", edgecolor=COLORS["blue"], linewidth=.8)
    ax.add_patch(Polygon(np.vstack([front, back[::-1]]), fc="#D8EDF8", ec=COLORS["blue"], lw=.8))
    ax.add_patch(Polygon([front[-1], back[-1], back[-1]-[0,.05], front[-1]-[0,.05]],
                         fc="#80BEDD", ec=COLORS["blue"], lw=.8))
    for xx in [.18, .76]:
        ax.add_patch(Circle((xx, .65), .065, fc="#E6E9EC", ec=COLORS["grey"], lw=.9))
        ax.plot([xx-.09, xx+.09], [.732,.732], c=COLORS["grey"], lw=1)
        arrow(ax,(xx,.89),(xx,.74),color=COLORS["grey"])
    ax.add_patch(Circle((.505, .29), .09, fc="#FCE8BA", ec=COLORS["orange"], lw=1))
    arrow(ax, (.505,.07), (.505,.19), color=COLORS["red"])
    ax.text(.61,.26,"Lower punch\n$R_p$",fontsize=8,ha="left",va="center")
    ax.text(.075,.93,"Upper supports, $R_s$",fontsize=7.8)
    arrow(ax, (.18,.17), (.76,.17), style="<->", label="$L$", color=COLORS["dark"])
    arrow(ax, (.91,.57), (.98,.66), style="<->", color=COLORS["dark"])
    ax.text(.97,.55,"$b$",fontsize=9)
    arrow(ax, (.875,.52), (.875,.57), style="<->", color=COLORS["dark"])
    ax.text(.87,.44,"$h$",fontsize=9)
    ax.text(.03,.99,"Rectangular cross-section; finite width",fontsize=7.5, color=COLORS["grey"])

    ax = fig.add_subplot(gs[0, 1]); diagram_ax(ax)
    panel(ax, "b", "Stroke zero at first contact", -.03)
    xx=np.linspace(.08,.92,100)
    base=.65 - .09*(1-((xx-.5)/.42)**2)
    ax.plot(xx,base,c=COLORS["blue"],lw=3,label="Prebent bar")
    ax.plot([.08,.92],[.71,.71],c=COLORS["grey"],ls="--",lw=.8)
    for cx in [.17,.83]:
        ax.add_patch(Circle((cx,.68),.045,fc="#E6E9EC",ec=COLORS["grey"],lw=.8))
    ax.add_patch(Circle((.5,.47),.09,fc="#FCE8BA",ec=COLORS["orange"],lw=1))
    ax.add_patch(Circle((.5,.25),.09,fill=False,ec=COLORS["grey"],ls="--",lw=.8))
    arrow(ax,(.50,.35),(.50,.44),color=COLORS["red"])
    arrow(ax,(.66,.25),(.66,.47),style="<->",color=COLORS["red"])
    ax.text(.69,.36,"Approach\nexcluded",fontsize=7.5,va="center")
    ax.text(.50,.76,"C0: first contact, $s=0$",fontsize=7.6,ha="center",va="bottom",color=COLORS["red"])
    ax.text(.05,.89,"A prebend → B unload → C0 contact\n→ C corrective press → D unload",fontsize=7.6,linespacing=1.6)
    ax.text(.05,.08,"Positive correction stroke is upward.\n$u$: separate prebending input; air travel excluded.",fontsize=7.3,linespacing=1.5,va="top")

    ax = fig.add_subplot(gs[1, 0]); diagram_ax(ax)
    panel(ax, "c", "Planned residual-shape diagnostic", -.03)
    xx=np.linspace(.10,.90,160)
    yy=.49 + .18*(1-((xx-.50)/.40)**2)
    ax.plot(xx,yy,color=COLORS["blue"],lw=2)
    ax.plot([.1,.9],[.49,.49],color=COLORS["grey"],ls="--",lw=1)
    ax.scatter([.1,.9],[.49,.49],s=18,c=COLORS["dark"],zorder=4)
    ax.text(.08,.42,"$P_1$",fontsize=8);ax.text(.88,.42,"$P_2$",fontsize=8)
    arrow(ax,(.5,.49),(.5,.67),style="<->",color=COLORS["red"])
    ax.text(.53,.58,"$J$",fontsize=10,va="center",color=COLORS["red"])
    ax.text(.5,.31,"Endpoint chord",ha="center",fontsize=8,color=COLORS["grey"])
    ax.text(.05,.22,r"$J=\max_i\,d_\perp(P_i,\overline{P_1P_2})$",fontsize=10)
    ax.text(.05,.09,"Proposed 3D centroid-axis diagnostic;\nreference X: [-130,130] mm.",fontsize=7.1,color=COLORS["grey"],linespacing=1.5,va="top")

    ax = fig.add_subplot(gs[1, 1]); diagram_ax(ax)
    panel(ax, "d", "Evaluation and planned FE labels", -.03)
    box(ax,(.13,.82),.74,.13,"Supplied workbook\nSix-input stroke analysis",bold=True,fs=7.6)
    arrow(ax,(.5,.81),(.5,.72))
    box(ax,(.03,.55),.43,.15,"Training\nFit parameters",fs=7.6)
    box(ax,(.54,.55),.43,.15,"Validation\nSelect settings",fc="#E5F3ED",ec=COLORS["green"],fs=7.6)
    arrow(ax,(.5,.74),(.24,.70));arrow(ax,(.5,.74),(.75,.70))
    arrow(ax,(.24,.54),(.24,.44));arrow(ax,(.75,.54),(.75,.44))
    box(ax,(.03,.26),.43,.16,"Calibration\nSet quantile",fc="#FFF1D6",ec=COLORS["orange"],fs=7.6)
    box(ax,(.54,.26),.43,.16,"Test + OOD\nRetained evaluation",fc="#F9EAF0",ec=COLORS["purple"],fs=7.6)
    ax.text(.5,.13,"Unique groups retained across splits",ha="center",fontsize=8,fontweight="bold")
    ax.text(.5,.02,"Outputs: stroke predictions\nand empirical prediction intervals",ha="center",fontsize=7,color=COLORS["grey"],va="top")
    save(fig,"Fig1","concept_and_workflow","Study definitions and evaluation workflow",
         "Conceptual definitions for the rectangular-bar study. (a) The lower punch acts upward against two upper supports; b, h, L, Rp and Rs denote width, thickness, correction span and tool radii. (b) The sequence is plastic prebending, full detachment, first corrective contact, corrective pressing and full detachment. Correction stroke is zero at first contact; air travel is excluded, while u denotes the separate prebending peak. The proposed setup uses outer/inner prebending spans of 260/100 mm, a 270 mm bar and correction spans of 180-260 mm. (c) The proposed diagnostic J is the maximum normal distance of the three-dimensional area-centroid axis to its endpoint chord over initial-reference X in [-130,130] mm. This panel defines a future shape endpoint; the present response is the workbook stroke label. (d) Training, validation, calibration, test and thickness-shift evaluation have separate roles.", [],
         panels=["a geometry", "b stroke convention", "c chord diagnostic", "d evaluation workflow"])


def data_arrays(dataset):
    rows=dataset["rows"]
    X=np.array([[r[f] for f in FEATURES] for r in rows],float)
    y=np.array([r["reference_stroke_mm"] for r in rows],float)
    yc=np.array([r.get("clean_reference_stroke_mm",r["reference_stroke_mm"]) for r in rows],float)
    noise=np.array([r.get("noise_std_mm",0) for r in rows],float)
    splits=np.array([r["split"] for r in rows])
    ids=np.array([r["sample_id"] for r in rows])
    return rows,X,y,yc,noise,splits,ids


def dataset_figure(dataset, data_path):
    rows,X,y,yc,noise,splits,ids=data_arrays(dataset)
    train=splits=="train";test=splits=="test"
    fig=plt.figure(figsize=(7.2,7.0));banner(fig,"Figure 2 | Supplied-table input and stroke-label coverage")
    gs=fig.add_gridspec(3,3,left=.085,right=.98,top=.88,bottom=.075,wspace=.42,hspace=.70,
                        height_ratios=[1,1,1.3])
    for j in range(6):
        ax=fig.add_subplot(gs[j//3,j%3]);panel(ax,chr(97+j),SHORT[j],-.18)
        low=min(X[train,j].min(),X[test,j].min());high=max(X[train,j].max(),X[test,j].max())
        bins=np.linspace(low,high,15)
        ax.hist(X[train,j],bins=bins,density=True,color=COLORS["blue"],alpha=.30,label="Train")
        ax.hist(X[test,j],bins=bins,density=True,color=COLORS["orange"],histtype="step",lw=1.3,label="Test")
        ax.set_xlabel(LABELS[j]);ax.set_ylabel("Density");clean(ax)
        if j==0:ax.legend(frameon=False,fontsize=6.5)
    ax=fig.add_subplot(gs[2,:2]);panel(ax,"g","Workbook label distributions",-.07)
    lo=y[splits!="ood"].min();hi=y[splits!="ood"].max()
    bins=np.linspace(lo,hi,38)
    ax.hist(y[train],bins=bins,density=True,alpha=.28,color=COLORS["blue"],label="Training stroke label")
    ax.hist(y[test],bins=bins,density=True,histtype="step",lw=1.4,color=COLORS["orange"],label="Retained test stroke label")
    peak=max(np.histogram(v,bins=bins,density=True)[0].max() for v in [y[train],y[test]])
    ax.set_ylim(0,peak*1.35)
    ax.set_xlabel("Reference stroke (mm)");ax.set_ylabel("Density");ax.legend(frameon=False,fontsize=6.8);clean(ax)
    ax=fig.add_subplot(gs[2,2]);panel(ax,"h","Thickness and label shift",-.18)
    for sp,c,label in [("train",COLORS["blue"],"Train"),("ood",COLORS["orange"],"OOD")]:
        mask=splits==sp
        ax.scatter(X[mask,1],y[mask],s=2.8,alpha=.20,c=c,rasterized=True,edgecolors="none",label=label)
    ax.set_xlabel("Thickness (mm)");ax.set_ylabel("Workbook stroke (mm)");ax.legend(frameon=False);clean(ax)
    counts={s:int(np.sum(splits==s)) for s in np.unique(splits)}
    save(fig,"Fig2","workbook_dataset","Supplied-table input and stroke-label coverage",
         "Input and response coverage of the supplied workbook. (a-f) Normalized histograms compare training and in-distribution test inputs using common bins. (g) Complete training and test stroke-label distributions. (h) Thickness versus stroke in the training and thickness-shift subsets; shifted thickness occupies 9.25-10 mm. Two legacy diagnostic columns are excluded from predictor inputs, targets and plotted panels. Split counts: "+", ".join(f"{k}={v}" for k,v in counts.items())+".",[data_path],
         panels=["a–f six feature distributions", "g supplied-label distributions", "h thickness and label shift"])


DISPLAY = {"Mean":"Mean", "Ridge":"Ridge", "RBF_SVR":"RBF–SVR", "RandomForest":"Random forest",
           "HGB":"HGB", "MLP":"MLP", "MGRE":"MGRE", "NoMechanics":"Raw inputs +\nconstant prior",
           "NoGate":"No gate", "NoGlobal":"No global SVR", "NoLocal":"No local experts",
           "NoResidualPrior":"No residual prior", "NoRatioPredictor":"No ratios in\npredictor", "ConstantInterval":"Constant scale"}
BASELINES = ["Mean", "Ridge", "RBF_SVR", "RandomForest", "HGB", "MLP"]
ABLA = ["MGRE", "NoMechanics", "NoResidualPrior", "NoRatioPredictor", "NoGate", "NoGlobal", "NoLocal"]


def run_for(results, model, seed=None):
    runs=[r for r in results["seed_results"] if r["model"]==model]
    if seed is None:
        seed=min(r["seed"] for r in runs)
    return next(r for r in runs if r["seed"]==seed)


def pred_arrays(run, split="test"):
    p=run["predictions"][split]
    return tuple(np.asarray(p[k],float) for k in ["y_true","y_pred","lower","upper"])


def summary(results, model, metric="RMSE_mm", split="iid"):
    v=results["model_summaries"][model][split][metric]
    return v["mean"],v["std"]


def validate_results(dataset, results):
    """Reject mismatched IDs, target copies, metrics or origins before plotting."""
    byid={r["sample_id"]:r for r in dataset["rows"]}
    checked=0
    for run in results["seed_results"]:
        assert run["data_origin"]=="AUTHOR_SUPPLIED_PROVENANCE_PENDING"
        for split,p in run["predictions"].items():
            y,pred,low,up=pred_arrays(run,split)
            ids=p["sample_ids"]
            assert len(set(ids))==len(ids)==len(y)
            assert all(byid[i]["split"]==split for i in ids)
            reference=np.array([byid[i]["reference_stroke_mm"] for i in ids])
            np.testing.assert_allclose(y,reference,rtol=0,atol=1e-12)
            assert np.isfinite(np.vstack([y,pred,low,up])).all()
            assert np.all(low<=pred) and np.all(pred<=up)
            np.testing.assert_allclose(np.sqrt(np.mean((y-pred)**2)),run["metrics"][split]["RMSE_mm"],rtol=1e-10)
            np.testing.assert_allclose(np.mean((y>=low)&(y<=up)),run["metrics"][split]["coverage_90"],rtol=1e-10)
            checked+=1
    return dict(prediction_arrays_checked=checked,ids_targets_rmse_coverage_consistent=True)


def model_architecture(dataset, results, paths):
    fig=plt.figure(figsize=(7.2,6.7));banner(fig,"Figure 3 | Gated residual prediction and calibrated intervals")
    gs=fig.add_gridspec(2,2,left=.075,right=.98,top=.88,bottom=.075,hspace=.48,wspace=.35,
                        height_ratios=[1.25,1])
    ax=fig.add_subplot(gs[0,:]);diagram_ax(ax);panel(ax,"a","MGRE architecture (conceptual schematic)",-.03)
    box(ax,(.02,.47),.115,.22,"Six inputs\n$b,h,L,R_p,$\n$R_s,u$",fs=8,bold=True)
    box(ax,(.19,.47),.16,.22,"Positive scale $m$\n+ 12 features $z$\nTrain-only scaling",fs=7.3)
    arrow(ax,(.14,.58),(.18,.58))
    box(ax,(.405,.73),.17,.17,"GMM soft gate\n$g_1+g_2+g_3=1$",fc="#E5F3ED",ec=COLORS["green"],fs=7.5)
    arrow(ax,(.35,.65),(.405,.80))
    for k,yy in enumerate([.75,.52,.29]):
        box(ax,(.625,yy),.14,.15,f"HGB expert {k+1}\nResidual $f_{k+1}(z)$",fc="#E5F3ED",ec=COLORS["green"],fs=7.3)
        arrow(ax,(.575,.81),(.625,yy+.075),color=COLORS["green"])
    box(ax,(.405,.15),.17,.17,"Global RBF–SVR\nResidual $f_G(z)$",fc="#F4E8F0",ec=COLORS["purple"],fs=7.5)
    arrow(ax,(.35,.50),(.405,.24),color=COLORS["purple"])
    box(ax,(.835,.47),.145,.22,"Residual fusion\n$\\alpha$ from VAL\n$\\hat{s}=m\\,e^{\\hat{r}}$",fc="#FFF1D6",ec=COLORS["orange"],fs=7.6,bold=True)
    for yy in [.825,.595,.365]:arrow(ax,(.77,yy),(.835,.58),color=COLORS["green"])
    arrow(ax,(.58,.235),(.835,.49),color=COLORS["purple"],connectionstyle="angle,angleA=0,angleB=90,rad=7")
    ax.text(.005,.045,r"$d_y=\sigma_yL^2/(6Eh),\quad m=u(L/260)^2+d_y,\quad r=\log(s_{ref}/m)$",fontsize=8.6)
    ax.text(.005,-.06,r"$\hat{r}=\alpha f_G(z)+(1-\alpha)\sum_{k=1}^3g_kf_k(z)$    |    Squared residual loss for weighted experts",fontsize=8)

    ax=fig.add_subplot(gs[1,0]);panel(ax,"b","Three learned feature regimes",-.15)
    r=run_for(results,"MGRE");p=r["predictions"]["test"]
    byid={row["sample_id"]:row for row in dataset["rows"]}
    xx=np.array([[byid[i][f] for f in FEATURES] for i in p["sample_ids"]])
    mat=dataset["metadata"]["fixed_material"]
    dy=mat["yield_stress_MPa"]*xx[:,2]**2/(6*mat["elastic_modulus_MPa"]*xx[:,1])
    gate=np.asarray(p["gate_probabilities"]);reg=gate.argmax(axis=1)
    for k,c in enumerate([COLORS["blue"],COLORS["orange"],COLORS["green"]]):
        mask=reg==k
        ax.scatter(xx[mask,5]/dy[mask],xx[mask,2]/xx[mask,1],s=6,alpha=.5,c=c,
                   label=f"Gate {k+1} (n={mask.sum()})",edgecolors="none",rasterized=True)
    ax.set_xlabel(r"Prebend / yield scale, $u/d_y$");ax.set_ylabel(r"Slenderness, $L/h$")
    ax.legend(frameon=False,fontsize=6.5,loc="best");clean(ax)
    ax.text(.02,.02,"Statistical clusters only",transform=ax.transAxes,
            fontsize=6.4,color=COLORS["grey"],bbox=dict(fc="white",ec="none",alpha=.8))

    ax=fig.add_subplot(gs[1,1]);diagram_ax(ax);panel(ax,"c","Split conformal calibration",-.03)
    box(ax,(.07,.77),.86,.16,"VAL: train positive error scale $a(x)$",fs=7.8)
    arrow(ax,(.50,.76),(.50,.65))
    box(ax,(.07,.46),.86,.18,"CAL: $v_i=|s_i-\\hat{s}_i|/a(x_i)$\nFinite-sample 90% quantile $q$",fc="#FFF1D6",ec=COLORS["orange"],fs=7.8)
    arrow(ax,(.50,.45),(.50,.33))
    box(ax,(.07,.12),.86,.18,"TEST: $[\\max(0,\\hat{s}-qa),\\ \\hat{s}+qa]$\nOOD: evaluated without recalibration",fc="#F4E8F0",ec=COLORS["purple"],fs=7.5)
    ax.text(.5,.02,"Fixed CAL quantile; evaluate\nIID and thickness-shift coverage.",ha="center",fontsize=6.8,color=COLORS["grey"],va="top")
    alphas=[run_for(results,"MGRE",s)["details"]["alpha"] for s in results["metadata"]["training_seeds"]]
    save(fig,"Fig3","model_architecture","Gated residual prediction and calibrated intervals",
         "Mechanics-normalized gated residual ensemble (MGRE). (a) Six inputs yield a positive engineering scale m and twelve train-standardized predictors. A three-component Gaussian-mixture gate weights three histogram-gradient-boosted residual experts, while a global RBF support-vector regressor predicts the same log residual. Validation MAE selects alpha from {0,0.25,0.5,0.75,1}; reconstruction is m exp(rhat). Modulus and yield stress are assigned reference constants. (b) First-seed test rows projected onto two gate inputs and colored by their maximum-probability gate assignment, showing learned statistical clusters. (c) Absolute validation errors train a positive scale; a separate calibration set supplies the finite-sample quantile. Intervals have nonnegative lower endpoints and target marginal 90% coverage under exchangeability. The thickness-shift test evaluates empirical coverage without recalibration. Selected alpha values by training seed: "+str(alphas)+".",paths,
         panels=["a implemented predictor", "b actual learned gate assignments", "c conformal interval procedure"])


def parity(ax, y, p, color, label=None):
    lo=min(y.min(),p.min());hi=max(y.max(),p.max());pad=(hi-lo)*.03
    ax.scatter(y,p,s=6,alpha=.30,c=color,edgecolors="none",rasterized=True)
    ax.plot([lo-pad,hi+pad],[lo-pad,hi+pad],ls="--",c=COLORS["dark"],lw=.9)
    ax.set_xlim(lo-pad,hi+pad);ax.set_ylim(lo-pad,hi+pad)
    ax.set_xlabel("Workbook stroke label (mm)");ax.set_ylabel("Predicted stroke (mm)")
    rmse=np.sqrt(np.mean((y-p)**2));mae=np.mean(np.abs(y-p))
    ax.text(.04,.96,f"RMSE = {rmse:.3f} mm\nMAE = {mae:.3f} mm",transform=ax.transAxes,va="top",fontsize=7.5,
            bbox=dict(fc="white",ec="none",alpha=.90))
    clean(ax)


def point_performance(results, path):
    fig=plt.figure(figsize=(7.2,6.5));banner(fig,"Figure 4 | Retained-split prediction performance")
    gs=fig.add_gridspec(2,2,left=.095,right=.98,top=.88,bottom=.075,wspace=.35,hspace=.49)
    best=results["metadata"]["best_baseline_by_validation"]
    run=run_for(results,"MGRE");br=run_for(results,best)
    y,p,lo,up=pred_arrays(run);_,bp,_,_=pred_arrays(br)
    ax=fig.add_subplot(gs[0,0]);panel(ax,"a","MGRE test parity",-.16);parity(ax,y,p,COLORS["blue"])
    ax=fig.add_subplot(gs[0,1]);panel(ax,"b","Signed prediction error",-.16)
    errors=[p-y,bp-y];bound=max(np.max(np.abs(e)) for e in errors)
    bins=np.linspace(-bound*1.08,bound*1.08,35)
    ax.hist(errors[0],bins=bins,density=True,color=COLORS["blue"],alpha=.30,label="MGRE")
    ax.hist(errors[1],bins=bins,density=True,color=COLORS["orange"],histtype="step",lw=1.4,label=DISPLAY[best])
    ax.axvline(0,c=COLORS["grey"],ls="--",lw=.8);ax.set_xlabel("Prediction − reference (mm)");ax.set_ylabel("Density")
    ax.legend(frameon=False);clean(ax)
    ax=fig.add_subplot(gs[1,0]);panel(ax,"c","All baseline families",-.16)
    names=sorted(BASELINES+["MGRE"],key=lambda n:summary(results,n)[0],reverse=True)
    vals=np.array([summary(results,n)[0] for n in names]);sd=np.array([summary(results,n)[1] for n in names])
    cols=[COLORS["blue"] if n=="MGRE" else COLORS["orange"] if n==best else "#AAB4BE" for n in names]
    ax.barh(np.arange(len(names)),vals,xerr=sd,color=cols,height=.65,error_kw=dict(capsize=2,lw=.8),zorder=3)
    ax.set_yticks(np.arange(len(names)),[DISPLAY[n] for n in names]);ax.set_xlabel("Test RMSE (mm), mean ± seed SD");clean(ax)
    ax.set_xscale("log");ax.grid(axis="x",which="both")
    for i,v in enumerate(vals):ax.text((v+sd[i])*1.06,i,f"{v:.4f}" if v<1 else f"{v:.3f}",va="center",fontsize=6.4)
    ax.set_xlim(max(.02,vals.min()*.65),vals.max()*1.95)
    ax=fig.add_subplot(gs[1,1]);panel(ax,"d","Error across the target range",-.16)
    edges=np.quantile(y,np.linspace(0,1,11));idx=np.clip(np.digitize(y,edges[1:-1]),0,9)
    for pp,c,label in [(p,COLORS["blue"],"MGRE"),(bp,COLORS["orange"],DISPLAY[best])]:
        xm=np.array([np.mean(y[idx==j]) for j in range(10)]);ym=np.array([np.mean(np.abs(pp[idx==j]-y[idx==j])) for j in range(10)])
        ax.plot(xm,ym,"o-",ms=3,c=c,label=label)
    ax.set_xlabel("Mean reference within test decile (mm)");ax.set_ylabel("Mean absolute error (mm)");ax.legend(frameon=False);clean(ax)
    save(fig,"Fig4","test_performance","Retained-split prediction performance",
         "Retained-split prediction performance. (a) First-seed MGRE parity on the 1,000-row in-distribution test set. (b) Signed-error densities compare this fit with "+DISPLAY[best]+", selected by validation MAE. (c) Six baselines and MGRE ordered by mean test RMSE for display. Bars and whiskers show means and sample SD across three training seeds; the logarithmic axis accommodates all families. (d) First-seed MAE across ten equal-count target bins summarizes error over the response range.",[path],
         panels=["a first-seed MGRE parity", "b first-seed signed error", "c all family benchmark", "d target-decile error"])


def ablation_and_learning(results, path):
    fig=plt.figure(figsize=(7.2,6.3));banner(fig,"Figure 5 | Component ablations and training-size response")
    gs=fig.add_gridspec(2,2,left=.10,right=.98,top=.88,bottom=.08,wspace=.37,hspace=.54)
    for k,metric in enumerate(["RMSE_mm","MAE_mm"]):
        ax=fig.add_subplot(gs[0,k]);panel(ax,chr(97+k),"Point-prediction ablations: "+metric.split("_")[0],-.18)
        vals=[summary(results,n,metric)[0] for n in ABLA];sd=[summary(results,n,metric)[1] for n in ABLA]
        ax.barh(np.arange(len(ABLA)),vals,color=[COLORS["blue"]]+["#B4C4D0"]*(len(ABLA)-1),height=.64,
                xerr=sd,error_kw=dict(capsize=2,lw=.8),zorder=3)
        for i,n in enumerate(ABLA):
            for j,r in enumerate([r for r in results["seed_results"] if r["model"]==n]):
                ax.scatter(r["metrics"]["test"][metric],i+(j-1)*.11,s=10,c=COLORS["dark"],zorder=5,edgecolors="white",lw=.3)
        ax.set_yticks(np.arange(len(ABLA)),[DISPLAY[n] for n in ABLA]);ax.invert_yaxis();ax.set_xlabel(f"Test {metric.split('_')[0]} (mm)")
        ax.axvline(vals[0],c=COLORS["blue"],ls="--",lw=.8);clean(ax)
        ax.set_xlim(0,max(vals)*1.18)
    models=list(dict.fromkeys(c["model"] for c in results["learning_curves"]))
    nseeds=len(results["metadata"]["training_seeds"])
    for k,metric in enumerate(["test_RMSE_mm","test_MAE_mm"]):
        ax=fig.add_subplot(gs[1,k]);panel(ax,chr(99+k),"Learning curve: "+metric.split("_")[1],-.18)
        for j,n in enumerate(models):
            curve=[c for c in results["learning_curves"] if c["model"]==n]
            sizes=sorted({c["n_train"] for c in curve});val=[];sd=[]
            for size in sizes:
                values=[c[metric] for c in curve if c["n_train"]==size]
                val.append(np.mean(values));sd.append(np.std(values,ddof=1) if len(values)>1 else 0)
            val=np.asarray(val);sd=np.asarray(sd)
            c=COLORS["blue"] if n=="MGRE" else COLORS["orange"]
            ax.plot(sizes,val,"o-",ms=3,c=c,label=DISPLAY[n]);ax.fill_between(sizes,np.maximum(0,val-sd),val+sd,color=c,alpha=.16)
        ax.set_xscale("log");ax.set_xticks(sizes,[str(s) for s in sizes],rotation=35);ax.set_xlabel("Training geometries (log scale)")
        ax.set_ylabel("Test "+metric.split("_")[1]+" (mm)");ax.legend(frameon=False);clean(ax)
    save(fig,"Fig5","ablations_learning_curves","Component ablations and training-size response",
         "Component ablations and training-size response. (a,b) MGRE is compared with six point-prediction ablations: raw inputs plus a training-median scale; m=1 with engineered features and gate retained; six raw predictor inputs with the prior and gate retained; equal expert weights; removal of the global SVR; or removal of local experts. Fusion selection uses validation MAE for each applicable configuration. Bars and whiskers show mean and sample SD across "+str(nseeds)+" training seeds; dots show individual fits and the dashed line marks full MGRE. The constant-scale interval variant appears in Figure 6 because its point predictions are unchanged. (c,d) MGRE and the validation-selected baseline are refitted at each subset size. Curves show seed means with bands of plus or minus one sample SD on a fixed test set, summarizing algorithm and subset sensitivity.",[path],
         panels=["a point-ablation RMSE", "b point-ablation MAE", "c learning RMSE", "d learning MAE"])


def calibration_and_ood(dataset, results, paths):
    fig=plt.figure(figsize=(7.2,6.5));banner(fig,"Figure 6 | Interval calibration and thickness-shift stress test")
    gs=fig.add_gridspec(2,2,left=.105,right=.98,top=.83,bottom=.08,wspace=.39,hspace=.52)
    best=results["metadata"]["best_baseline_by_validation"];names=["MGRE",best,"ConstantInterval"]
    for j,metric in enumerate(["coverage_90","mean_interval_width_mm"]):
        ax=fig.add_subplot(gs[0,j]);panel(ax,chr(97+j),"Empirical coverage" if j==0 else "Mean prediction-interval width",-.18)
        for k,split in enumerate(["iid","ood"]):
            v=np.array([summary(results,n,metric,split)[0] for n in names]);s=np.array([summary(results,n,metric,split)[1] for n in names])
            ax.bar(np.arange(3)+(k-.5)*.34,v,width=.32,yerr=s,color=COLORS["blue"] if k==0 else COLORS["orange"],
                   label="IID test" if k==0 else "Thickness OOD",error_kw=dict(capsize=2,lw=.8),zorder=3)
        ax.set_xticks(np.arange(3),["MGRE",DISPLAY[best],"MGRE\nconstant scale"])
        if j==0:
            ax.axhline(.9,c=COLORS["red"],lw=1,ls="--",label="Nominal 90%")
            ax.set_ylim(0,1.04);ax.set_yticks(np.linspace(0,1,6));ax.set_ylabel("Covered fraction")
        else:
            ax.set_ylabel("Mean width (mm)")
            peak=max(summary(results,n,metric,s)[0]+summary(results,n,metric,s)[1] for n in names for s in ["iid","ood"])
            ax.set_ylim(0,peak*1.08)
        if j==0:
            handles,labels=ax.get_legend_handles_labels()
            fig.legend(handles,labels,loc="upper center",bbox_to_anchor=(.52,.923),
                       frameon=False,ncol=3,fontsize=8.8,columnspacing=1.2,handlelength=1.8)
        clean(ax)
    ax=fig.add_subplot(gs[1,0]);panel(ax,"c","Retained shift in thickness",-.18)
    _,X,y,yc,noise,splits,ids=data_arrays(dataset)
    for split,color,label in [("train",COLORS["blue"],"Train: 7–9 mm"),("ood",COLORS["orange"],"OOD: 9.25–10 mm")]:
        mask=splits==split;ax.hist(X[mask,1],bins=np.linspace(7,10,31),density=True,alpha=.4,color=color,label=label)
    ax.axvspan(9,9.25,fc="#E9EDF0",zorder=0);ax.set_xlabel("Thickness (mm)");ax.set_ylabel("Density");ax.legend(frameon=False,fontsize=6.6);clean(ax)
    ax.text(.02,.97,"Other five input ranges are unchanged",transform=ax.transAxes,va="top",fontsize=6.5,color=COLORS["grey"])
    ax=fig.add_subplot(gs[1,1]);panel(ax,"d","Prediction error under shift",-.18)
    names=sorted(BASELINES+["MGRE"],key=lambda n:summary(results,n)[0],reverse=True)
    for k,n in enumerate(names):
        i,si=summary(results,n);o,so=summary(results,n,split="ood")
        ax.plot([i,o],[k,k],c="#AAB4BE",lw=1,zorder=1)
        ax.errorbar(i,k,xerr=si,fmt="o",c=COLORS["blue"],ms=3,capsize=2,lw=.8)
        ax.errorbar(o,k,xerr=so,fmt="s",c=COLORS["orange"],ms=3,capsize=2,lw=.8)
    ax.set_yticks(range(len(names)),[DISPLAY[n] for n in names]);ax.set_xscale("log");ax.set_xlabel("RMSE (mm), mean ± seed SD")
    ax.plot([],[],"o",c=COLORS["blue"],ms=3,label="IID test");ax.plot([],[],"s",c=COLORS["orange"],ms=3,label="Thickness OOD")
    clean(ax)
    save(fig,"Fig6","calibration_ood","Interval calibration and thickness-shift stress test",
         "Interval calibration and thickness-shift evaluation. (a,b) Mean empirical 90% coverage and width across training seeds for MGRE, the validation-selected baseline and MGRE with constant error scale. The constant-scale variant retains MGRE point predictions and calibrates its own quantile. Whiskers show sample SD across seeds. The 90% line denotes the marginal in-distribution target. (c) Training thickness is uniform on 7-9 mm and shifted thickness on 9.25-10 mm; the other five input ranges are shared. (d) IID and OOD RMSE for all six baseline families and MGRE. Shifted-data results use the original fitted models and calibration quantiles.",paths,
         panels=["a IID/OOD coverage", "b IID/OOD width", "c thickness feature shift", "d all models IID/OOD RMSE"])


def baseline_parities(results, path):
    fig=plt.figure(figsize=(7.2,7.3));banner(fig,"Supplementary Figure S1 | Complete baseline test parities")
    gs=fig.add_gridspec(3,2,left=.095,right=.98,top=.88,bottom=.07,wspace=.33,hspace=.47)
    for i,n in enumerate(BASELINES):
        ax=fig.add_subplot(gs[i//2,i%2]);panel(ax,chr(97+i),DISPLAY[n],-.15)
        y,p,_,_=pred_arrays(run_for(results,n));parity(ax,y,p,PAL[i%len(PAL)])
    save(fig,"FigS1","baseline_parities","Complete baseline test parities",
         "First-seed predictions of all six baseline families on the same 1,000-row IID test set. Dashed lines denote parity; annotations are computed from each panel's predictions. Equal x/y limits are used within panels, with ranges adjusted between families to include every point. Hyperparameters were selected using validation labels. The constant mean predictor provides a shared-value reference alongside Ridge, RBF-SVR, random forest, histogram gradient boosting and multilayer perceptron.",[path],kind="supplementary",
         panels=[DISPLAY[n]+" parity" for n in BASELINES])


def regime_diagnostics(results, path):
    fig=plt.figure(figsize=(7.2,6.4));banner(fig,"Supplementary Figure S2 | Errors within learned feature regimes")
    gs=fig.add_gridspec(2,2,left=.095,right=.98,top=.88,bottom=.08,wspace=.36,hspace=.49)
    r=run_for(results,"MGRE");best=results["metadata"]["best_baseline_by_validation"];br=run_for(results,best)
    ax=fig.add_subplot(gs[0,0]);panel(ax,"a","Gate-assignment composition",-.16)
    for j,split in enumerate(["test","ood"]):
        reg=np.asarray(r["predictions"][split]["regime_argmax"]);counts=np.bincount(reg,minlength=3)/len(reg)
        ax.bar(np.arange(3)+(j-.5)*.34,counts,width=.32,color=COLORS["blue"] if j==0 else COLORS["orange"],
               label="IID test" if j==0 else "Thickness OOD",zorder=3)
    ax.set_xticks(range(3),["Gate 1","Gate 2","Gate 3"]);ax.set_ylabel("Assigned fraction");ax.legend(frameon=False);clean(ax)
    for j,split in enumerate(["test","ood"]):
        ax=fig.add_subplot(gs[0,1] if j==0 else gs[1,0]);panel(ax,chr(98+j),"IID error by gate" if j==0 else "OOD error by gate",-.16)
        reg=np.asarray(r["predictions"][split]["regime_argmax"])
        for k,(run,c,n) in enumerate([(r,COLORS["blue"],"MGRE"),(br,COLORS["orange"],DISPLAY[best])]):
            y,p,_,_=pred_arrays(run,split)
            means=[np.mean(np.abs(y[reg==i]-p[reg==i])) if (reg==i).any() else np.nan for i in range(3)]
            ax.bar(np.arange(3)+(k-.5)*.34,means,width=.32,color=c,label=n,zorder=3)
        ax.set_xticks(range(3),[f"Gate {i+1}\nn={(reg==i).sum()}" for i in range(3)]);ax.set_ylabel("Mean absolute error (mm)")
        ax.set_ylim(0,np.nanmax([p.get_height() for p in ax.patches])*1.22)
        ax.legend(frameon=False,fontsize=6.5,ncol=2,loc="upper center");clean(ax)
    ax=fig.add_subplot(gs[1,1]);panel(ax,"d","Gate strength and prediction error",-.16)
    for split,c,n in [("test",COLORS["blue"],"IID test"),("ood",COLORS["orange"],"Thickness OOD")]:
        y,p,_,_=pred_arrays(r,split);gate=np.asarray(r["predictions"][split]["gate_probabilities"])
        ax.scatter(gate.max(axis=1),np.abs(y-p),c=c,s=5,alpha=.22,edgecolors="none",label=n,rasterized=True)
    ax.set_xlabel("Maximum soft-gate probability");ax.set_ylabel("MGRE absolute error (mm)");ax.legend(frameon=False,markerscale=2);clean(ax)
    save(fig,"FigS2","gate_regime_errors","Errors within learned feature regimes",
         "Prediction errors within learned feature clusters. First-seed diagnostics assign each row to the maximum-probability component of the fitted MGRE Gaussian-mixture gate. (a) Assignment proportions in IID and thickness-shift subsets. (b,c) MGRE and the validation-selected baseline evaluated on identical MGRE-assigned groups; n denotes row count and bars show empirical MAE. (d) MGRE absolute error versus maximum gate probability. Gate probability measures statistical cluster membership; predictive intervals are calibrated separately.",[path],kind="supplementary",
         panels=["a regime composition", "b IID grouped error", "c OOD grouped error", "d gate strength versus error"])


def fitted_sensitivity(dataset, results, paths):
    import sys
    import joblib
    from threadpoolctl import threadpool_limits
    sys.path.insert(0,str(ROOT/"scripts"))
    import run_experiments as exp
    # Executed experiment scripts save their custom estimator in __main__.
    setattr(sys.modules["__main__"],"MGRE",exp.MGRE)
    seed=min(results["metadata"]["training_seeds"])
    model_path=ROOT/"models"/f"MGRE_seed{seed}.joblib"
    bundle=joblib.load(model_path)
    assert bundle["data_origin"]=="AUTHOR_SUPPLIED_PROVENANCE_PENDING"
    assert bundle["data_sha256"]==results["metadata"]["data_sha256"]
    m=bundle["point_model"]
    _,X,y,yc,noise,splits,ids=data_arrays(dataset)
    train_idx=np.flatnonzero(splits=="train")
    # Deterministic uniform-in-index subsample, fixed independently of outcomes.
    background_idx=train_idx[np.linspace(0,len(train_idx)-1,128,dtype=int)]
    background=X[background_idx]
    payload=dict(data_origin="AUTHOR_SUPPLIED_PROVENANCE_PENDING",model_file=str(model_path.relative_to(ROOT)),
                 model_sha256=digest(model_path),background_sample_ids=ids[background_idx].tolist(),
                 interpretation="Partial dependence and ICE of one fitted workbook model; not physical sensitivity or uncertainty.",features={})
    fig=plt.figure(figsize=(7.2,7.0));banner(fig,"Supplementary Figure S3 | Fitted-model response diagnostics")
    gs=fig.add_gridspec(3,2,left=.095,right=.98,top=.88,bottom=.07,wspace=.34,hspace=.53)
    with threadpool_limits(limits=1):
        for j in range(6):
            bounds=dataset["metadata"]["in_domain_bounds"][FEATURES[j]]
            grid=np.linspace(*bounds,25);curves=[]
            for value in grid:
                work=background.copy();work[:,j]=value;curves.append(m.predict(work))
            ice=np.asarray(curves).T;pdp=ice.mean(axis=0)
            # Centering removes differences in the fixed backgrounds' baselines.
            centered=ice-ice.mean(axis=1,keepdims=True);pdp_centered=centered.mean(axis=0)
            payload["features"][FEATURES[j]]=dict(grid=grid.tolist(),mean_prediction_mm=pdp.tolist(),
                 centered_mean_prediction_mm=pdp_centered.tolist(),ice_centered_mm=centered.tolist())
            ax=fig.add_subplot(gs[j//2,j%2]);panel(ax,chr(97+j),SHORT[j],-.16)
            for k in np.linspace(0,127,8,dtype=int):
                ax.plot(grid,centered[k],c=COLORS["grey"],alpha=.32,lw=.65)
            ax.plot(grid,pdp_centered,c=COLORS["blue"],lw=1.8,label="Partial dependence (centered)")
            ax.axhline(0,c=COLORS["grey"],ls="--",lw=.65);ax.set_xlabel(LABELS[j]);ax.set_ylabel("Centered prediction (mm)");clean(ax)
            if j==0:
                ax.plot([],[],c=COLORS["grey"],alpha=.6,lw=.7,label="8 fixed-background ICE curves")
                ax.legend(frameon=False,fontsize=6,loc="best")
    sidecar=OUT/"fitted_model_sensitivity.json";sidecar.write_text(json.dumps(payload,indent=2),encoding="utf-8")
    save(fig,"FigS3","fitted_model_sensitivity","Fitted-model response diagnostics",
         "Centered partial-dependence and individual-conditional-expectation (ICE) responses of the first-seed MGRE fit. Each input varies across 25 equally spaced points in its IID range, holding the other inputs at 128 deterministic training backgrounds spaced uniformly by row index. Each response curve is centered by its own grid mean. Blue lines average all 128 centered curves; gray lines show eight evenly spaced backgrounds. These fitted-model diagnostics display average response direction and variation across backgrounds while preserving the disclosed input ranges.",paths+[model_path,sidecar],kind="supplementary",
         panels=[SHORT[j]+" centered response" for j in range(6)])


def seed_variability(results, path):
    fig=plt.figure(figsize=(7.2,6.8));banner(fig,"Supplementary Figure S4 | Algorithm-seed variability")
    gs=fig.add_gridspec(2,2,left=.095,right=.98,top=.88,bottom=.12,wspace=.36,hspace=.60)
    seeds=results["metadata"]["training_seeds"];names=BASELINES+["MGRE"]
    for j,(split,metric) in enumerate([("test","RMSE_mm"),("test","MAE_mm"),("ood","RMSE_mm"),("ood","MAE_mm")]):
        ax=fig.add_subplot(gs[j//2,j%2]);panel(ax,chr(97+j),("IID test" if split=="test" else "Thickness OOD")+" "+metric.split("_")[0],-.16)
        for k,seed in enumerate(seeds):
            vals=[run_for(results,n,seed)["metrics"][split][metric] for n in names]
            ax.plot(np.arange(len(names))+(k-(len(seeds)-1)/2)*.14,vals,"o",ms=3.5,c=PAL[k],
                    label=f"Seed {seed}",alpha=.85)
        ax.set_xticks(range(len(names)),[DISPLAY[n] for n in names],rotation=37,ha="right")
        ax.set_ylabel(metric.split("_")[0]+" (mm)");ax.set_yscale("log");clean(ax)
        if j==0:ax.legend(frameon=False,fontsize=6.5)
    save(fig,"FigS4","seed_variability","Algorithm-seed variability",
         "Seed-level variability for six baselines and MGRE. Algorithm seeds: "+str(seeds)+". (a,b) IID RMSE and MAE. (c,d) Thickness-shift RMSE and MAE. Horizontal offsets distinguish seed markers; vertical coordinates are the recorded metrics. Logarithmic axes accommodate all families. Fits share the same training, validation, calibration and evaluation partitions, so these differences quantify algorithm-seed sensitivity on a fixed dataset. Coincident markers represent identical metric values.",[path],kind="supplementary",
         panels=["a IID RMSE by seed", "b IID MAE by seed", "c OOD RMSE by seed", "d OOD MAE by seed"])


def interval_diagnostics(results, path):
    fig=plt.figure(figsize=(7.2,6.6));banner(fig,"Supplementary Figure S5 | Interval and normalized-error diagnostics")
    gs=fig.add_gridspec(2,2,left=.095,right=.98,top=.83,bottom=.075,wspace=.36,hspace=.50)
    r=run_for(results,"MGRE");q=r["conformal"]["q"]
    for j,split in enumerate(["test","ood"]):
        ax=fig.add_subplot(gs[0,j]);panel(ax,chr(97+j),("IID" if j==0 else "OOD")+" intervals relative to each target",-.16)
        y,p,lo,up=pred_arrays(r,split)
        # Select sample IDs before viewing outcomes, then order only for presentation.
        idorder=np.argsort(r["predictions"][split]["sample_ids"])
        take=idorder[np.linspace(0,len(y)-1,60,dtype=int)];take=take[np.argsort(y[take])]
        xx=np.arange(len(take));hit=(y[take]>=lo[take])&(y[take]<=up[take])
        for mask,c,label in [(hit,COLORS["blue"],"Covered"),(~hit,COLORS["red"],"Missed")]:
            ax.vlines(xx[mask],(lo-y)[take][mask],(up-y)[take][mask],color=c,lw=.75,alpha=.8)
            ax.scatter(xx[mask],(p-y)[take][mask],s=6,color=c,label=label,zorder=4)
        ax.axhline(0,c=COLORS["dark"],ls="--",lw=.9);ax.set_xlabel("60 fixed-ID examples, ordered by reference")
        ax.set_ylabel("Interval bound − reference (mm)")
        if j==0:
            handles,labels=ax.get_legend_handles_labels()
            fig.legend(handles,["(a–b) "+v for v in labels],loc="upper center",bbox_to_anchor=(.52,.923),
                       frameon=False,ncol=2,fontsize=8.8,columnspacing=1.4,handlelength=1.5)
        clean(ax)
    ax=fig.add_subplot(gs[1,0]);panel(ax,"c","Normalized-error empirical CDF",-.16)
    for split,c,n in [("test",COLORS["blue"],"IID test"),("ood",COLORS["orange"],"Thickness OOD")]:
        y,p,_,_=pred_arrays(r,split);sc=np.asarray(r["predictions"][split]["scale_mm"])
        scores=np.sort(np.abs(y-p)/sc);cdf=np.arange(1,len(scores)+1)/len(scores)
        ax.step(scores,cdf,c=c,label=n,where="post")
    ax.axvline(q,c=COLORS["purple"],ls="--",label=f"CAL quantile q={q:.2f}",lw=1)
    ax.axhline(.9,c=COLORS["grey"],ls=":",lw=.8);ax.set_xlabel("Absolute error / validation-trained scale")
    ax.set_ylabel("Cumulative fraction");ax.legend(frameon=False,fontsize=6.5);clean(ax)
    ax=fig.add_subplot(gs[1,1]);panel(ax,"d","Interval width across the target range",-.16)
    for split,c,n in [("test",COLORS["blue"],"IID test"),("ood",COLORS["orange"],"Thickness OOD")]:
        y,p,lo,up=pred_arrays(r,split);ax.scatter(y,up-lo,c=c,s=5,alpha=.20,edgecolors="none",label=n,rasterized=True)
    ax.set_xlabel("Workbook stroke label (mm)");ax.set_ylabel("Interval width (mm)");clean(ax)
    save(fig,"FigS5","interval_diagnostics","Interval and normalized-error diagnostics",
         "First-seed MGRE interval diagnostics with a fixed calibration quantile. (a,b) Sixty rows per split are selected at uniformly spaced positions in lexicographically sorted IDs, then ordered by target for display. Subtracting each reference from the interval bounds places its target at zero; crossing zero indicates coverage. Blue and red distinguish covered and missed examples. These panels illustrate intervals; overall coverage uses all evaluation rows. (c) Complete empirical CDFs of normalized absolute error, with the calibration quantile marked vertically. (d) Complete interval widths against observed stroke labels. IID and shifted-data panels use the same fitted error scale and calibration quantile.",[path],kind="supplementary",
         panels=["a fixed IID interval examples", "b fixed OOD interval examples", "c normalized error CDF", "d interval width response"])


def feature_label_associations(dataset,path):
    _,X,y,_,_,splits,_=data_arrays(dataset)
    fig=plt.figure(figsize=(7.2,7.1));banner(fig,"Supplementary Figure S6 | Input–label associations")
    gs=fig.add_gridspec(3,2,left=.10,right=.98,top=.88,bottom=.075,wspace=.36,hspace=.53)
    for j in range(6):
        ax=fig.add_subplot(gs[j//2,j%2]);panel(ax,chr(97+j),SHORT[j],-.16)
        for sp,c,label in [("train",COLORS["blue"],"Train"),("ood",COLORS["orange"],"Thickness OOD")]:
            mask=splits==sp
            ax.scatter(X[mask,j],y[mask],s=3,alpha=.13,c=c,edgecolors="none",rasterized=True,label=label)
        ax.set_xlabel(LABELS[j]);ax.set_ylabel("Workbook stroke (mm)");clean(ax)
        if j==0:ax.legend(frameon=False,markerscale=3)
    save(fig,"FigS6","input_label_associations","Input–label associations",
         "Six bivariate input-label projections include every training and thickness-shift row. The other five inputs vary simultaneously, so the panels describe marginal associations across the design. The shifted thickness range is separated by an explicit gap; the remaining input ranges are shared.",[path],kind="supplementary",panels=[x+" versus label" for x in SHORT])


def correlation_diagnostics(dataset,path):
    from scipy.stats import spearmanr
    _,X,y,_,_,splits,_=data_arrays(dataset)
    Z=np.column_stack([X,y]);labels=["b","h","L","Rp","Rs","u","Stroke"]
    fig=plt.figure(figsize=(7.2,7.0));banner(fig,"Supplementary Figure S7 | Correlation and input geometry")
    gs=fig.add_gridspec(2,2,left=.09,right=.97,top=.87,bottom=.08,wspace=.47,hspace=.53)
    for k,(mask,method,title) in enumerate([(splits=="train","pearson","Training Pearson correlation"),(splits=="train","spearman","Training rank correlation"),(splits=="ood","pearson","OOD Pearson correlation")]):
        ax=fig.add_subplot(gs[k//2,k%2]);panel(ax,chr(97+k),title,-.15)
        corr=np.corrcoef(Z[mask].T) if method=="pearson" else spearmanr(Z[mask],axis=0).statistic
        im=ax.imshow(corr,cmap="RdBu_r",vmin=-1,vmax=1)
        ax.set_xticks(range(7),labels,rotation=40,ha="right");ax.set_yticks(range(7),labels)
        for i in range(7):
            for j in range(7):
                if abs(corr[i,j])>=.1:ax.text(j,i,f"{corr[i,j]:.2f}",ha="center",va="center",fontsize=6.2,color="white" if abs(corr[i,j])>.58 else COLORS["dark"])
        fig.colorbar(im,ax=ax,fraction=.045,pad=.035)
    ax=fig.add_subplot(gs[1,1]);panel(ax,"d","Thickness–span design coverage",-.15)
    for sp,c,label in [("train",COLORS["blue"],"Train"),("test",COLORS["green"],"IID test"),("ood",COLORS["orange"],"Thickness OOD")]:
        mask=splits==sp;ax.scatter(X[mask,1],X[mask,2],s=4,alpha=.20,c=c,edgecolors="none",rasterized=True,label=label)
    ax.axvspan(9,9.25,fc="#E9EDF0",zorder=0);ax.set_xlabel("Thickness (mm)");ax.set_ylabel("Span (mm)");ax.legend(frameon=False,markerscale=3);clean(ax)
    save(fig,"FigS7","correlation_design","Correlation and input geometry",
         "Correlation and design coverage. (a,b) Pearson and Spearman correlations among the six inputs and stroke label in 4,800 training rows. (c) Pearson correlation in 1,000 thickness-shift rows. Signed color scales are fixed to [-1,1]; annotations identify absolute correlations of at least 0.10. (d) Every training, IID-test and OOD row in thickness-span coordinates. Correlations summarize marginal linear or rank association; the fitted predictor uses the full multivariate input. Legacy diagnostic columns are excluded.",[path],kind="supplementary",panels=["a Pearson train","b Spearman train","c Pearson OOD","d design coverage"])


def ablation_error_distributions(results,path):
    fig=plt.figure(figsize=(7.2,7.5));banner(fig,"Supplementary Figure S8 | Complete ablation error distributions")
    gs=fig.add_gridspec(2,2,left=.10,right=.98,top=.79,bottom=.08,wspace=.38,hspace=.52)
    names=ABLA
    for j,split in enumerate(["test","ood"]):
        ax=fig.add_subplot(gs[0,j]);panel(ax,chr(97+j),("IID" if j==0 else "OOD")+" absolute-error CDF",-.16)
        for k,n in enumerate(names):
            yy,pp,_,_=pred_arrays(run_for(results,n),split);errors=np.sort(np.abs(yy-pp))
            ax.step(errors,np.arange(1,len(errors)+1)/len(errors),where="post",c=PAL[k%len(PAL)],label=DISPLAY[n].replace("\n"," "),lw=1.4,ls="--" if k>3 else "-")
        ax.set_xlabel("Absolute error (mm)");ax.set_ylabel("Cumulative fraction");clean(ax)
    for j,split in enumerate(["test","ood"]):
        ax=fig.add_subplot(gs[1,j]);panel(ax,chr(99+j),("IID" if j==0 else "OOD")+" signed-error quantiles",-.16)
        q=np.array([.05,.25,.5,.75,.95])
        for k,n in enumerate(names):
            yy,pp,_,_=pred_arrays(run_for(results,n),split);quant=np.quantile(pp-yy,q)
            ax.plot(quant[[0,4]],[k,k],c=PAL[k%len(PAL)],lw=1.3)
            ax.plot(quant[[1,3]],[k,k],c=PAL[k%len(PAL)],lw=4)
            ax.scatter(quant[2],k,c=PAL[k%len(PAL)],s=18,zorder=4,edgecolors="white",lw=.5)
        ax.set_yticks(range(len(names)),["MGRE","No mechanics","No prior","No ratios","No gate","No global","No local"]);ax.invert_yaxis();ax.axvline(0,c=COLORS["grey"],ls="--");ax.set_xlabel("Prediction − label (mm)");clean(ax)
    handles,labels=fig.axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc="upper center",bbox_to_anchor=(.52,.935),ncol=3,frameon=False,fontsize=7.1,columnspacing=1,handlelength=2)
    save(fig,"FigS8","ablation_error_distributions","Complete ablation error distributions",
         "First-seed predictions for MGRE and all six point-prediction ablations on identical evaluation rows. (a,b) Complete absolute-error empirical CDFs. (c,d) Signed-error distributions: thin lines span the 5th-95th percentiles, thick lines the interquartile range, and dots the medians. The CDFs include every row; the lower panels summarize empirical quantiles. NoRatioPredictor retains the positive prior and four-dimensional gate while restricting global and expert predictors to the original six columns.",[path],kind="supplementary",panels=["a IID error CDF","b OOD error CDF","c IID signed quantiles","d OOD signed quantiles"])


def binned_coverage(results,dataset,paths):
    fig=plt.figure(figsize=(7.2,6.8));banner(fig,"Supplementary Figure S9 | Coverage across thickness and label bins")
    gs=fig.add_gridspec(2,2,left=.10,right=.98,top=.87,bottom=.08,wspace=.37,hspace=.52)
    byid={r["sample_id"]:r for r in dataset["rows"]};best=results["metadata"]["best_baseline_by_validation"]
    for row,split in enumerate(["test","ood"]):
        for col,feature in enumerate(["thickness_mm","reference_stroke_mm"]):
            ax=fig.add_subplot(gs[row,col]);panel(ax,chr(97+2*row+col),("IID" if row==0 else "OOD")+" coverage by "+("thickness" if col==0 else "label"),-.16)
            r=run_for(results,"MGRE");ids=r["predictions"][split]["sample_ids"];xx=np.array([byid[i][feature] for i in ids]);edges=np.quantile(xx,np.linspace(0,1,6));binid=np.digitize(xx,edges[1:-1]);centers=np.array([xx[binid==k].mean() for k in range(5)])
            for n,c in [("MGRE",COLORS["blue"]),(best,COLORS["orange"]),("ConstantInterval",COLORS["purple"])]:
                yy,pp,lo,up=pred_arrays(run_for(results,n),split);hit=(yy>=lo)&(yy<=up);cover=[];lower=[];upper=[]
                for k in range(5):
                    mask=binid==k;nt=mask.sum();phat=hit[mask].mean();z=1.96;den=1+z*z/nt;mid=(phat+z*z/(2*nt))/den;half=z*np.sqrt(phat*(1-phat)/nt+z*z/(4*nt*nt))/den
                    cover.append(phat);lower.append(phat-(mid-half));upper.append(mid+half-phat)
                ax.errorbar(centers,cover,yerr=[lower,upper],fmt="o-",c=c,ms=3,capsize=2,label="MGRE constant scale" if n=="ConstantInterval" else DISPLAY[n])
            ax.axhline(.9,c=COLORS["grey"],ls="--");ax.set_ylim(0,1.04);ax.set_xlabel("Mean "+("thickness (mm)" if col==0 else "workbook label (mm)"));ax.set_ylabel("Covered fraction");clean(ax)
    handles,labels=fig.axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc="upper center",bbox_to_anchor=(.52,.94),ncol=3,frameon=False,fontsize=7.5)
    save(fig,"FigS9","binned_coverage","Coverage across thickness and label bins",
         "Descriptive interval coverage across thickness and stroke-label bins. Each 1,000-row subset is divided into five equal-count bins (n=200) by observed thickness or stroke. Lines show first-seed empirical coverage of fixed nominal 90% intervals. Whiskers are unadjusted 95% Wilson binomial intervals for each bin; they are pointwise descriptive intervals. (a,b) IID evaluation. (c,d) Thickness-shift evaluation. Label-based bins use observed outcomes. Calibration quantiles and fitted models remain fixed across panels, allowing direct comparison of marginal and binned coverage.",paths,kind="supplementary",panels=["a IID thickness bins","b IID label bins","c OOD thickness bins","d OOD label bins"])


def bootstrap_comparison(results,path):
    fig=plt.figure(figsize=(7.2,6.4));banner(fig,"Supplementary Figure S10 | Paired model-comparison diagnostics")
    gs=fig.add_gridspec(2,2,left=.10,right=.98,top=.87,bottom=.08,wspace=.37,hspace=.52)
    best=results["metadata"]["best_baseline_by_validation"]
    sidecar={"data_origin":"AUTHOR_SUPPLIED_PROVENANCE_PENDING","comparison":"MGRE minus "+best,"interpretation":"Conditional row bootstrap; exploratory reused split.","splits":{}}
    rng=np.random.default_rng(results["paired_bootstrap"]["test"]["seed"])
    for row,split in enumerate(["test","ood"]):
        rr=[r for r in results["seed_results"] if r["model"]=="MGRE"];bb=[r for r in results["seed_results"] if r["model"]==best]
        y=pred_arrays(rr[0],split)[0];pa=np.mean([pred_arrays(r,split)[1] for r in rr],axis=0);pb=np.mean([pred_arrays(r,split)[1] for r in bb],axis=0)
        ea,eb=np.abs(y-pa),np.abs(y-pb);diff=ea-eb
        ax=fig.add_subplot(gs[row,0]);panel(ax,chr(97+2*row),("IID" if row==0 else "OOD")+" paired absolute errors",-.16)
        bound=max(ea.max(),eb.max())*1.02;ax.scatter(eb,ea,c=COLORS["blue"] if row==0 else COLORS["orange"],s=6,alpha=.27,edgecolors="none",rasterized=True)
        ax.plot([0,bound],[0,bound],c=COLORS["grey"],ls="--");ax.set_xlim(0,bound);ax.set_ylim(0,bound);ax.set_xlabel(DISPLAY[best]+" absolute error (mm)");ax.set_ylabel("MGRE absolute error (mm)");clean(ax)
        ax=fig.add_subplot(gs[row,1]);panel(ax,chr(98+2*row),("IID" if row==0 else "OOD")+" conditional bootstrap",-.16)
        record=results["paired_bootstrap"][split]
        idx=rng.integers(0,len(y),size=(record["n_bootstrap"],len(y)))
        delta=diff[idx].mean(axis=1);actual=diff.mean();ci=np.quantile(delta,[.025,.975]);sidecar["splits"][split]={"n_bootstrap":record["n_bootstrap"],"seed":record["seed"],"MAE_delta_mm":float(actual),"MAE_delta_95CI_mm":ci.tolist()}
        np.testing.assert_allclose(actual,record["MAE_delta_mm"],rtol=0,atol=1e-12)
        np.testing.assert_allclose(ci,record["MAE_delta_95CI_mm"],rtol=0,atol=1e-12)
        ax.hist(delta,bins=35,color=COLORS["blue"] if row==0 else COLORS["orange"],alpha=.35,density=True)
        from matplotlib.ticker import MaxNLocator
        ax.xaxis.set_major_locator(MaxNLocator(5))
        ax.axvline(0,c=COLORS["grey"],ls="--");ax.axvline(actual,c=COLORS["dark"])
        for val in ci:ax.axvline(val,c=COLORS["purple"],ls=":")
        ax.set_xlabel("MAE(MGRE) − MAE("+DISPLAY[best]+") (mm)");ax.set_ylabel("Bootstrap density");ax.text(.03,.96,f"Difference {actual:.4f} mm\n95% CI [{ci[0]:.4f}, {ci[1]:.4f}]",transform=ax.transAxes,va="top",fontsize=7,bbox=dict(fc="white",ec="none",alpha=.9));clean(ax)
    sp=OUT/"paired_comparison_diagnostics.json";sp.write_text(json.dumps(sidecar,indent=2),encoding="utf-8")
    save(fig,"FigS10","paired_bootstrap_comparison","Paired model-comparison diagnostics",
         "Paired model-comparison diagnostics use predictions averaged across three training seeds, so errors can differ from averages of seed-level metrics. (a,c) Each dot compares MGRE and the validation-selected baseline on the same row; points below parity favor MGRE. (b,d) Paired row-bootstrap distributions use the recorded resampling count and seed. Solid lines mark full-row MAE differences, dotted lines percentile 95% intervals and dashed lines zero. Intervals describe row-resampling variability conditional on this dataset and the fitted seed-averaged predictors. (a,b) IID rows; (c,d) thickness-shift rows.",[path,sp],kind="supplementary",panels=["a IID paired errors","b IID conditional bootstrap","c OOD paired errors","d OOD conditional bootstrap"])


def main():
    global FIGURE_DISPLAY_MAP_PATH
    p=argparse.ArgumentParser();p.add_argument("--schematics-only",action="store_true")
    p.add_argument("--dataset-only",action="store_true",help="Render definitions and workbook diagnostics before model results exist.")
    p.add_argument("--display-map",type=Path,default=ROOT/'data/figure_display_map.json',
                   help="Optional stable-figure-ID to integrated-manuscript number mapping.")
    args=p.parse_args()
    if args.display_map.exists():
        FIGURE_DISPLAY_MAP_PATH=args.display_map
        FIGURE_DISPLAY_OVERRIDES.update({k:str(v) for k,v in load_json(args.display_map).items()})
    conceptual_geometry()
    if not args.schematics_only:
        dp=ROOT/"data/dataset.json";rp=ROOT/"analysis/results.json"
        dataset=load_json(dp)
        assert dataset["metadata"]["data_origin"]=="AUTHOR_SUPPLIED_PROVENANCE_PENDING"
        dataset_figure(dataset,dp)
        feature_label_associations(dataset,dp)
        correlation_diagnostics(dataset,dp)
        if not args.dataset_only:
            results=load_json(rp)
            assert results["data_origin"]=="AUTHOR_SUPPLIED_PROVENANCE_PENDING"
            assert digest(dp)==results["metadata"]["data_sha256"], "Results do not match current data."
            validation=validate_results(dataset,results)
            (OUT/"figure_input_validation.json").write_text(json.dumps(validation,indent=2),encoding="utf-8")
            model_architecture(dataset,results,[dp,rp])
            point_performance(results,rp)
            ablation_and_learning(results,rp)
            calibration_and_ood(dataset,results,[dp,rp])
            baseline_parities(results,rp)
            regime_diagnostics(results,rp)
            fitted_sensitivity(dataset,results,[dp,rp])
            seed_variability(results,rp)
            interval_diagnostics(results,rp)
            ablation_error_distributions(results,rp)
            binned_coverage(results,dataset,[dp,rp])
            bootstrap_comparison(results,rp)
    MANIFEST.sort(key=lambda f:(f["kind"]!="main",int(f["id"].replace("FigS","").replace("Fig",""))))
    (OUT/"figure_manifest.json").write_text(json.dumps(dict(schema_version="pending-provenance-figure-manifest-v1",
        data_origin="AUTHOR_SUPPLIED_PROVENANCE_PENDING",main_figure_count=sum(f["kind"]=="main" for f in MANIFEST),
        supplementary_figure_count=sum(f["kind"]=="supplementary" for f in MANIFEST),
        main_display_items_planned="6 figures + 2 tables = 8",figures=MANIFEST),indent=2),encoding="utf-8")
    print(json.dumps(dict(figures=len(MANIFEST),directory=str(OUT)),indent=2))


if __name__=="__main__":
    main()


