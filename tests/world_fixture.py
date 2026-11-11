"""A small hand-written world (the sunglasses story) in the shape the design stage returns; used by tests and for a smoke render."""
from brainrot.world import spec

DISC = lambda r, h, color, pos, rot=(0, 0, 1.5708), opacity=1.0, glow=0.0: {"shape": "disc", "size": [r, h, r], "pos": list(pos), "rot": list(rot), "color": color, "opacity": opacity, "glow": glow}  # noqa: E731


def world() -> spec.World:
    person = lambda i, x, z=0, shirt="#E59C7C", **kw: {"id": i, "preset": "person", "pos": [x, 0, z], "color": shirt, "color2": "#EBC3A6", **kw}  # noqa: E731
    return spec.World.model_validate({
        "title": "La invención de los lentes de sol", "setting": "un paseo marítimo soleado con un puesto de lentes y, delante, un escenario redondo por cada idea", "hero": "boardwalk",
        "glossary": ["inuit", "cuarzo", "ultravioleta", "Foster Grant"], "motion_words": ["rebot", "atraviesa"],
        "stations": [
            {"id": "boardwalk", "title": "El paseo", "note": "el sol, un puesto y un paseante", "ground": "sand", "nouns": ["sol", "playa", "verano"], "pieces": [
                {"id": "stall", "preset": "house", "pos": [-16, 0, -4], "scale": 2, "color": "#F6C3C3", "color2": "#E59C7C"}, {"id": "base", "preset": "custom", "pos": [0, 0, 0], "parts": [{"shape": "box", "size": [60, 0.4, 14], "pos": [0, 0.2, 0], "color": "#C9A27A"}]}, person("walker", 0, 2, "#5E7BA6", scale=3.5),
                {"id": "sun", "preset": "custom", "pos": [20, 9, -6], "parts": [{"shape": "ball", "size": [3, 3, 3], "pos": [0, 0, 0], "color": "#FFE9A8", "glow": 0.8}]}],
             "actions": [{"name": "sun_glare", "frames": 120, "text": "el sol brilla y lanza un rayo al paseante", "effects": [
                 {"type": "glow", "piece": "sun", "start": 0, "end": 1, "amount": 1.5}, {"type": "ray", "piece": "", "start": 0.1, "end": 0.9, "vec": [20, 9, -4], "vec2": [1, 6.5, 2], "color": "#FFF3B0", "amount": 0.15}]},
                 {"name": "shades_on", "frames": 100, "text": "el paseante se pone lentes", "effects": [{"type": "wear", "piece": "walker", "start": 0, "end": 1, "color": "#2B3140"}]}]},
            {"id": "snow", "title": "Los inuit", "note": "gafas de marfil con ranuras en la nieve", "ground": "snow", "nouns": ["inuit", "nieve", "marfil", "ranuras"], "cutaway": True, "pieces": [
                {"id": "igloo", "preset": "custom", "pos": [-5, 0, -2], "parts": [{"shape": "ball", "size": [2.8, 2, 2.8], "pos": [0, 0.6, 0], "color": "#F8F6F0"}]}, person("hunter", 0, 0.5, "#5E7BA6", scale=2.6)],
             "actions": [{"name": "glare_hits", "frames": 120, "text": "la luz rebota en la nieve y llega a los ojos", "effects": [
                 {"type": "ray", "piece": "", "start": 0, "end": 1, "vec": [4, 0.5, 1], "vec2": [0, 2.5, 0.6], "color": "#FFF3B0", "amount": 0.12}]}]},
            {"id": "quartz", "title": "El cuarzo de China", "note": "un juez con discos de cuarzo ahumado", "ground": "snow", "nouns": ["china", "cuarzo", "jueces", "testigos"], "cutaway": True, "pieces": [
                person("judge", 0, -2, "#3A4256", scale=2.6), {"id": "bench", "preset": "custom", "pos": [0, 0, 0], "parts": [{"shape": "box", "size": [7, 1.8, 1.6], "pos": [0, 0.9, 0], "color": "#A08066"}]}],
             "actions": [{"name": "quartz_on", "frames": 100, "text": "el juez baja los discos de cuarzo sobre los ojos", "effects": [{"type": "wear", "piece": "judge", "start": 0, "end": 1, "color": "#7A6A5C"}]}]},
            {"id": "uv", "title": "Rayos ultravioleta", "note": "rayos violetas hasta que un cristal los frena", "ground": "snow", "nouns": ["ultravioleta", "rayos", "crookes"], "cutaway": True, "pieces": [
                person("reader", 5, 0, "#E59C7C", rot_y=-1.57, scale=2.6),
                {"id": "lens", "preset": "custom", "pos": [1.5, 3, 0], "hidden": True, "parts": [DISC(2.2, 0.15, "#F4E8A0", (0, 0, 0), opacity=0.6)]}],
             "actions": [{"name": "rays_hit", "frames": 110, "text": "rayos violetas cruzan la escena", "effects": [
                 {"type": "ray", "piece": "", "start": 0, "end": 1, "vec": [-6, 6, 0], "vec2": [4.5, 2.6, 0], "color": "#B48CFF", "amount": 0.12}]},
                 {"name": "lens_blocks", "frames": 120, "text": "un cristal aparece y frena los rayos", "effects": [{"type": "appear", "piece": "lens", "start": 0, "end": 0.4}]}]},
            {"id": "market", "title": "El negocio", "note": "una barra de ventas que crece", "ground": "sand", "nouns": ["foster", "celuloide", "negocio", "millones"], "pieces": [
                {"id": "bar", "preset": "custom", "pos": [5, 0, 0], "scale": 3, "parts": [{"shape": "box", "size": [1.6, 1, 1.6], "pos": [0, 0.5, 0], "color": "#F5C542"}]}, person("buyer", -3, 1, "#9BC48F", scale=2.6)],
             "actions": [{"name": "sales_up", "frames": 130, "text": "la barra de ventas crece", "effects": [{"type": "scale", "piece": "bar", "start": 0, "end": 1, "vec": [1, 5, 1]}]}]},
        ]})
