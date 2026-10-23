"""Four original explanatory scenes: reversal, ice, reconciliation, and payoff.

Animations are illustrative, not simulations or measured experimental results.
The renderer accepts local scene time in seconds and returns an RGB PIL image.
"""
import math

from PIL import ImageDraw

from visual import (
    BG, PANEL, INK, MUTED, COOL, WARM, GOLD, LINE,
    arrow, block, ease, frame, hand, heat_dots, line, note, pill, reveal, text,
)

CUES = {}


def _panel(im, box):
    ImageDraw.Draw(im).rounded_rectangle(box, radius=32, fill=PANEL, outline=LINE, width=2)


def _ice(im, cx, base, width, height):
    """A beveled ice cube whose silhouette can visibly melt."""
    d = ImageDraw.Draw(im)
    x0, x1, y0 = cx-width/2, cx+width/2, base-height
    d.rounded_rectangle((x0, y0, x1, base), radius=min(24, height/3),
                        fill='#83d8df', outline='#c9f1ee', width=3)
    if height > 35:
        d.line((x0+18, y0+18, x1-18, y0+18), fill=INK, width=4)
        d.line((x0+18, y0+20, x0+18, base-20), fill='#b6eeeb', width=3)
    if height > 80:
        line(im, [(cx-20, y0+height*.27), (cx+16, y0+height*.52),
                  (cx-12, y0+height*.78)], '#afe5e5', 4)


def _scene_six(t, duration):
    im = frame(6, t, duration, 'Reverse the direction',
               'Hotter objects.\nSame principle.', 'Conduction works in both directions.')
    p = reveal(t, duration*.12, duration*.19)
    for cx, material, label, speed, width in [
        (292, 'metal', 'METAL', 2.3, 15),
        (788, 'wood', 'WOOD', .55, 6),
    ]:
        _panel(im, (cx-220, 570, cx+220, 1460))
        text(im, label, (cx, 625), 32, MUTED, bold=True)
        block(im, (cx-170, 710, cx+170, 855), material, WARM)
        pill(im, 'HOTTER THAN SKIN', (cx-175, 1150, cx+175, 1206), WARM, 25)
        # A contact cutaway makes conduction explicit: the fingertip begins at
        # the bottom face of the material. Energy travels across that interface.
        hand(im, cx, 962, .67, COOL)
        text(im, 'CONTACT VIEW', (cx, 1080), 25, MUTED, bold=True)
        arrow(im, (cx, 800), (cx, 925), WARM, width, p)
        if p > .95:
            heat_dots(im, (cx, 808), (cx, 915), t, speed, WARM,
                      count=5 if material == 'metal' else 2, radius=6)
        text(im, 'ENERGY IN', (cx, 1330), 29, WARM, bold=True)
        if t > duration*.47:
            text(im, 'Faster transfer' if material == 'metal' else 'Slower transfer',
                 (cx, 1398), 30, INK)
    note(im, 'Conceptual diagram / Do not touch hot surfaces', size=29)
    return im


def _scene_seven(t, duration):
    im = frame(7, t, duration, 'An observable clue',
               'Let the ice\ntell the story.', 'Matching cubes. Different heat transfer.')
    # An opening hold establishes equal cube sizes before their paths diverge.
    melt_start = CUES.get('melt_start', duration*.52)
    melt = ease(max(0, (t-melt_start)/max(.1,duration*.93-melt_start)))
    for cx, material, label, amount, accent in [
        (292, 'metal', 'METAL', melt, COOL),
        (788, 'wood', 'WOOD', melt*.23, GOLD),
    ]:
        _panel(im, (cx-220, 570, cx+220, 1460))
        text(im, label, (cx, 638), 34, MUTED, bold=True)
        block(im, (cx-175, 1050, cx+175, 1210), material, accent)
        # Puddle develops continuously; no elapsed-time or experimental claims.
        d = ImageDraw.Draw(im)
        puddle_width = 120 + amount*190
        d.ellipse((cx-puddle_width/2, 1024-amount*6,
                   cx+puddle_width/2, 1062+amount*15), fill='#3d91a5')
        cube_width = 190 - amount*45
        _ice(im, cx, 1045, cube_width, 235-amount*198)
        transfer = reveal(t, melt_start, duration*.12)
        arrow(im, (cx, 1185), (cx, 1040), WARM,
              12 if material == 'metal' else 5, transfer)
        if transfer > .9:
            heat_dots(im, (cx, 1175), (cx, 1048), t,
                      1.7 if material == 'metal' else .45, WARM, count=3, radius=5)
        text(im, 'ROOM TEMPERATURE', (cx, 1374), 25, MUTED, bold=True)
        if t > duration*.56:
            text(im, 'Heat arrives faster' if material == 'metal' else 'Heat arrives slower',
                 (cx, 1430), 27, COOL if material == 'metal' else GOLD, bold=True)
    note(im, 'Illustration / comparable room-temperature blocks', size=28)
    return im


def _scene_eight(t, duration):
    im = frame(8, t, duration, 'Resolve the puzzle',
               'One metal block.\nTwo exchanges.', 'Starting temperatures set the direction.')
    _panel(im, (90, 555, 990, 1480))
    hand(im, 370, 785, .72, WARM)
    text(im, 'WARM HAND', (665, 704), 35, WARM, bold=True)
    text(im, 'Loses energy', (665, 760), 31, MUTED)
    block(im, (230, 955, 850, 1100), 'metal', COOL)
    text(im, 'METAL', (415, 1027), 34, INK, bold=True)
    pill(im, '22°C', (610, 986, 785, 1066), COOL, 38)
    _ice(im, 370, 1430, 190, 190)
    text(im, 'COLDER ICE', (665, 1312), 35, COOL, bold=True)
    text(im, 'Gains energy', (665, 1368), 31, MUTED)
    top = reveal(t, duration*.09, duration*.16)
    bottom = reveal(t, duration*.43, duration*.16)
    arrow(im, (370, 858), (370, 934), WARM, 12, top)
    arrow(im, (370, 1124), (370, 1215), COOL, 12, bottom)
    if top > .99:
        heat_dots(im, (370, 866), (370, 924), t, 1.5, WARM, count=3, radius=5)
    if bottom > .99:
        heat_dots(im, (370, 1132), (370, 1205), t, 1.5, COOL, count=3, radius=5)
    note(im, 'Heat flows from warmer to cooler.', COOL, size=35)
    return im


def _handle(im, cx, cy, material):
    """An original geometric door-and-handle callback, distinct from a slab."""
    block(im, (cx-130, cy-155, cx+130, cy+155), material,
          COOL if material == 'metal' else GOLD)
    d = ImageDraw.Draw(im)
    color = '#b4c9c8' if material == 'metal' else '#ba8b5c'
    d.rounded_rectangle((cx-54, cy-96, cx+4, cy+95), radius=22, fill=color)
    d.rounded_rectangle((cx-25, cy-28, cx+89, cy+18), radius=18, fill=color)


def _scene_nine(t, duration):
    # Freeze ALL motion for the last 1.5 seconds, leaving a deliberate final hold.
    visual_t = min(t, max(0, duration-1.5))
    im = frame(9, visual_t, duration, 'What your hand reports',
               'You feel\nthe exchange.', 'Same temperature. Different transfer.')
    for cx, material, label, accent in [
        (292, 'metal', 'METAL', COOL), (788, 'wood', 'WOOD', GOLD),
    ]:
        _panel(im, (cx-220, 570, cx+220, 1455))
        text(im, label, (cx, 630), 32, MUTED, bold=True)
        _handle(im, cx, 875, material)
        pill(im, '22°C', (cx-92, 1060, cx+92, 1132), accent, 38)
        # Narrow flow paths connect the warm fingertip to each cooler handle.
        hand(im, cx, 1340, .45, WARM)
        p = reveal(visual_t, duration*.17, duration*.2)
        arrow(im, (cx, 1253), (cx, 1160), WARM,
              13 if material == 'metal' else 5, p)
        if p > .99:
            heat_dots(im, (cx, 1240), (cx, 1170), visual_t,
                      2 if material == 'metal' else .45, WARM,
                      count=4 if material == 'metal' else 2, radius=5)
    note(im, 'Sensation is not a thermometer.', INK, size=36)
    return im


def render(scene: int, t: float, duration: float):
    """Render one of the final four global scene indices."""
    functions = {6: _scene_six, 7: _scene_seven, 8: _scene_eight, 9: _scene_nine}
    if scene not in functions:
        raise ValueError(f'Payoff scenes support indices 6–9; got {scene}')
    return functions[scene](max(0, t), max(.01, duration)).convert('RGB')
