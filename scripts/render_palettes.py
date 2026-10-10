#!/usr/bin/env python3
"""Render a visual palette card for every Konsole *.colorscheme in ../konsole.

For each scheme it writes docs/palettes/<name>.svg: a fake Konsole window
showing everyday output (ls, git, grep, ...) in the scheme's real colors,
plus a legend explaining which slot paints what. The cards are written into
README.md between the palettes:start/end markers (README.md is created if
missing).

Usage:
    python3 scripts/render_palettes.py          # write SVGs + README section
    python3 scripts/render_palettes.py --print  # also preview in a truecolor terminal
"""

import configparser
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMES = ROOT / "konsole"
OUT = ROOT / "docs" / "palettes"
README = ROOT / "README.md"
START, END = "<!-- palettes:start -->", "<!-- palettes:end -->"

NAMES = ["Black", "Red", "Green", "Yellow", "Blue", "Magenta", "Cyan", "White"]

# slot -> (short sample for the SVG legend, long description for the README)
USAGE = {
    "Color0": ("black text on bars", "Black text drawn on top of colored highlights (status bars, fzf/tmux selections)"),
    "Color0Intense": ("autosuggestions, comments", "Dimmed gray: zsh autosuggestions, comments, hints"),
    "Color1": ("errors, untracked, − lines", "Errors, `git status` untracked/modified files, `git diff` removed lines"),
    "Color1Intense": ("archives, grep matches", "**Bold red**: archives in `ls` (`.tar.gz`, `.zip`), `grep` matches, `origin/…` in `git log`"),
    "Color2": ("staged files, + lines", "`git status` staged files, `git diff` added lines, `grep` line numbers"),
    "Color2Intense": ("executables, user@host", "**Bold green**: executables in `ls`, local branch in `git log`, `user@host` in prompts"),
    "Color3": ("commit hashes, warnings", "Commit hashes in `git log`, warnings"),
    "Color3Intense": ("devices (/dev/sda)", "**Bold yellow**: block/char devices in `ls /dev`"),
    "Color4": ("plain blue text (rare)", "Non-bold blue — rare in the shell, shows up in syntax highlighting / TUI apps"),
    "Color4Intense": ("folders, prompt path", "**Bold blue**: 📁 folders in `ls`, the current path in most prompts"),
    "Color5": ("grep filenames, git branch", "Filenames in `grep -r` output, git branch in many prompts"),
    "Color5Intense": ("images, media, sockets", "**Bold magenta**: images/media files and sockets in `ls`"),
    "Color6": ("diff @@ hunks, grep : sep", "`@@` hunk headers in `git diff`, `:` separators in `grep`"),
    "Color6Intense": ("symlinks, HEAD ->", "**Bold cyan**: symlinks in `ls`, `HEAD ->` in `git log`"),
    "Color7": ("light gray in TUI apps", "Light gray used by TUI apps that ask for \"white\" (htop, mc)"),
    "Color7Intense": ("bold white text", "Bright white for bold white text"),
    "Foreground": ("regular text & files", "Everything uncolored: command output, regular files, what you type"),
    "ForegroundIntense": ("bold text, diff headers", "**Bold** uncolored text: `diff --git` headers, man page headings"),
    "Background": ("the terminal canvas", "The terminal canvas"),
    "BackgroundIntense": ("intense bg (rarely seen)", "Default background with the intense attribute — rarely visible"),
}

LEGEND_ROWS = [(f"Color{i}", f"Color{i}Intense") for i in range(8)] + [
    ("Foreground", "ForegroundIntense"),
    ("Background", "BackgroundIntense"),
]


def label(slot):
    if slot.startswith("Color"):
        i = int(slot[5])
        return ("Bright " if slot.endswith("Intense") else "") + NAMES[i]
    return slot.replace("Intense", " Intense")


def load(path):
    cp = configparser.ConfigParser(interpolation=None)
    cp.optionxform = str
    cp.read(path)
    colors = {
        sec: "#%02X%02X%02X" % tuple(int(c) for c in cp[sec]["Color"].split(","))
        for sec in cp.sections()
        if "Color" in cp[sec]
    }
    name = cp.get("General", "Description", fallback=path.stem)
    return name, colors


# --- the fake terminal session ---------------------------------------------
# Each line is a list of (slot, text[, bold[, bg_slot]]) segments. Konsole draws
# bold text in the Intense variant of the base color, which is why ls folders
# (bold blue) come out as Color4Intense rather than Color4.

FG, FGI = "Foreground", "ForegroundIntense"


def prompt(cmd, *extra):
    return [("Color2Intense", "john@fedora", True), (FG, ":"), ("Color4Intense", "~/konsole-configs", True),
            ("Color5", " (main)"), (FG, " $ " + cmd), *extra]


SESSION = [
    prompt("ls -l"),
    [(FG, "drwxr-xr-x  "), ("Color4Intense", "src", True), (FG, "/")],
    [(FG, "-rwxr-xr-x  "), ("Color2Intense", "build.sh", True)],
    [(FG, "lrwxrwxrwx  "), ("Color6Intense", "latest", True), (FG, " -> "), ("Color2Intense", "build.sh", True)],
    [(FG, "-rw-r--r--  "), ("Color5Intense", "logo.png", True)],
    [(FG, "-rw-r--r--  "), ("Color1Intense", "release.tar.gz", True)],
    [(FG, "-rw-r--r--  README.md")],
    prompt("git log --oneline -2"),
    [("Color3", "5ae30d3 ("), ("Color6Intense", "HEAD -> ", True), ("Color2Intense", "main", True),
     ("Color3", ", "), ("Color1Intense", "origin/main", True), ("Color3", ")"), (FG, " Add bl1nk color scheme")],
    [("Color3", "ff41695"), (FG, " Add README and initial color schemes")],
    prompt("git status -s"),
    [("Color2", "A "), (FG, " konsole/new.colorscheme")],
    [(FG, " "), ("Color1", "M"), (FG, " README.md")],
    [("Color1", "??"), (FG, " notes.txt")],
    prompt("git diff"),
    [(FGI, "diff --git a/README.md b/README.md", True)],
    [("Color6", "@@ -1,3 +1,3 @@"), (FG, " # Konsole Configs")],
    [("Color1", "-Custom color schemes")],
    [("Color2", "+Custom color schemes and profiles")],
    prompt("grep -rn color ."),
    [("Color5", "./README.md"), ("Color6", ":"), ("Color2", "3"), ("Color6", ":"), (FG, "Custom "),
     ("Color1Intense", "color", True), (FG, " schemes and profiles")],
    prompt("git p", ("Color0Intense", "ush origin main"), ("__cursor__", "")),
]

FONT = "Hack, 'Hack Nerd Font Mono', 'DejaVu Sans Mono', Menlo, Consolas, monospace"
W, PAD, LINE_H = 920, 16, 20


def tspans(segments, colors):
    out = []
    for seg in segments:
        slot, text = seg[0], seg[1]
        bold = len(seg) > 2 and seg[2]
        if slot == "__cursor__":
            slot, text = FG, "█"
        weight = ' font-weight="bold"' if bold else ""
        out.append(f'<tspan fill="{colors[slot]}"{weight}>{escape(text)}</tspan>')
    return "".join(out)


def render_svg(name, colors):
    bg, fg = colors["Background"], colors["Foreground"]
    title_h = 32
    term_h = PAD * 2 + LINE_H * len(SESSION)
    legend_top = title_h + term_h + 18
    row_h = 40
    legend_h = 34 + row_h * len(LEGEND_ROWS) + 12
    H = legend_top + legend_h + 10

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         f'font-family="{FONT}">']
    # window frame
    s.append(f'<rect width="{W}" height="{H}" rx="10" fill="#2b2b2b"/>')
    s.append(f'<rect width="{W}" height="{title_h}" rx="10" fill="#3c3c3c"/>')
    s.append(f'<rect y="{title_h - 10}" width="{W}" height="10" fill="#3c3c3c"/>')
    # KDE-style window buttons: minimize, maximize, close
    icon = 'stroke="#ddd" stroke-width="1.5" fill="none" stroke-linecap="round"'
    cx = W - 86
    s.append(f'<line x1="{cx - 5}" y1="19" x2="{cx + 5}" y2="19" {icon}/>')
    cx += 30
    s.append(f'<rect x="{cx - 5}" y="11" width="10" height="10" {icon}/>')
    cx += 30
    s.append(f'<path d="M{cx - 5} 11 L{cx + 5} 21 M{cx + 5} 11 L{cx - 5} 21" {icon}/>')
    s.append(f'<text x="16" y="21" font-size="13" fill="#ddd">{escape(name)} — Konsole</text>')

    # terminal body
    s.append(f'<rect y="{title_h}" width="{W}" height="{term_h}" fill="{bg}"/>')
    for n, line in enumerate(SESSION):
        y = title_h + PAD + LINE_H * n + 14
        s.append(f'<text x="{PAD}" y="{y}" font-size="14" xml:space="preserve">{tspans(line, colors)}</text>')

    # legend
    s.append(f'<rect x="0" y="{legend_top - 8}" width="{W}" height="{legend_h + 8}" fill="{bg}"/>')
    col_w = W // 2
    for c, head in enumerate(["NORMAL", "BOLD / INTENSE"]):
        s.append(f'<text x="{c * col_w + PAD}" y="{legend_top + 14}" font-size="11" letter-spacing="2" '
                 f'fill="{fg}" opacity="0.6">{head}</text>')
    for r, pair in enumerate(LEGEND_ROWS):
        y = legend_top + 34 + r * row_h
        for c, slot in enumerate(pair):
            if slot not in colors:
                continue
            x = c * col_w + PAD
            color = colors[slot]
            s.append(f'<rect x="{x}" y="{y}" width="28" height="28" rx="5" fill="{color}" '
                     f'stroke="{fg}" stroke-opacity="0.35"/>')
            s.append(f'<text x="{x + 38}" y="{y + 12}" font-size="12" fill="{fg}">{escape(label(slot))}</text>')
            s.append(f'<text x="{x + 38}" y="{y + 26}" font-size="10" fill="{fg}" opacity="0.55">'
                     f'{slot} {color}</text>')
            sample = USAGE[slot][0]
            sx = x + 210
            if slot == "Color0":
                # black is only legible on a highlight, which is how it's used
                s.append(f'<rect x="{sx - 4}" y="{y + 4}" width="{len(sample) * 7.9 + 8:.0f}" height="20" '
                         f'rx="3" fill="{colors["Color7"]}"/>')
                text_fill = color
            elif slot.startswith("Background"):
                s.append(f'<rect x="{sx - 4}" y="{y + 4}" width="{len(sample) * 7.9 + 8:.0f}" height="20" '
                         f'rx="3" fill="{color}" stroke="{fg}" stroke-opacity="0.35"/>')
                text_fill = fg
            else:
                text_fill = color
            weight = ' font-weight="bold"' if slot.endswith("Intense") else ""
            s.append(f'<text x="{sx}" y="{y + 19}" font-size="13" fill="{text_fill}"{weight}>{escape(sample)}</text>')
    s.append("</svg>")
    return "\n".join(s) + "\n"


def swatch(hex_color):
    path = OUT / "swatches" / f"{hex_color[1:].lower()}.svg"
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20">'
                    f'<rect width="20" height="20" rx="4" fill="{hex_color}" stroke="#888"/></svg>\n')
    return path.relative_to(ROOT).as_posix()


def readme_section(schemes):
    md = [START, "", "<!-- Generated by scripts/render_palettes.py — do not edit by hand. -->", "",
          "## Palettes", ""]
    for path, name, colors, svg in schemes:
        md += [f"### {name}", "", f"`konsole/{path.name}`", "", f"![{name} palette]({svg})", "",
               "<details><summary>Color table</summary>", "",
               "| | Slot | Hex | Where you'll see it |", "|---|---|---|---|"]
        for pair in LEGEND_ROWS:
            for slot in pair:
                if slot in colors:
                    md.append(f"| ![]({swatch(colors[slot])}) | {label(slot)} (`{slot}`) | "
                              f"`{colors[slot]}` | {USAGE[slot][1]} |")
        md += ["", "</details>", ""]
    md += ["Regenerate after editing a scheme: `python3 scripts/render_palettes.py`", "", END]
    return "\n".join(md)


def print_terminal(name, colors):
    def ansi(hex_color, bold=False):
        r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
        return f"\033[{'1' if bold else '22'};38;2;{r};{g};{b}m"

    r, g, b = (int(colors["Background"][i:i + 2], 16) for i in (1, 3, 5))
    bgc = f"\033[48;2;{r};{g};{b}m"
    print(f"\n{name}")
    for line in SESSION:
        out = "".join(ansi(colors[seg[0]] if seg[0] != "__cursor__" else colors["Foreground"],
                           len(seg) > 2 and seg[2]) + seg[1] for seg in line if seg[0] != "__cursor__")
        print(f"{bgc}  {out}\033[K\033[0m")


def main():
    (OUT / "swatches").mkdir(parents=True, exist_ok=True)
    schemes = []
    for path in sorted(SCHEMES.glob("*.colorscheme")):
        name, colors = load(path)
        svg = OUT / f"{path.stem}.svg"
        svg.write_text(render_svg(name, colors))
        schemes.append((path, name, colors, svg.relative_to(ROOT).as_posix()))
        print(f"wrote {svg.relative_to(ROOT)}")
        if "--print" in sys.argv:
            print_terminal(name, colors)

    readme = README.read_text() if README.exists() else ""
    section = readme_section(schemes)
    if START in readme and END in readme:
        head, rest = readme.split(START, 1)
        readme = head + section + rest.split(END, 1)[1]
    elif readme.strip():
        readme = readme.rstrip("\n") + "\n\n" + section + "\n"
    else:
        readme = section + "\n"
    README.write_text(readme)
    print("updated README.md")


if __name__ == "__main__":
    main()
