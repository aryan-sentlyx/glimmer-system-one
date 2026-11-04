# SPEC: Glimmer System One, "The line does not wait"

GOAL:    The viewer believes that a decision model answers a production line in one forward pass, with calibrated numbers, while a reasoning model is still writing. They open the demo URL.
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps
TIME:    96 s x 30 = 2880 frames. No music. The voice of Aryan (ElevenLabs clone, added last). Sound effects on actions.
LOOK:    Two worlds.
         World L (the line): ground #e9e6e0 flat, 1.5% paper grain; ink #1c1a17; belt #2a2826 with #3a3733 rollers.
         World P (the product): ground #1c1a17 (the demo's ink-950); ink #ece9e4; the demo's own greys.
         Accent: amber #f0b429, the demo's "signal". It may appear on: the timer once it passes 1 s, the Run button, the head's curve, the mark, one word per title.
         Display: IBM Plex Sans 700, 88 px (8% of height), tracking -0.02em. Body: IBM Plex Sans 500, 36 px. Numbers: IBM Plex Mono 500. Labels: IBM Plex Sans Condensed 600, 24 px, uppercase, tracking 0.14em.
         Light: flat. Shadow on bottles and cards: 0 6px 18px rgba(0,0,0,0.18). No glow, no gradient, no vignette.
OBJECTS: The belt: a dark band 160 px tall with a 24 px lighter top edge, rollers (circles, 40 px) every 220 px under it, moving stripes on the band.
         The bottles: the four real MVTec photos, 180 px circles with a 4 px #1c1a17 ring and a shadow; they travel on the belt.
         The inspection gate: a dark post with a lamp; the lamp is grey when idle, amber when thinking, green #5fd38a when a verdict lands.
         The presenter: a stick figure, 6 px ink strokes, round caps; the head is the headshot cut-out, 150 px wide in world L, 110 px in world P. Head bob 3 px at 2 Hz while speaking; pose changes through anticipation (4 frames back) then settle (`back.out(1.6)`).
         The token wall: IBM Plex Mono 22 px, grey #6b675f, real tokens from the Spark reasoning, scrolling up inside the gate's screen.
         The timer: IBM Plex Mono 500, 120 px, top centre.
         The demo page: the real full-page plate `assets/demo-full.png` at 1920 wide, then the rebuilt pieces at 1.6x with the real labels, fonts and colours of the page.
         The table: real numbers from README.md, four rows, IBM Plex Mono for numbers.
         The reliability chart: two curves from `assets/reliability.json` (head held-out, Spark default on the same 866 images), the perfect diagonal dashed.
MOTION:  enter `expo.out` 0.5 s; move `power2.inOut` 0.5 s; exit `power3.in` 0.25 s; camera `power2.inOut` 0.6 s.
         Belt speed: 220 px/s. A bottle crosses the frame in 8.7 s. Stagger between bottles 1.0 s.
         Counters tick on a linear curve. Titles land and hold still.
         Transitions: (1) the gate's screen grows to fill the frame (object becomes the world), (2) the Run button iris opens onto the output pane, (3) a whip left between the demo and the race, (4) colour flood from dark to light for the table, (5) the mark is carried in by the presenter.
SHOTS:   see SCRIPT.md for the frame ranges, the lines and the sound.
BANNED:  dark void with floating cards; glow, particles, gradients; three cards in a row; a title over a dimmed screenshot; the logo docked in a corner; every scene fading and sliding up; a drawn dashboard that is not the real page; the presenter larger than 40% of the height; the presenter in the middle of the frame; both arms moving together.
QA:      frame 0: belt, one bottle, the timer at 0.00, the presenter at the right. frame 480 (16 s): the token wall, the counter above 1,000, three bottles queued. frame 780 (26 s): the title lands. frame 1200 (40 s): the Run button at 1.6x. frame 1500 (50 s): the output pane with 1.0%. frame 1950 (65 s): the race, right counter in the hundreds, left at 1. frame 2400 (80 s): the chart, both curves drawn. frame 2820 (94 s): the end card.
