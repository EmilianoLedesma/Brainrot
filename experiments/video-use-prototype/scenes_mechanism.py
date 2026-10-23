"""Narration-paced thermal-conduction diagrams for prototype scenes 04–06."""
import math

from PIL import ImageDraw

from visual import (
    BG, PANEL, INK, MUTED, COOL, WARM, GOLD, LINE,
    frame, text, pill, line, arrow, block, hand, thermometer, heat_dots, note,
    reveal,
)


def _mix(a, b, p):
    p = max(0.0, min(1.0, p))
    aa = tuple(int(a[k:k + 2], 16) for k in (1, 3, 5))
    bb = tuple(int(b[k:k + 2], 16) for k in (1, 3, 5))
    return tuple(round(x + (y - x) * p) for x, y in zip(aa, bb))


def _at(t, duration, start, length=.07):
    return reveal(t, duration * start, max(.3, duration * length))


def _contact(im, t, duration, material):
    """Matched geometry makes the difference in energy spread legible."""
    metal = material == 'metal'
    d = ImageDraw.Draw(im)
    contact = _at(t, duration, .02, .11)
    spread = _at(t, duration, .22, .27)
    cooling = _at(t, duration, .60, .15)
    motion_time = min(t, duration * .85)
    color = _mix(WARM, COOL, cooling * (.87 if metal else .28))

    pill(im, 'GOOD CONDUCTOR' if metal else 'POORER CONDUCTOR',
         (295, 565, 785, 625), COOL if metal else GOLD, size=29)
    text(im, 'YOUR FINGER', (540, 677), 27, MUTED, bold=True)
    hand(im, 540, 824 - 70 * (1 - contact), .92, color=color)
    block(im, (125, 900, 955, 1332), material=material,
          accent=COOL if metal else GOLD)

    # A cutaway model, intentionally qualitative: no invented transfer rates.
    if metal:
        points = [(x, y) for y in (1005, 1125, 1245)
                  for x in (225, 330, 435, 540, 645, 750, 855)]
        for y in (1005, 1125, 1245):
            line(im, [(225, y), (855, y)], '#46616c', 2)
        for x in (225, 330, 435, 540, 645, 750, 855):
            line(im, [(x, 1005), (x, 1245)], '#46616c', 2)
        for x, y in points:
            distance = math.hypot((x - 540) / 1.2, y - 940)
            warmed = max(0, min(1, (spread * 470 - distance) / 100))
            color_node = _mix('#66808a', WARM, warmed * .8)
            d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=color_node)
        if contact > .7:
            # Warmth first appears at the contact, then spreads into the object.
            for r in (26, 17, 8):
                d.ellipse((540 - r, 930 - r, 540 + r, 930 + r),
                          fill=_mix('#293d49', WARM, .9 - r / 50))
        paths = [((535, 956), (240, 1090)),
                 ((545, 956), (840, 1090)),
                 ((540, 962), (540, 1260))]
        if spread > .01:
            for a, b in paths:
                arrow(im, a, b, WARM, width=5, progress=spread)
                heat_dots(im, a, (a[0] + (b[0] - a[0]) * spread,
                                  a[1] + (b[1] - a[1]) * spread),
                          motion_time, speed=1.6, radius=6, count=3)
    else:
        # Wood grain and elongated cells suggest a different material structure.
        for row in range(3):
            y = 988 + row * 112
            for col in range(5):
                x = 166 + col * 153 + (14 if row % 2 else 0)
                d.rounded_rectangle((x, y, x + 120, y + 65), radius=24,
                                    outline='#8c7056', width=2)
        if contact > .7:
            for radius in range(112, 12, -10):
                warm = .57 * (1 - radius / 125) * max(.2, spread)
                d.ellipse((540 - radius, 939 - radius * .25,
                           540 + radius, 939 + radius * .75),
                          fill=_mix('#614d3e', WARM, warm))
            d.ellipse((526, 919, 554, 946), fill=WARM)
        if spread > .01:
            for a, b in [((523, 960), (455, 1005)),
                         ((557, 960), (625, 1005)),
                         ((540, 966), (540, 1040))]:
                arrow(im, a, b, WARM, width=5, progress=spread)
                heat_dots(im, a, b, motion_time, speed=.4, count=1, radius=6)

    text(im, material.upper(), (540, 1380), 35,
         COOL if metal else GOLD, bold=True)
    if _at(t, duration, .39) > .4:
        text(im, 'Energy spreads through the object' if metal
             else 'More warmth stays near the contact',
             (540, 1435), 32, INK, max_width=900)
    if cooling > .15:
        pill(im, 'SKIN COOLS FASTER' if metal else 'SKIN COOLS MORE SLOWLY',
             (227, 1490, 853, 1550), COOL if metal else WARM, size=29)


def _metal(t, duration):
    im = frame(3, t, duration, 'Follow the energy',
               'Metal carries\nheat away.',
               'Fast conduction keeps energy moving from your skin.')
    _contact(im, t, duration, 'metal')
    note(im, 'Heat flows from warmer skin into cooler metal.', size=32)
    return im


def _wood(t, duration):
    im = frame(4, t, duration, 'Now change the material',
               'Wood keeps heat\ncloser to the touch.',
               'The starting temperature can still be exactly the same.')
    _contact(im, t, duration, 'wood')
    note(im, 'Illustrative cutaway · arrows show energy, not cold.', size=30)
    return im


def _distinction(t, duration):
    im = frame(5, t, duration, 'Two different questions',
               'Temperature is\nonly part of the story.',
               'A thermometer and your skin respond differently.')
    d = ImageDraw.Draw(im)
    motion_time = min(t, duration * .85)
    # Deliberately equal card sizes; labels explain rather than imply a scale.
    for box in ((72, 580, 515, 1480), (565, 580, 1008, 1480)):
        d.rounded_rectangle(box, radius=32, fill=PANEL, outline=LINE, width=2)
    text(im, 'TEMPERATURE', (293, 640), 30, COOL, bold=True)
    text(im, 'HEAT FLOW', (786, 640), 30, WARM, bold=True)
    text(im, 'Thermal state', (293, 698), 28, MUTED)
    text(im, 'Skin cooling', (786, 698), 28, MUTED)

    a = _at(t, duration, .08, .16)
    for y, material, accent in ((890, 'metal', COOL), (1160, 'wood', GOLD)):
        block(im, (125, y + 45, 460, y + 135), material, accent)
        text(im, material.upper(), (293, y + 174), 26, MUTED, bold=True)
        if a > .01:
            thermometer(im, 218, y - 30 + 24 * (1 - a), '22°C', COOL)
    if _at(t, duration, .28) > .3:
        pill(im, 'MATCHING READINGS', (104, 1374, 483, 1435), COOL, size=25)

    flow = _at(t, duration, .43, .2)
    if flow > .01:
        for y, material, accent in ((890, 'metal', COOL), (1160, 'wood', GOLD)):
            # The two contact drawings differ only in energy-transfer indication.
            block(im, (618, y + 45, 955, y + 135), material, accent)
            hand(im, 674, y + 11, .45,
                 color=_mix(WARM, COOL, .65 if material == 'metal' else .15))
            destination = (916 if material == 'metal' else 797, y + 87)
            arrow(im, (720, y + 87), destination, WARM,
                  width=8, progress=flow)
            heat_dots(im, (720, y + 87), destination, motion_time,
                      speed=1.3 if material == 'metal' else .4,
                      count=3 if material == 'metal' else 1, radius=6)
            text(im, 'Faster cooling' if material == 'metal' else 'Slower cooling',
                 (786, y + 174), 28, INK)
    if _at(t, duration, .70) > .3:
        pill(im, 'DIFFERENT SENSATIONS', (588, 1374, 985, 1435), WARM, size=25)
    note(im, 'Touch responds to changes in your skin.', size=34)
    text(im, 'Diagram illustrates the distinction; no measured rates shown.',
         (540, 1635), 24, MUTED, max_width=920)
    return im


def render(scene: int, t: float, duration: float):
    """Return a full 1080 × 1920 RGB frame for the requested scene."""
    return {3: _metal, 4: _wood, 5: _distinction}[scene](t, duration).convert('RGB')
