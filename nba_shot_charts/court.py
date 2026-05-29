import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Circle, Rectangle
from matplotlib.lines import Line2D


def draw_court(ax=None, color="black", lw=2):
    """
    Draw an NBA half-court in the NBA API coordinate system.

    NBA API coordinates: LOC_X and LOC_Y are in tenths of feet.
    Origin (0, 0) is at the basket. LOC_X is negative to the left.
    LOC_Y is positive toward half-court. The shot data is already
    filtered to one half (LOC_Y >= -50 approximately).

    Court is drawn from x=-250 to x=250, y=-47.5 to y=422.5
    (the full half-court in tenths of feet with a small baseline margin).
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 9))

    # --- Outer boundary ---
    ax.add_patch(Rectangle((-250, -47.5), 500, 470, linewidth=lw, edgecolor=color, fill=False))

    # --- Paint / lane (16 ft wide = 160 units, 19 ft deep = 190 units) ---
    ax.add_patch(Rectangle((-80, -47.5), 160, 190, linewidth=lw, edgecolor=color, fill=False))

    # --- Free-throw line (at y = 142.5, 15 ft from baseline) ---
    ax.add_line(Line2D([-80, 80], [142.5, 142.5], linewidth=lw, color=color))

    # --- Free-throw circle (radius 6 ft = 60 units, centered at (0, 142.5)) ---
    ax.add_patch(Arc((0, 142.5), 120, 120, theta1=0, theta2=180, linewidth=lw, color=color))
    ax.add_patch(Arc((0, 142.5), 120, 120, theta1=180, theta2=360, linewidth=lw, color=color, linestyle="dashed"))

    # --- Restricted area arc (radius 4 ft = 40 units) ---
    ax.add_patch(Arc((0, 0), 80, 80, theta1=0, theta2=180, linewidth=lw, color=color))

    # --- Backboard (6 ft wide = 60 units, at y = -7.5) ---
    ax.add_line(Line2D([-30, 30], [-7.5, -7.5], linewidth=lw * 2, color=color))

    # --- Rim (radius 9 inches ≈ 7.5 units) ---
    ax.add_patch(Circle((0, 0), 7.5, linewidth=lw, edgecolor=color, fill=False))

    # --- Three-point arc ---
    # Corner three straights: from baseline to y=90 (corner three depth)
    ax.add_line(Line2D([-220, -220], [-47.5, 90], linewidth=lw, color=color))
    ax.add_line(Line2D([220, 220], [-47.5, 90], linewidth=lw, color=color))
    # Arc: radius 23.75 ft = 237.5 units, centered at basket (0, 0)
    # The arc starts where the corner lines end (approx theta1=22°, theta2=158°)
    ax.add_patch(Arc((0, 0), 475, 475, theta1=22, theta2=158, linewidth=lw, color=color))

    # --- Half-court line and circle ---
    ax.add_line(Line2D([-250, 250], [422.5, 422.5], linewidth=lw, color=color))
    ax.add_patch(Arc((0, 422.5), 120, 120, theta1=180, theta2=360, linewidth=lw, color=color))

    ax.set_xlim(-260, 260)
    ax.set_ylim(-60, 440)
    ax.set_aspect("equal")
    ax.axis("off")

    return ax
