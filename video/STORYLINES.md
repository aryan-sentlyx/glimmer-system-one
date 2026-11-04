# Storylines for the Glimmer System One video

Three films. All three use the presenter: a stick figure with the headshot of Aryan as the head. Aryan narrates. Pick one.

Facts that every storyline uses (from AGENTS.md and results/):
- Muse Spark 1.3 writes a median of 1,144 reasoning tokens per image. The median time is 8.0 s.
- Glimmer System One answers in 45 ms per image batched, 21 ms with the early exit at layer 13.
- One real bottle, `bottle_002_good_0.png`: Spark took 19.2 s and 2,279 reasoning tokens, and called it "broken_small" at 0.82. System One said 0.04% defective.
- Head on the held-out half: AUROC 0.962, ECE 0.045. Spark: AUROC 0.872, ECE 0.101.
- The demo page at https://aryan-59489--glimmer-demo.us-east.modal.run.

## A. The line does not wait (recommended)

Device: a moment in someone's day, then life before and after. Form: one conveyor belt that never stops.

The viewer sees a production line. Bottles move from left to right on a belt. The presenter stands at the end of the belt as the inspector. The viewer feels the clock: the belt does not wait for a model that thinks.

First two seconds: a bottle slides in from the left on the belt. The head of the presenter turns to follow it. A timer at the top starts at 0.00 s.

Beats: hook (belt, bottle, timer) → tension (Spark writes a wall of 1,144 tokens, the timer passes 8.0 s, bottles pile up at the stop) → reveal (title "Glimmer System One", the belt starts again) → proof (the real demo page: drop the image, type the question, press Run, read 0.04%) → payoff (the race: 1,725 images through both systems, two counters) → claim (the results table and the reliability diagram) → end card (the mark, the demo URL, the Hugging Face link).

Look: a light grey industrial ground, black ink, one safety-orange accent. The belt and the bottles are drawn; the demo page, the table and the diagram are real captures.

Sound: the voice of Aryan. A low belt hum. One stamp sound per part. A tick for the timer. No music under the voice.

## B. The receipt

Device: type carries the argument, a number lands. Form: kinetic type on paper.

The viewer sees a paper-white stage. The presenter holds one bottle photo up to the camera. A receipt prints from the top of the frame: the reasoning of Spark, token by token, until it runs off the bottom. Then System One gives one stamp with one number. The viewer feels the difference between a page of text and one number.

First two seconds: the presenter holds up the bottle photo. A printer sound starts. The first line of the receipt appears.

Beats: hook (photo, printer) → tension (the receipt unrolls, the counter reaches 2,279 tokens and 19.2 s, the verdict is wrong) → reveal (title) → proof (the demo page, one Run, 0.04%) → payoff (the results table lands one number at a time, then the reliability diagram) → claim → end card.

Look: paper white, black ink, one red accent for the stamp. Monospace for the receipt, sans for the titles.

Sound: the voice of Aryan. A dot-matrix printer. One stamp. No music.

## C. The race

Device: the result first. Form: a split screen for the whole film.

The viewer sees two lanes from the first frame. The same bottle enters both lanes at the same instant. The right lane answers in 45 ms. The left lane still thinks. The presenter sits at the bottom between the lanes and narrates. The viewer feels the gap grow for the whole film.

First two seconds: both lanes start on the same bottle. The right lane shows its answer at 0.045 s. The left lane shows "thinking" with the token counter.

Beats: hook (the race starts) → tension (the left lane still sits on the first image, the right lane passes 100 images) → reveal (title) → proof (the demo page fills the frame for one Run) → payoff (the right lane finishes all 1,725 images, the left lane shows its count) → claim (table, diagram) → end card.

Look: a dark lane for Spark, a light lane for System One, one accent. The bold option.

Sound: the voice of Aryan. A tick per image on the right lane. A low drone on the left lane.
