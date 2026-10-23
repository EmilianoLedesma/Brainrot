"""Opening illustrations for the original metal-and-wood explainer.

All geometry is drawn locally. Temperatures are illustrative values, and moving
energy dots indicate direction only; they are not a numerical heat simulation.
"""

import math

from PIL import Image, ImageDraw

from visual import (
    BG, COOL, GOLD, INK, LINE, MUTED, PANEL, WARM, arrow, block,
    ease, frame, hand, heat_dots, line, note, pill, text,
)


def _spoon(im, cx, cy, material):
    """Draw a spoon as one continuous silhouette, with material-specific detail."""
    d = ImageDraw.Draw(im)
    metal = material == 'metal'
    base = '#829fa8' if metal else '#b88955'
    light = '#c3d5d4' if metal else '#dab178'
    shadow = '#435e6a' if metal else '#745138'
    d.rounded_rectangle((cx-29, cy+48, cx+29, cy+388), radius=28,
                        fill=base, outline=light, width=3)
    d.ellipse((cx-102, cy-142, cx+102, cy+124), fill=base,
              outline=light, width=4)
    d.ellipse((cx-76, cy-116, cx+76, cy+87), fill=shadow)
    if metal:
        d.arc((cx-65, cy-102, cx+66, cy+75), 112, 258,
              fill='#e3e8df', width=9)
        d.line((cx-12, cy+144, cx-12, cy+346), fill=light, width=5)
    else:
        for j in range(4):
            yy = cy-74+j*37
            pts = [(cx-51+k*10.2, yy+9*math.sin(k*.43+j*.5))
                   for k in range(11)]
            d.line(pts, fill='#b58a5c', width=3)
        d.line((cx+8, cy+153, cx+8, cy+342), fill=light, width=3)


def _opening(t, duration):
    u = t / max(duration, .001)
    im = frame(0, t, duration, 'The everyday mystery',
               'Why does metal\nfeel colder?',
               'Same room. Two very different sensations.')
    d = ImageDraw.Draw(im)
    entering = ease(u/.075)
    for cx, material, accent, offset in (
        (305, 'metal', COOL, -1), (775, 'wood', GOLD, 1)
    ):
        shift = offset*90*(1-entering)
        x = cx+shift
        d.rounded_rectangle((x-201, 594, x+201, 1455), radius=35,
                            fill=PANEL, outline=LINE, width=2)
        text(im, material.upper(), (x, 655), 32, accent, bold=True)
        _spoon(im, x, 965, material)
        # Two separate touches follow the narrated comparison.
        start = .06 if material == 'metal' else .18
        touch = ease((u-start)/.075)
        lift = ease((u-.45)/.07)
        if u > start and lift < 1:
            hand(im, x, 639+158*touch-235*lift, scale=.66)
        if u > start+.065:
            label = 'FEELS COLDER' if material == 'metal' else 'LESS COLD'
            pill(im, label, (x-166, 1365, x+166, 1427), accent, 26)
    # The equal temperature is the reveal, rather than an opening assumption.
    if u > .48:
        r = ease((u-.48)/.075)
        d.rounded_rectangle((152, 723, 928, 797), radius=36,
                            fill=BG, outline=COOL, width=2)
        text(im, 'SAME ROOM  /  SAME TEMPERATURE',
             (540, 760+12*(1-r)), 28, COOL, bold=True, max_width=720)
    if u > .77:
        note(im, 'What is your hand actually measuring?', INK, size=37)
    else:
        note(im, 'Touch each one. Notice the difference.', size=34)
    return im


def _temperature_meter(im, x, y, progress):
    """A schematic thermometer whose level rises with a scene reveal."""
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((x-22, y-160, x+22, y+93), radius=22,
                        fill=BG, outline=COOL, width=3)
    d.ellipse((x-39, y+56, x+39, y+134), fill=COOL)
    level = y+74-210*progress
    d.rounded_rectangle((x-8, level, x+8, y+87), radius=8, fill=COOL)
    for j in range(6):
        yy = y-127+j*33
        line(im, [(x+31, yy), (x+49 if j % 2 == 0 else x+42, yy)],
             MUTED, 2)


def _thermometers(t, duration):
    u = t / max(duration, .001)
    im = frame(1, t, duration, 'Measure before touching',
               'Both can read\n22°C.',
               'Leave the objects in the same room long enough.')
    d = ImageDraw.Draw(im)
    entry = ease(u/.09)
    fill = ease((u-.08)/.16)
    for cx, material, accent, side in (
        (305, 'metal', COOL, -1), (775, 'wood', GOLD, 1)
    ):
        x = cx+side*80*(1-entry)
        d.rounded_rectangle((x-201, 595, x+201, 1417), radius=35,
                            fill=PANEL, outline=LINE, width=2)
        text(im, material.upper(), (x, 665), 33, accent, bold=True)
        block(im, (x-158, 1140, x+158, 1318), material, accent)
        # Moving the gauge toward the object connects reading to material.
        _temperature_meter(im, x-48, 992-42*(1-entry), fill)
        if u > .24:
            text(im, '22°C', (x+34, 861), 57, INK, bold=True)
        text(im, 'TEMPERATURE', (x, 1366), 24, MUTED, bold=True)
    if u > .33:
        d.ellipse((492, 942, 588, 1038), fill=BG, outline=COOL, width=2)
        text(im, '=', (540, 988), 62, COOL, bold=True)
    if u > .58:
        pill(im, 'TEMPERATURE ≠ TRANSFER SPEED',
             (154, 1418, 926, 1480), WARM, 30)
        note(im, 'A temperature reading is only part of the story.', size=32)
    else:
        note(im, 'Illustrative readings before either object is touched.', size=30)
    return im


def _energy_direction(t, duration):
    u = t / max(duration, .001)
    im = frame(2, t, duration, 'Follow the energy',
               'Warm skin.\nCooler objects.',
               'Energy moves from warmer to cooler.')
    d = ImageDraw.Draw(im)
    entry = ease(u/.085)
    hand(im, 540, 790-72*(1-entry), scale=1.03)
    pill(im, 'SKIN ≈ 32°C', (365, 580, 715, 642), WARM, 31)
    if u > .08:
        text(im, 'WARMER', (782, 793), 28, WARM, bold=True)
        line(im, [(665, 795), (704, 795)], WARM, 2)
    for cx, material, accent in ((290, 'metal', COOL), (790, 'wood', GOLD)):
        block(im, (cx-170, 1114+60*(1-entry), cx+170, 1307+60*(1-entry)),
              material, accent)
        text(im, material.upper(), (cx, 1220+60*(1-entry)), 32,
             INK, bold=True)
        pill(im, '22°C', (cx-98, 1340, cx+98, 1402), COOL, 33)
    transfer = ease((u-.27)/.13)
    if transfer > 0:
        for start, end in (((462, 919), (290, 1088)),
                           ((618, 919), (790, 1088))):
            arrow(im, start, end, WARM, 7, transfer)
            if transfer > .9:
                heat_dots(im, start, end, t, speed=.75,
                          color=GOLD, count=4, radius=8)
        text(im, 'ENERGY', (540, 1018), 27, WARM, bold=True)
    if u > .64:
        pill(im, 'SAME DIRECTION. DIFFERENT SPEED.',
             (120, 1418, 960, 1480), COOL, 31)
    note(im, 'Temperatures are examples; arrows show direction.', size=30)
    return im


def render(scene: int, t: float, duration: float) -> Image.Image:
    """Render one opening scene at local time ``t`` in seconds."""
    scenes = {0: _opening, 1: _thermometers, 2: _energy_direction}
    if scene not in scenes:
        raise ValueError(f'Opening scenes only support indices 0, 1 and 2: {scene}')
    return scenes[scene](max(0., t), max(.001, duration)).convert('RGB')
