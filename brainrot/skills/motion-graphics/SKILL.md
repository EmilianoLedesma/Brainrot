---
name: motion-graphics
description: Choose at most one focus-grabbing on-screen device per scene of a narrated short video, using only facts stated in the narration.
---

# Motion-graphics scene design

You art-direct an animated vertical short. The narration is already written and
voiced. For each numbered scene, decide whether one on-screen device would help a
viewer follow or remember that scene, and fill in its text. Return one beat per scene.

## Devices

- `stat`: a big number that counts up. `big` is a number or short figure taken from
  the scene ("21", "2019", "70%"); `title` says what it counts (max 5 words).
- `compare`: two bars side by side. `items` holds exactly two short labels (max 3
  words each); `values` holds two integers from 5 to 100 showing which is larger.
  Use only when the narration states or clearly implies which is larger or faster.
  The bars show no numbers, so do not invent any.
- `checklist`: three or four short rows (`items`, max 4 words each). `highlight` is
  the zero-based row the narration supports; the others are crossed out. Use -1 to
  show every row as a plain list item.
- `steps`: three or four short stages (`items`, max 4 words each) shown in order
  with arrows, for a process or chain of cause and effect.
- `stamp`: a short label slammed on screen (`title`, max 3 words), for a verdict
  such as a hypothesis, a myth or a turning point.
- `alert`: a notification-style card (`title`, max 8 words) restating the scene's
  key sentence. Use it rarely, at most once per video.
- `none`: no device; the scene keeps only its keyword punches and captions.

## Rules

- Use only facts, names and numbers that appear in the narration. Never invent a
  statistic, quote or comparison the narration does not make.
- Be selective. Roughly one scene in three should be `none`, and never use the same
  device in two scenes in a row. Devices exist to focus attention, not to decorate.
- `cue` is two to four consecutive words copied exactly from that scene's narration,
  at the moment the device should appear. Copy the words as written; ignore
  punctuation and capitalization differences.
- Keep text short enough to read in about a second. Match the narration's language.
- Fill every field. Use an empty string, an empty list or -1 for fields a device
  does not use.
