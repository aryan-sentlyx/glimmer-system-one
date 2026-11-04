# Your note

*My Script is rough treat it is as a rough guideline for my vision and
how I want the video to run. Max runtime is 3 mins we will try to keep
it at that. First I will introduce myself then introduce Jev, then the
Muse models and the lack of System One model, then we will go on the use
cases and examples, then comparison with other system one models and
finally the demo page*

# Shape

Eight sections in your order. The target length is 180 seconds. The
presenter is a stick figure with your headshot, and the visuals change
with each section. The screen never repeats a spoken sentence word for
word.

Word count of the narration: 425 words after the cut of November 5. The ElevenLabs read (eleven_v4, the clone of Aryan) is 178 s of speech and the film is 179.9 s with the pauses.

Final version, November 4, 2026, cut by about 50 words on November 5 to fit the read into 180 s. Every claim about other models is
listed with its source at the end of the document.

# Sections

## 1. Who I am (0–9 s)

**Narration**

Hello judges. I am Aryan Srivastava, a machine learning engineer from
India. I like to work at the edge of what is new in AI.

**On screen**

The presenter walks in. Name and role land beside the head.

## 2. Push the frontier (9–20 s)

**Narration**

This hackathon asks us to push the frontier. For me that means taking
the Muse models past what they ship with today, to something that does not exist yet.

**On screen**

The theme line “Push the Frontier” lands. The word “yet” is the one
accent word.

## 3. The Muse family and the gap (20–55 s)

**Narration**

This year Meta released the Muse family. Muse Spark is the reasoning
model behind the API. Muse Glimmer is the open 30B multimodal model. What the family does not have is a System One
model. TypeSafe Jev made that category popular in September: a model
that does not write an answer. It decides. It returns a probability in
one pass. OpenAI followed with the Decisions API on GPT-6 Luna.
Microsoft followed with Decision-1. Both are closed. And the Muse family
has none.

**On screen**

A row of the Muse models (Spark, Glimmer, Spark Open, Code, Image,
Video) with an empty slot at the end labelled “System One”. Then the Jev
request shape: a state and a question in, a probability out. Then three
logos: TypeSafe, OpenAI, Microsoft, each with a lock.

## 4. What I built (55–87 s)

**Narration**

So I built Glimmer System One. I took Muse Glimmer, Meta's open 30B
model, and removed the part that writes text. You give it a picture, a
short description, and your questions. For each question it gives back
one number: how sure it is.  You can ask three kinds of questions. Is this true? Which one of
these? How much, on a scale? And because the weights are open, I can stop it at layer 13 of 52 and still answer in 21 milliseconds.

**On screen**

The title lands in the empty slot. A picture, a text and three questions
go in; three numbers come out. The three questions show as three lines
in the demo’s question box, each with its tag. Then the 52 layers as a
bar, with a cut at layer 13 and “21 ms”.

## 5. Use cases and examples (87–120 s)

**Narration**

Where does this help? Think of a factory line. Every second a new part comes by, and one question needs an answer: is it broken? A normal AI model first writes a long explanation, more than a thousand tokens, and that takes eight seconds. The part is
long gone. System One skips the explanation and answers in forty-five
milliseconds. And it works without a picture too. It can stop an AI agent before a dangerous command, or route a support ticket and rate how urgent it is.

**On screen**

The belt with bottles. The bottle waits at the gate while the token wall
scrolls and the timer passes 8.0 s; then the same bottle gets one number
in 45 ms. Then the two text-only presets from the demo: the agent safety
gate and the ticket triage.

## 6. How it compares (120–154 s)

**Narration**

I ran all 1,725 MVTec images through every model. On the
held-out half, Glimmer System One reaches an AUROC of 0.962 with a
calibration error of 0.045. Spark gets 0.87 and 0.10. Liquid, TypeSafe
and Baseten land between, and all of them are worse calibrated. When
System One says seventy percent, about seventy percent of those parts
are defective. That is what makes a threshold mean something.

**On screen**

The results table lands row by row. Then the reliability chart: the
diagonal, the head curve in amber, the Spark curve in grey.

## 7. The demo page (154–171 s)

**Narration**

Here is the demo. Drop an image, write the state, type your questions as
plain lines. Press Run. Six prompts, one pass, every answer as a
probability. The code, the trained heads, and the demo are open under
Apache 2.0.

**On screen**

The real page. Punch in on the two boxes, the Run button, then the
output pane with the live numbers.

## 8. Close (171–180 s)

**Narration**

Glimmer System One. A decision model for the Muse family. Thank you.

**On screen**

The presenter carries the mark in. The name, the demo URL, and the
Hugging Face link hold for three seconds.

# Verified claims and sources

|  |  |
|----|----|
| Muse Spark is the flagship, proprietary reasoning model; 1.1 launched July 9, 2026; 1.3 is current | Wikipedia, Muse Spark; whatllm.org |
| Muse Glimmer 30B: open weights, Apache 2.0, August 2026, distilled from Spark, 52 layers, hidden 6656, 1.8B vision encoder | huggingface.co/meta-models/Muse-Glimmer-30B; CNBC Aug 10, 2026 |
| Muse Spark Open: open weights, October 15, 2026, 816B MoE, 42B active | Wikipedia, Meta Superintelligence Labs |
| Muse Code (Aug 5, 2026), Muse Image, Muse Video exist | Wikipedia; constellationr.com |
| TypeSafe Jev: released September 15, 2026, the first model sold as a System One model, closed, text only | systemonemodels.org; firecrawl.dev blog |
| OpenAI Decisions API: announced at DevDay, September 29, 2026, built on GPT-6 Luna, text or images in, public beta October 6, 2026. Probability output is not documented by OpenAI | firecrawl.dev blog; dev.to; systemonemodels.org |
| Microsoft-Decision-1: October 9, 2026, a calibrated probability per option, in Microsoft Foundry and on OpenRouter, closed | helpnetsecurity.com Oct 12, 2026; innfactory.ai |
| Removed claim: “no open decision model takes images”. Open models with image input exist: Baseten elephant-1 (MIT), Cloudflare Clef (Apache 2.0), Perplexity pplx-decider, H2O-Lightning-4B, Mapika decider-31b (Gemma 4) | systemonemodels.org/models; huggingface.co/Mapika/decider-31b |
| Note: systemonemodels.org lists Baseten elephant-1 as open (MIT). Your README lists it as closed. Check this before the submission text |  |

# Facts the narration uses

|  |  |
|----|----|
| Muse Glimmer 30B | open, Apache 2.0, 30B dense, 52 layers, 1.8B vision encoder |
| Spark median reasoning tokens per image | 1,144 |
| Spark median latency (default reasoning) | 8.0 s |
| System One per image, batched | 45 ms; 21 ms with the early exit at layer 13 |
| Head on the held-out half (866 images) | AUROC 0.962, accuracy 90.2%, ECE 0.045 |
| Spark, all 1,717 images | AUROC 0.872, accuracy 82.6%, ECE 0.101 |
| Liquid d1-ultra | AUROC 0.929, ECE 0.147, 0.46 s, closed |
| TypeSafe Jev 1.14 | AUROC 0.917, ECE 0.125, 0.31 s, closed |
| Baseten Elephant 1 | AUROC 0.902, ECE 0.181, 0.43 s, closed |
| Reliability, head | bin at 76% confidence: 71% defective (21 images) |
| Reliability, Spark | bin at 5% confidence: 36% defective (288 images) |
| Live demo run, good bottle | 1.0% defective, good 99.0%, severity 0.82 / 3, forward 378 ms for 6 prompts |
| Test set | 1,725 images, 15 products, MVTec AD |
| Demo presets without an image | Agent safety gate; Ticket triage |
