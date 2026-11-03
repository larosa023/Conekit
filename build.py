#!/usr/bin/env python3
"""
Conekit - modern skins for VLC media player (VLC 3.x "skins2" format).

Run:  python build.py
Out:  dist/Conekit-<Variant>.vlt   (load in VLC: Tools > Preferences > Interface > Use custom skin)
      preview/<variant>.png        (screenshot-style preview for the README)

Everything (icons, backgrounds, layout, theme.xml) is generated from the
PALETTES and layout constants below, so a new color variant is just a new dict.
Requires: Python 3.8+, Pillow  (pip install pillow)
"""
import os
import shutil
import zipfile
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(ROOT, "src", "fonts")
DIST = os.path.join(ROOT, "dist")
PREVIEW = os.path.join(ROOT, "preview")
S = 4  # supersampling factor for anti-aliased icons

PALETTES = {
    "Dark": {
        "title_bg": "#101114", "video_bg": "#050506", "bar_bg": "#16181C",
        "border": "#24272D", "panel_bg": "#121417", "row_alt": "#16181C",
        "fg": "#E8EAED", "muted": "#9AA0AA", "hover": "#25282F", "press": "#2E323A",
        "track": "#30343C", "accent": "#FF7A1A", "accent_hover": "#FF9040",
        "on_accent": "#FFFFFF", "close_hover": "#C42B1C", "sel": "#2A2E36",
    },
    "Light": {
        "title_bg": "#F2F3F5", "video_bg": "#0C0C0E", "bar_bg": "#FFFFFF",
        "border": "#E2E4E8", "panel_bg": "#FAFAFB", "row_alt": "#F2F3F5",
        "fg": "#1B1D21", "muted": "#5F6570", "hover": "#EDEFF2", "press": "#E2E5E9",
        "track": "#D6D9DE", "accent": "#F26A00", "accent_hover": "#FF8121",
        "on_accent": "#FFFFFF", "close_hover": "#C42B1C", "sel": "#E5E8EC",
    },
}

# ---------------------------------------------------------------- drawing ---

def hx(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


class Canvas:
    """Draws at S-times resolution in 1x coordinates, then downsamples."""

    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.img = Image.new("RGBA", (w * S, h * S), hx(bg))
        self.d = ImageDraw.Draw(self.img)

    def _p(self, pts):
        return [(x * S, y * S) for x, y in pts]

    def rrect(self, box, r, fill=None, outline=None, width=1.0):
        x0, y0, x1, y1 = box
        self.d.rounded_rectangle((x0 * S, y0 * S, x1 * S - 1, y1 * S - 1), radius=r * S,
                                 fill=hx(fill) if fill else None,
                                 outline=hx(outline) if outline else None,
                                 width=int(width * S))

    def rect(self, box, fill):
        x0, y0, x1, y1 = box
        self.d.rectangle((x0 * S, y0 * S, x1 * S - 1, y1 * S - 1), fill=hx(fill))

    def circle(self, cx, cy, r, fill=None, outline=None, width=1.0):
        self.d.ellipse(((cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S),
                       fill=hx(fill) if fill else None,
                       outline=hx(outline) if outline else None, width=int(width * S))

    def poly(self, pts, fill):
        self.d.polygon(self._p(pts), fill=hx(fill))

    def line(self, pts, color, width=1.6):
        self.d.line(self._p(pts), fill=hx(color), width=int(width * S), joint="curve")
        for x, y in (pts[0], pts[-1]):  # round caps
            self.circle(x, y, width / 2, fill=color)

    def arc(self, cx, cy, r, start, end, color, width=1.6):
        self.d.arc(((cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S),
                   start, end, fill=hx(color), width=int(width * S))

    def save(self, path):
        self.img.resize((self.w, self.h), Image.LANCZOS).convert("RGB").save(path, optimize=True)


# Icons: f(canvas, cx, cy, color). Drawn inside a ~16px box.
def ic_play(c, x, y, col):
    c.poly([(x - 4.5, y - 7), (x - 4.5, y + 7), (x + 7, y)], col)

def ic_pause(c, x, y, col):
    c.rrect((x - 6, y - 7, x - 2, y + 7), 1, fill=col)
    c.rrect((x + 2, y - 7, x + 6, y + 7), 1, fill=col)

def ic_prev(c, x, y, col):
    c.rrect((x - 7, y - 6, x - 5, y + 6), 1, fill=col)
    c.poly([(x + 6, y - 6), (x + 6, y + 6), (x - 4, y)], col)

def ic_next(c, x, y, col):
    c.rrect((x + 5, y - 6, x + 7, y + 6), 1, fill=col)
    c.poly([(x - 6, y - 6), (x - 6, y + 6), (x + 4, y)], col)

def ic_stop(c, x, y, col):
    c.rrect((x - 5.5, y - 5.5, x + 5.5, y + 5.5), 2, fill=col)

def ic_open(c, x, y, col):
    c.line([(x - 8, y + 6), (x - 8, y - 6), (x - 3, y - 6), (x - 1, y - 4),
            (x + 7, y - 4), (x + 7, y + 6), (x - 8, y + 6)], col, 1.5)

def _speaker(c, x, y, col):
    c.poly([(x - 8, y - 3), (x - 5, y - 3), (x - 1, y - 7), (x - 1, y + 7),
            (x - 5, y + 3), (x - 8, y + 3)], col)

def ic_volume(c, x, y, col):
    _speaker(c, x, y, col)
    c.arc(x - 1, y, 4.5, -50, 50, col, 1.5)
    c.arc(x - 1, y, 8, -50, 50, col, 1.5)

def ic_muted(c, x, y, col):
    _speaker(c, x, y, col)
    c.line([(x + 2.5, y - 3.5), (x + 8.5, y + 3.5)], col, 1.5)
    c.line([(x + 8.5, y - 3.5), (x + 2.5, y + 3.5)], col, 1.5)

def ic_list(c, x, y, col):
    for dy in (-5, 0, 5):
        c.line([(x - 7, y + dy), (x + 7, y + dy)], col, 1.6)

def ic_more(c, x, y, col):
    for dx in (-6, 0, 6):
        c.circle(x + dx, y, 1.7, fill=col)

def ic_fullscreen(c, x, y, col):
    k, a = 7, 4
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        c.line([(x + sx * k, y + sy * (k - a)), (x + sx * k, y + sy * k), (x + sx * (k - a), y + sy * k)], col, 1.6)

def ic_unfullscreen(c, x, y, col):
    k, a = 7, 4
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        p = (x + sx * (k - a), y + sy * (k - a))
        c.line([(x + sx * (k - a), y + sy * k), p, (x + sx * k, y + sy * (k - a))], col, 1.6)

def ic_min(c, x, y, col):
    c.line([(x - 5, y), (x + 5, y)], col, 1.1)

def ic_close(c, x, y, col):
    c.line([(x - 5, y - 5), (x + 5, y + 5)], col, 1.1)
    c.line([(x + 5, y - 5), (x - 5, y + 5)], col, 1.1)

def ic_pin(c, x, y, col):
    c.line([(x - 6, y - 6), (x + 6, y - 6)], col, 1.3)
    c.line([(x, y + 6), (x, y - 2)], col, 1.3)
    c.line([(x - 3.5, y + 1.5), (x, y - 2), (x + 3.5, y + 1.5)], col, 1.3)

def ic_add(c, x, y, col):
    c.line([(x - 6, y), (x + 6, y)], col, 1.6)
    c.line([(x, y - 6), (x, y + 6)], col, 1.6)

def ic_remove(c, x, y, col):
    c.line([(x - 6, y), (x + 6, y)], col, 1.6)

def ic_shuffle(c, x, y, col):
    c.line([(x - 7, y + 5), (x - 3, y + 5), (x + 3, y - 5), (x + 6, y - 5)], col, 1.4)
    c.line([(x - 7, y - 5), (x - 3, y - 5), (x + 3, y + 5), (x + 6, y + 5)], col, 1.4)
    c.poly([(x + 5, y - 8), (x + 8.5, y - 5), (x + 5, y - 2)], col)
    c.poly([(x + 5, y + 2), (x + 8.5, y + 5), (x + 5, y + 8)], col)

def ic_loop(c, x, y, col):
    c.line([(x + 4, y + 5), (x - 4, y + 5), (x - 7, y + 2), (x - 7, y - 2), (x - 4, y - 5), (x + 3, y - 5)], col, 1.4)
    c.line([(x + 7, y - 1), (x + 7, y + 2), (x + 4, y + 5)], col, 1.4)
    c.poly([(x + 2, y - 8.5), (x + 6, y - 5), (x + 2, y - 1.5)], col)


def button_states(path_base, w, h, bg, P, icon, icon_col=None, style="soft", out=None):
    """Writes <base>_up/_over/_down.png. style: soft (rounded hover), close, accent (round play)."""
    icon_col = icon_col or P["muted"]
    names = {}
    for st in ("up", "over", "down"):
        c = Canvas(w, h, bg)
        cx, cy = w / 2, h / 2
        col = icon_col
        if style == "accent":
            fill = {"up": P["accent"], "over": P["accent_hover"], "down": P["accent"]}[st]
            r = min(w, h) / 2 - (1 if st == "down" else 0)
            c.circle(cx, cy, r, fill=fill)
            col = P["on_accent"]
            icon(c, cx + (1 if icon is ic_play else 0), cy, col)
        elif style == "close":
            if st != "up":
                c.rect((0, 0, w, h), P["close_hover"] if st == "over" else "#A82418")
                col = "#FFFFFF"
            else:
                col = P["fg"]
            icon(c, cx, cy, col)
        else:
            if st == "over":
                c.rrect((2, 2, w - 2, h - 2), 7, fill=P["hover"])
            elif st == "down":
                c.rrect((2, 2, w - 2, h - 2), 7, fill=P["press"])
            if st != "up" and icon_col == P["muted"]:
                col = P["fg"]
            icon(c, cx, cy, col)
        fn = f"{path_base}_{st}.png"
        c.save(os.path.join(out, fn))
        names[st] = fn
    return names


# ----------------------------------------------------------------- layout ---
# Main window
W, H, TB, BAR = 720, 460, 36, 84
# Docked playlist sidebar width; resize-handle thickness
SB = 320
EDGE = 5
VERSION = open(os.path.join(ROOT, "VERSION")).read().strip()
# Fullscreen controller
FW, FH = 640, 80


class Theme:
    def __init__(self, variant, P, out):
        self.variant, self.P, self.out = variant, P, out
        self.bitmaps = []          # (id, file)
        self.windows = []          # xml strings
        self.preview_ops = {}      # window id -> list of ops

    # bitmap helpers --------------------------------------------------------
    def bmp(self, bid, fn):
        self.bitmaps.append((bid, fn))
        return bid

    def solid(self, bid, w, h, color, top_border=None, grip=False):
        c = Canvas(w, h, color)
        if top_border:
            c.rect((0, 0, w, 1), top_border)
        c.save(os.path.join(self.out, f"{bid}.png"))
        return self.bmp(bid, f"{bid}.png")

    def button(self, bid, w, h, bg, icon, style="soft", icon_col=None):
        n = button_states(bid, w, h, bg, self.P, icon, icon_col=icon_col, style=style, out=self.out)
        return {st: self.bmp(f"{bid}_{st}", fn) for st, fn in n.items()}

    def knob(self, bid, d, bg, color):
        c = Canvas(d, d, bg)
        c.circle(d / 2, d / 2, d / 2 - 0.5, fill=color)
        c.save(os.path.join(self.out, f"{bid}.png"))
        return self.bmp(bid, f"{bid}.png")

    def track(self, bid, w, h, bg, color):
        c = Canvas(w, h, bg)
        c.rect((0, 0, w, h), color)
        c.save(os.path.join(self.out, f"{bid}.png"))
        return self.bmp(bid, f"{bid}.png")

    def grip(self, bid, bg):
        c = Canvas(12, 12, bg)
        for (x, y) in ((9, 3), (6, 6), (9, 6), (3, 9), (6, 9), (9, 9)):
            c.circle(x, y, 0.9, fill=self.P["track"])
        c.save(os.path.join(self.out, f"{bid}.png"))
        return self.bmp(bid, f"{bid}.png")

    def logo(self, bid, bg):
        c = Canvas(18, 18, bg)
        a = self.P["accent"]
        c.poly([(9, 1.5), (14, 14), (4, 14)], a)
        c.rect((5.5, 6.5, 12.5, 8), "#FFFFFF")
        c.rect((4.2, 10.5, 13.8, 12), "#FFFFFF")
        c.rrect((2, 14, 16, 16.5), 1, fill=a)
        c.save(os.path.join(self.out, f"{bid}.png"))
        return self.bmp(bid, f"{bid}.png")

    # element emitters (xml + preview op) -----------------------------------
    @staticmethod
    def _anchor(a):
        return {"tl": "lefttop", "tr": "righttop", "bl": "leftbottom", "br": "rightbottom"}[a]

    def image(self, ops, xml, x, y, bid, lt="tl", rb="tl", action=None, resize="scale"):
        act = f' action="{action}"' if action else ""
        xml.append(f'<Image x="{x}" y="{y}" image="{bid}" resize="{resize}" '
                   f'lefttop="{self._anchor(lt)}" rightbottom="{self._anchor(rb)}"{act}/>')
        ops.append(("img", x, y, bid))

    def btn(self, ops, xml, x, y, b, action, tip, lt="tl", rb=None):
        rb = rb or lt
        xml.append(f'<Button x="{x}" y="{y}" up="{b["up"]}" over="{b["over"]}" down="{b["down"]}" '
                   f'action="{action}" tooltiptext="{tip}" lefttop="{self._anchor(lt)}" rightbottom="{self._anchor(rb)}"/>')
        ops.append(("img", x, y, b["up"]))

    def check(self, ops, xml, x, y, b1, b2, state, a1, a2, t1, t2, lt="tl", preview_state=False):
        xml.append(f'<Checkbox x="{x}" y="{y}" state="{state}" '
                   f'up1="{b1["up"]}" over1="{b1["over"]}" down1="{b1["down"]}" '
                   f'up2="{b2["up"]}" over2="{b2["over"]}" down2="{b2["down"]}" '
                   f'action1="{a1}" action2="{a2}" tooltiptext1="{t1}" tooltiptext2="{t2}" '
                   f'lefttop="{self._anchor(lt)}" rightbottom="{self._anchor(lt)}"/>')
        ops.append(("img", x, y, (b2 if preview_state else b1)["up"]))

    def text(self, ops, xml, x, y, w, text, font, color, lt="tl", rb=None, align="left", sample=""):
        rb = rb or lt
        xml.append(f'<Text x="{x}" y="{y}" width="{w}" text="{text}" font="{font}" color="{color}" '
                   f'alignment="{align}" scrolling="none" lefttop="{self._anchor(lt)}" rightbottom="{self._anchor(rb)}"/>')
        ops.append(("text", x, y, w, sample, font, color, align))

    def slider(self, ops, xml, x, y, length, knob, value, tip, lt, rb, preview_pos=0.35, ky=2):
        xml.append(f'<Slider x="{x}" y="{y}" points="(0,{ky}),({length},{ky})" thickness="14" '
                   f'up="{knob}" over="{knob}_o" down="{knob}_o" value="{value}" tooltiptext="{tip}" '
                   f'lefttop="{self._anchor(lt)}" rightbottom="{self._anchor(rb)}"/>')
        ops.append(("knob", x + length * preview_pos, y + ky, knob))

    # windows ---------------------------------------------------------------
    def build(self):
        P = self.P
        tb, bar, panel = P["title_bg"], P["bar_bg"], P["panel_bg"]

        # shared bitmaps
        b_min = self.button("win_min", 44, 36, tb, ic_min, style="soft", icon_col=P["fg"])
        b_close = self.button("win_close", 44, 36, tb, ic_close, style="close")
        b_pin = self.button("win_pin", 44, 36, tb, ic_pin, icon_col=P["muted"])
        b_pin_on = self.button("win_pin_on", 44, 36, tb, ic_pin, icon_col=P["accent"])
        b_play = self.button("play", 40, 40, bar, ic_play, style="accent")
        b_pause = self.button("pause", 40, 40, bar, ic_pause, style="accent")
        b_prev = self.button("prev", 32, 32, bar, ic_prev)
        b_next = self.button("next", 32, 32, bar, ic_next)
        b_stop = self.button("stop", 32, 32, bar, ic_stop)
        b_open = self.button("open", 32, 32, bar, ic_open)
        b_vol = self.button("vol", 32, 32, bar, ic_volume)
        b_mute = self.button("mute", 32, 32, bar, ic_muted, icon_col=P["accent"])
        b_list = self.button("list", 32, 32, bar, ic_list)
        b_list_on = self.button("list_on", 32, 32, bar, ic_list, icon_col=P["accent"])
        b_more = self.button("more", 32, 32, bar, ic_more)
        b_fs = self.button("fs", 32, 32, bar, ic_fullscreen)
        b_unfs = self.button("unfs", 32, 32, bar, ic_unfullscreen)
        b_add = self.button("pl_add", 32, 32, panel, ic_add)
        b_del = self.button("pl_del", 32, 32, panel, ic_remove)
        b_shuf = self.button("shuf", 32, 32, panel, ic_shuffle)
        b_shuf_on = self.button("shuf_on", 32, 32, panel, ic_shuffle, icon_col=P["accent"])
        b_loop = self.button("loop", 32, 32, panel, ic_loop)
        b_loop_on = self.button("loop_on", 32, 32, panel, ic_loop, icon_col=P["accent"])
        self.knob("knob", 14, bar, P["accent"]); self.knob("knob_o", 14, bar, P["accent_hover"])
        self.knob("vknob", 12, bar, P["fg"]); self.knob("vknob_o", 12, bar, P["accent"])
        self.track("fsc_track", FW - 32, 4, bar, P["track"])
        # volume track: VLC's slider spans 0-200%, so mark 100% in the middle
        vt = Canvas(80, 10, bar); vt.rect((0, 3, 80, 7), P["track"]); vt.rect((39, 0, 41, 10), P["muted"])
        vt.save(os.path.join(self.out, "vol_track.png")); self.bmp("vol_track", "vol_track.png")
        grip = self.grip("grip", bar)
        gc = Canvas(16, 16, bar)
        for (gx, gy) in ((13, 7), (10, 10), (13, 10), (7, 13), (10, 13), (13, 13)):
            gc.circle(gx, gy, 0.9, fill=P["track"])
        gc.save(os.path.join(self.out, "grip_big.png")); self.bmp("grip_big", "grip_big.png")
        logo = self.logo("logo", tb)

        # ---- main window: two layouts (compact, and with the playlist docked on the right) ----
        thumb = Canvas(6, 40, panel); thumb.rrect((0, 0, 6, 40), 3, fill=P["track"])
        thumb.save(os.path.join(self.out, "pl_thumb.png")); self.bmp("pl_thumb", "pl_thumb.png")
        layouts = []
        for lid, w, with_pl in (("main_compact", W, False), ("main_full", W + SB, True)):
            ops, x = [], []
            vw = w - (SB if with_pl else EDGE)
            self.solid(f"{lid}_title", w, TB, tb)
            self.solid(f"{lid}_body", vw, H - TB - BAR, P["video_bg"])
            self.solid(f"{lid}_bar", w, BAR, bar, top_border=P["border"])
            self.track(f"{lid}_seek", w - 32, 4, bar, P["track"])
            self.image(ops, x, 0, 0, f"{lid}_title", "tl", "tr", action="move")
            self.image(ops, x, 14, 9, logo, "tl", "tl", action="move")
            self.text(ops, x, 40, 10, w - 40 - 132 - 8, "$N", "title", P["fg"], "tl", "tr",
                      sample="Big Buck Bunny (2008) 1080p.mkv")
            self.check(ops, x, w - 132, 0, b_pin, b_pin_on, "vlc.isOnTop", "vlc.onTop()", "vlc.onTop()",
                       "Keep on top", "Stop keeping on top", lt="tr")
            self.btn(ops, x, w - 88, 0, b_min, "vlc.minimize()", "Minimize", "tr")
            self.btn(ops, x, w - 44, 0, b_close, "vlc.quit()", "Close VLC", "tr")
            self.image(ops, x, 0, TB, f"{lid}_body", "tl", "br", action="move")
            x.append(f'<Video x="0" y="{TB}" width="{vw}" height="{H - TB - BAR}" autoresize="false" '
                     f'lefttop="lefttop" rightbottom="rightbottom"/>')
            ops.append(("video", 0, TB, vw, H - TB - BAR))
            if with_pl:
                sx = w - SB
                self.solid("side_body", SB, H - TB - BAR, panel)
                self.solid("side_line", 1, H - TB - BAR, P["border"])
                self.image(ops, x, sx, TB, "side_body", "tr", "br")
                self.image(ops, x, sx, TB, "side_line", "tr", "br")
                self.text(ops, x, sx + 16, TB + 14, 100, "Playlist", "title", P["fg"], "tr",
                          sample="Playlist")
                hy = TB + 4
                self.btn(ops, x, w - 148, hy, b_add, "playlist.add()", "Add files", "tr")
                self.btn(ops, x, w - 112, hy, b_del, "playlist.del()", "Remove selected", "tr")
                self.check(ops, x, w - 76, hy, b_shuf, b_shuf_on, "playlist.isRandom",
                           "playlist.setRandom(true)", "playlist.setRandom(false)", "Shuffle", "Shuffle off", lt="tr")
                self.check(ops, x, w - 40, hy, b_loop, b_loop_on, "playlist.isLoop",
                           "playlist.setLoop(true)", "playlist.setLoop(false)", "Repeat all", "Repeat off",
                           lt="tr", preview_state=True)
                ty = TB + 44
                th = H - BAR - ty - 8
                x.append(
                    f'<Playtree id="playtree" x="{sx + 8}" y="{ty}" width="{SB - 30}" height="{th}" '
                    f'font="list" flat="true" fgcolor="{P["fg"]}" playcolor="{P["accent"]}" '
                    f'selcolor="{P["sel"]}" bgcolor1="{panel}" bgcolor2="{P["row_alt"]}" '
                    f'lefttop="righttop" rightbottom="rightbottom">'
                    f'<Slider value="playtree.slider" x="{w - 16}" y="{ty}" points="(3,{th - 20}),(3,20)" '
                    f'up="pl_thumb" over="pl_thumb" down="pl_thumb" thickness="8" '
                    f'lefttop="righttop" rightbottom="rightbottom"/></Playtree>')
                ops.append(("playtree", sx + 8, ty, SB - 30, th))
            by = H - BAR
            self.image(ops, x, 0, by, f"{lid}_bar", "bl", "br")
            self.image(ops, x, 16, by + 14, f"{lid}_seek", "bl", "br")
            self.slider(ops, x, 16, by + 14, w - 32, "knob", "time", "$T / $D", "bl", "br")
            row = by + 28
            self.check(ops, x, 16, row, b_play, b_pause, "vlc.isPlaying", "vlc.play()", "vlc.pause()",
                       "Play", "Pause", lt="bl", preview_state=True)
            self.btn(ops, x, 64, row + 4, b_prev, "playlist.previous()", "Previous", "bl")
            self.btn(ops, x, 100, row + 4, b_next, "playlist.next()", "Next", "bl")
            self.btn(ops, x, 136, row + 4, b_stop, "vlc.stop()", "Stop", "bl")
            self.btn(ops, x, 172, row + 4, b_open, "dialogs.fileSimple()", "Open file", "bl")
            self.text(ops, x, 216, row + 13, 150, "$T  /  $D", "time", P["muted"], "bl",
                      sample="0:03:28  /  0:09:56")
            self.btn(ops, x, w - 48, row + 4, b_fs, "vlc.fullscreen()", "Fullscreen", "br")
            self.btn(ops, x, w - 84, row + 4, b_more, "conekit_menu.show()", "Menu", "br")
            if with_pl:
                self.check(ops, x, w - 120, row + 4, b_list_on, b_list, "main_compact.isActive",
                           "main_window.setLayout(main_compact)", "main_window.setLayout(main_full)",
                           "Hide playlist", "Show playlist", lt="br")
            else:
                self.check(ops, x, w - 120, row + 4, b_list, b_list_on, "main_full.isActive",
                           "main_window.setLayout(main_full)", "main_window.setLayout(main_compact)",
                           "Show playlist", "Hide playlist", lt="br")
            vx = w - 132 - 80
            self.text(ops, x, vx - 82, row + 13, 40, "$V%", "time", P["muted"], "br", align="right",
                      sample="  70%")
            self.image(ops, x, vx, row + 15, "vol_track", "br", "br")
            self.slider(ops, x, vx, row + 18, 80, "vknob", "volume", "Volume $V% (middle mark = 100%)", "br", "br", preview_pos=0.5)
            self.check(ops, x, vx - 40, row + 4, b_vol, b_mute, "vlc.isMute", "vlc.mute()", "vlc.mute()",
                       "Mute", "Unmute", lt="br")
            # resize handles: right edge, bottom edge, bottom-right corner (all skins2 supports)
            body_col = panel if with_pl else P["video_bg"]
            self.solid(f"{lid}_edge_body", EDGE, H - TB - BAR, body_col)
            self.solid(f"{lid}_edge_bar", EDGE, BAR - 1, bar)
            self.solid(f"{lid}_edge_bottom", w, EDGE, bar)
            self.image(ops, x, w - EDGE, TB, f"{lid}_edge_body", "tr", "br", action="resizeE")
            self.image(ops, x, w - EDGE, H - BAR + 1, f"{lid}_edge_bar", "br", "br", action="resizeE")
            self.image(ops, x, 0, H - EDGE, f"{lid}_edge_bottom", "bl", "br", action="resizeS")
            self.image(ops, x, w - 16, H - 16, "grip_big", "br", "br", action="resizeSE")
            minw = 640 + (SB if with_pl else 0)
            layouts.append((lid, w, H, minw, 300, x))
            self.preview_ops["main" if not with_pl else "full"] = (w, H, ops)
        self.window("main_window", 120, 100, True, layouts)

        # custom "more" menu: the useful stuff, with clear names
        self.popup = [("Open file...", "dialogs.fileSimple()"), ("Open folder...", "dialogs.directory()"),
                      ("Open network stream...", "dialogs.net()"), ("Open disc...", "dialogs.disc()"), None,
                      ("Audio (tracks, device)...", "dialogs.audioPopup()"),
                      ("Video (aspect ratio, crop)...", "dialogs.videoPopup()"),
                      ("Subtitles and more...", "dialogs.miscPopup()"), None,
                      ("Playback speed: faster", "vlc.faster()"), ("Playback speed: slower", "vlc.slower()"),
                      ("Take snapshot", "vlc.snapshot()"), ("Media information", "dialogs.fileInfo()"), None,
                      ("Preferences...", "dialogs.prefs()"), ("Change skin...", "dialogs.changeSkin()"),
                      ("Full VLC menu", "dialogs.popup()"), None, ("Quit", "vlc.quit()"), None,
                      (f"Conekit {VERSION}  (run Conekit-Updater to update)", "none")]

        # ---- fullscreen controller (shown by VLC when in fullscreen) ----
        ops, x = [], []
        self.solid("fsc_bg", FW, FH, bar, top_border=P["border"])
        self.image(ops, x, 0, 0, "fsc_bg", "tl", "tl", action="move")
        self.image(ops, x, 16, 14, "fsc_track", "tl", "tl")
        self.slider(ops, x, 16, 14, FW - 32, "knob", "time", "$T / $D", "tl", "tl")
        fr = 28
        self.check(ops, x, 16, fr, b_play, b_pause, "vlc.isPlaying", "vlc.play()", "vlc.pause()", "Play", "Pause")
        self.btn(ops, x, 64, fr + 4, b_prev, "playlist.previous()", "Previous")
        self.btn(ops, x, 100, fr + 4, b_next, "playlist.next()", "Next")
        self.text(ops, x, 144, fr + 13, 160, "$T  /  $D", "time", P["muted"], sample="0:03:28  /  0:09:56")
        fvx = FW - 52 - 80
        self.check(ops, x, fvx - 40, fr + 4, b_vol, b_mute, "vlc.isMute", "vlc.mute()", "vlc.mute()", "Mute", "Unmute")
        self.image(ops, x, fvx, fr + 15, "vol_track")
        self.slider(ops, x, fvx, fr + 18, 80, "vknob", "volume", "Volume $V%", "tl", "tl", preview_pos=0.7)
        self.btn(ops, x, FW - 48, fr + 4, b_unfs, "vlc.fullscreen()", "Exit fullscreen")
        self.window("fullscreenController", 0, 0, False, [("fsc_layout", FW, FH, FW, FH, x)])
        self.preview_ops["fsc"] = (FW, FH, ops)

    def window(self, wid, wx, wy, visible, layouts):
        """layouts: list of (layout_id, w, h, minw, minh, body). Same w/h as min = fixed size."""
        parts = []
        for lid, w, h, minw, minh, body in layouts:
            fixed = (minw == w and minh == h)
            maxw = str(w) if fixed else "-1"
            maxh = str(h) if fixed else "-1"
            inner = "\n      ".join(body)
            parts.append(f'    <Layout id="{lid}" width="{w}" height="{h}" minwidth="{minw}" minheight="{minh}" '
                         f'maxwidth="{maxw}" maxheight="{maxh}">\n      {inner}\n    </Layout>')
        self.windows.append(
            f'  <Window id="{wid}" x="{wx}" y="{wy}" visible="{str(visible).lower()}" '
            f'dragdrop="true" playondrop="true">\n' + "\n".join(parts) + '\n  </Window>')

    def popup_xml(self):
        items = []
        for it in self.popup:
            items.append('    <MenuSeparator/>' if it is None else f'    <MenuItem label="{it[0]}" action="{it[1]}"/>')
        return '  <PopupMenu id="conekit_menu">\n' + "\n".join(items) + '\n  </PopupMenu>'

    def xml(self):
        bm = "\n".join(f'  <Bitmap id="{i}" file="{f}" alphacolor="#FF00FF"/>' for i, f in self.bitmaps)
        return f'''<?xml version="1.0" encoding="utf-8" standalone="no"?>
<!DOCTYPE Theme PUBLIC "-//VideoLAN//DTD VLC Skins V2.0//EN" "skin.dtd">
<!-- Conekit {self.variant} - generated by build.py. Edit build.py, not this file. -->
<Theme version="2.0" tooltipfont="list" magnet="12" alpha="255" movealpha="235">
  <ThemeInfo name="Conekit {self.variant} {VERSION}" author="Conekit contributors" email="" webpage="https://github.com/larosa023/Conekit"/>
  <Font id="title" file="fonts/Inter-SemiBold.ttf" size="12"/>
  <Font id="time" file="fonts/Inter-Regular.ttf" size="12"/>
  <Font id="list" file="fonts/Inter-Regular.ttf" size="12"/>
{bm}
{self.popup_xml()}
{chr(10).join(self.windows)}
</Theme>
'''

    # preview ---------------------------------------------------------------
    def render(self, key, scale=1):
        w, h, ops = self.preview_ops[key]
        img = Image.new("RGB", (w, h), hx(self.P["bar_bg"])[:3])
        d = ImageDraw.Draw(img)
        fonts = {"title": ImageFont.truetype(os.path.join(FONT_DIR, "Inter-SemiBold.ttf"), 12),
                 "time": ImageFont.truetype(os.path.join(FONT_DIR, "Inter-Regular.ttf"), 12),
                 "list": ImageFont.truetype(os.path.join(FONT_DIR, "Inter-Regular.ttf"), 12)}
        for op in ops:
            if op[0] == "img":
                _, x, y, bid = op
                img.paste(Image.open(os.path.join(self.out, f"{bid}.png")), (int(x), int(y)))
            elif op[0] == "knob":
                _, cx, cy, bid = op
                k = Image.open(os.path.join(self.out, f"{bid}.png"))
                if bid == "knob":  # show played portion in preview
                    pass
                img.paste(k, (int(cx - k.width / 2), int(cy - k.height / 2)))
            elif op[0] == "text":
                _, x, y, tw, sample, font, color, align = op
                d.text((x, y - 1), sample, font=fonts[font], fill=hx(color)[:3])
            elif op[0] == "video":
                _, x, y, vw, vh = op
                frame = Image.new("RGB", (vw, vh))
                fd = ImageDraw.Draw(frame)
                for i in range(vh):  # dusk-sky gradient as a stand-in video frame
                    t = i / vh
                    c = (int(40 + 150 * t), int(60 + 70 * t), int(110 - 40 * t))
                    fd.line([(0, i), (vw, i)], fill=c)
                fd.ellipse((vw * 0.62, vh * 0.42, vw * 0.62 + 70, vh * 0.42 + 70), fill=(255, 196, 120))
                fd.polygon([(0, vh), (0, vh * 0.72), (vw * 0.3, vh * 0.58), (vw * 0.55, vh * 0.75),
                            (vw * 0.8, vh * 0.6), (vw, vh * 0.7), (vw, vh)], fill=(28, 26, 38))
                img.paste(frame, (x, y))
            elif op[0] == "playtree":
                _, x, y, pw, ph = op
                items = ["Big Buck Bunny (2008) 1080p.mkv", "Sintel - Open Movie.mp4",
                         "Tears of Steel.mkv", "Lo-fi Mix Vol. 3.mp3", "Cosmos Laundromat.webm"]
                for i, it in enumerate(items):
                    ry = y + i * 24
                    bgc = self.P["panel_bg"] if i % 2 == 0 else self.P["row_alt"]
                    d.rectangle((x, ry, x + pw, ry + 23), fill=hx(bgc)[:3])
                    col = self.P["accent"] if i == 0 else self.P["fg"]
                    d.text((x + 10, ry + 5), it, font=fonts["list"], fill=hx(col)[:3])
        # seek progress fill in preview (VLC shows track + knob)
        return img


def preview_sheet(theme, path):
    full = theme.render("full")
    pad = 40
    sheet = Image.new("RGB", (full.width + pad * 2, full.height + pad * 2),
                      (225, 228, 233) if theme.variant == "Light" else (32, 34, 40))
    sheet.paste(full, (pad, pad))
    sheet.save(path, optimize=True)


def build_variant(variant, P):
    out = os.path.join(ROOT, "build", variant)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(os.path.join(out, "fonts"))
    for f in ("Inter-Regular.ttf", "Inter-SemiBold.ttf", "OFL-Inter.txt"):
        shutil.copy(os.path.join(FONT_DIR, f), os.path.join(out, "fonts", f))
    t = Theme(variant, P, out)
    t.build()
    with open(os.path.join(out, "theme.xml"), "w", encoding="utf-8") as fh:
        fh.write(t.xml())
    os.makedirs(DIST, exist_ok=True)
    vlt = os.path.join(DIST, f"Conekit-{variant}.vlt")
    with zipfile.ZipFile(vlt, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _, files in os.walk(out):
            for f in sorted(files):
                full = os.path.join(base, f)
                z.write(full, os.path.relpath(full, out))
    os.makedirs(PREVIEW, exist_ok=True)
    preview_sheet(t, os.path.join(PREVIEW, f"{variant.lower()}.png"))
    t.render("main").save(os.path.join(PREVIEW, f"{variant.lower()}-compact.png"))
    t.render("fsc").save(os.path.join(PREVIEW, f"{variant.lower()}-fullscreen-bar.png"))
    print(f"built {vlt}  ({len(t.bitmaps)} bitmaps)")


if __name__ == "__main__":
    for name, pal in PALETTES.items():
        build_variant(name, pal)
